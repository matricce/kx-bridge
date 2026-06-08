"""
kobrax_moonraker_bridge.py – Moonraker-kompatibler HTTP/WebSocket-Bridge für Anycubic Kobra X

Emuliert die Moonraker/Klipper-API damit OrcaSlicer den Kobra X direkt ansteuern kann.

Verwendung:
  python kobrax_moonraker_bridge.py --printer-ip 192.168.178.94

OrcaSlicer-Konfiguration:
  Drucker-Typ: Klipper  |  Host: 127.0.0.1  |  Port: 7125

────────────────────────────────────────────────────────────────────────────
Copyright (C) 2026 viewit (KX-Bridge contributors)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License v3.0 as published
by the Free Software Foundation. See the LICENSE file in the project root
or <https://www.gnu.org/licenses/gpl-3.0.html> for the full text.

This program is distributed WITHOUT ANY WARRANTY; without even the implied
warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

Reverse-engineering of the Anycubic Kobra X MQTT protocol was carried out
for interoperability purposes (§69e UrhG / EU Software Directive Art. 6).
This project is not affiliated with Anycubic. See NOTICE.md for details.
"""

import argparse
import sqlite3
import uuid
try:
    import config_loader as env_loader
except ImportError:
    import env_loader
import asyncio
import hashlib
import json
import logging
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import time
import threading
import html
from urllib.parse import quote

# Bei PyInstaller-Binary liegt alles neben sys.executable, sonst neben __file__
_BASE = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _BASE)
# Read-Only Web-Assets (Themes) werden im Onefile-Binary via --add-data unter
# sys._MEIPASS entpackt; im Script-/Docker-Modus liegen sie neben dieser Datei.
_WEB_BASE = getattr(sys, "_MEIPASS", _BASE)
from kobrax_client import KobraXClient


try:
    import imageio_ffmpeg
    def _find_ffmpeg() -> str:
        return imageio_ffmpeg.get_ffmpeg_exe()
except ImportError:
    def _find_ffmpeg() -> str:
        exe_name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
        local = os.path.join(_BASE, exe_name)
        if os.path.isfile(local):
            return local
        return "ffmpeg"

try:
    from aiohttp import web
    import aiohttp
except ImportError:
    print("Fehler: aiohttp nicht installiert. Bitte: pip install aiohttp")
    sys.exit(1)

try:
    import base64 as _base64
    from Crypto.Cipher import AES as _AES
    from Crypto.Util.Padding import unpad as _unpad
    _HAS_CRYPTO = True
except ImportError:
    _HAS_CRYPTO = False


def _kx_generate_signature(token: str, ts: int, nonce: str) -> str:
    first = hashlib.md5(token[:16].encode()).hexdigest()
    return hashlib.md5((first + str(ts) + nonce).encode()).hexdigest()


def _kx_decrypt_info(encrypted_b64: str, key: str, iv: str) -> dict:
    cipher = _AES.new(key.encode(), _AES.MODE_CBC, iv.encode())
    raw = _base64.b64decode(encrypted_b64)
    return json.loads(_unpad(cipher.decrypt(raw), _AES.block_size).decode())


async def _kx_fetch_credentials(ip: str, port: int = 18910) -> dict:
    """Holt + entschlüsselt Drucker-Credentials via HTTP /info + /ctrl.

    Wirft eine Exception bei Netzwerk-/Decrypt-Fehlern. Algorithmus aus
    tools/fetch_credentials.py (AES-256-CBC, Key=token[16:32], IV=ctrl-token).
    """
    if not _HAS_CRYPTO:
        raise RuntimeError("pycryptodome nicht installiert")
    import random, string
    nonce = "".join(random.choice(string.ascii_letters + string.digits) for _ in range(6))
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession() as s:
        async with s.get(f"http://{ip}:{port}/info", timeout=timeout) as r:
            r.raise_for_status()
            info = await r.json()
        token = info["token"]
        ts = int(time.time() * 1000)
        sign = _kx_generate_signature(token, ts, nonce)
        params = {"ts": ts, "nonce": nonce, "sign": sign, "did": "random"}
        async with s.post(f"http://{ip}:{port}/ctrl", params=params, timeout=timeout) as r:
            r.raise_for_status()
            data = await r.json()
    result = _kx_decrypt_info(data["data"]["info"], token[16:32], data["data"]["token"])
    if "error" in result:
        raise RuntimeError(result.get("error", "decrypt failed"))
    return {
        "printer_ip": result.get("ip", ip),
        "username":   result.get("username", ""),
        "password":   result.get("password", ""),
        "device_id":  result.get("deviceId", ""),
        "mode_id":    str(result.get("modeId", "20030")),
        "model":      result.get("modelName", "Anycubic Kobra"),
    }

logging.basicConfig(level=logging.INFO,
                    format="[%(asctime)s] %(levelname)-5s %(name)s: %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("bridge")

# Web-UI: Unterverzeichnis unter web/themes/<name>/index.html
_UI_THEME_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")
# Erlaubte statische Theme-Dateien unter /kx/ui/<name>
_KX_UI_ASSETS: dict[str, str] = {
    "style.css": "text/css",
    "app.js":    "application/javascript",
}
_KX_UI_TRANSLATION_RE = re.compile(r"^translations/([a-z]{2}(?:-[a-z]{2})?)\.json$")

# Ring-Buffer für Browser-Log-Stream (letzte 200 Einträge)
import collections as _collections
_log_buffer: "_collections.deque[dict]" = _collections.deque(maxlen=500)
_log_sse_queues: "list[asyncio.Queue]" = []

class _BrowserLogHandler(logging.Handler):
    """Sendet Log-Records in den Ring-Buffer und alle offenen SSE-Queues."""
    _fmt = logging.Formatter(datefmt="%H:%M:%S")

    def emit(self, record: logging.LogRecord):
        msg = record.getMessage()
        # Exceptions mit Traceback in den Browser durchreichen (sonst sieht der
        # Nutzer nur "Fehler: X" ohne Kontext).
        if record.exc_info:
            try:
                msg += "\n" + self._fmt.formatException(record.exc_info)
            except Exception:
                pass
        entry = {
            "ts":    self._fmt.formatTime(record, "%H:%M:%S"),
            "lvl":   record.levelname,
            "name":  record.name,
            "msg":   msg,
        }
        _log_buffer.append(entry)
        for q in list(_log_sse_queues):
            try:
                q.put_nowait(entry)
            except Exception:
                pass

_browser_handler = _BrowserLogHandler()
logging.getLogger().addHandler(_browser_handler)

KOBRA_TO_KLIPPER_STATE = {
    "free":          "standby",
    "busy":          "printing",
    "printing":      "printing",
    "preheating":    "printing",
    "auto_leveling": "printing",
    "checking":      "printing",
    "updated":       "printing",
    "init":          "printing",
    "pausing":       "paused",
    "paused":        "paused",
    "resuming":      "printing",
    "resumed":       "printing",
    "stopping":      "printing",
    "stoped":        "standby",
    "finished":      "complete",
    "failed":        "error",
    "canceled":      "standby",
}

MOONRAKER_VERSION = "v0.9.3-1"
KLIPPER_VERSION   = "v0.12.0-1"


def _parse_gcode_estimated_time(data: bytes) -> int:
    """Liest geschätzte Druckzeit aus GCode (OrcaSlicer + PrusaSlicer).
    Gibt Sekunden zurück, 0 wenn nicht gefunden.
    PrusaSlicer schreibt die Zeit ins Header (erste 16KB),
    OrcaSlicer schreibt sie ans Ende der Datei (letzte 16KB)."""
    import re
    # Anfang + Ende der Datei durchsuchen (OrcaSlicer schreibt Zeit am Ende)
    search_text = (data[:16384] + data[-65536:]).decode("utf-8", errors="ignore")
    # OrcaSlicer:  ; total estimated time: 9m 20s
    # PrusaSlicer: ; estimated printing time (normal mode) = 1h 9m 20s
    m = (re.search(r";\s*total estimated time:\s*(.*)", search_text) or
         re.search(r";\s*estimated printing time \(normal mode\)\s*=\s*(.*)", search_text))
    if not m:
        return 0
    parts = re.findall(r"(\d+)\s*([hms])", m.group(1))
    secs = 0
    for val, unit in parts:
        if unit == "h":   secs += int(val) * 3600
        elif unit == "m": secs += int(val) * 60
        elif unit == "s": secs += int(val)
    if secs:
        log.info(f"Slicer estimate: {secs}s ({m.group(1).strip()})")
    return secs


def _parse_gcode_layer_heights(data: bytes) -> tuple[float, float]:
    """Liest (layer_height, initial_layer_height) aus dem OrcaSlicer-/PrusaSlicer-
    GCode-Header. Beide sind als Konfigblock am Ende des GCode hinterlegt.

    Beispiel-Zeilen:
      ; layer_height = 0.2
      ; initial_layer_print_height = 0.2

    Liefert (0.0, 0.0) wenn nicht gefunden — Aufrufer entscheidet was er macht
    (typisch: keinen Z-Wert anzeigen)."""
    import re
    head = data[:16384].decode("utf-8", errors="ignore")
    tail = data[-65536:].decode("utf-8", errors="ignore")
    search = head + "\n" + tail
    def _grab(pat):
        m = re.search(pat, search)
        if not m:
            return 0.0
        try:
            return float(m.group(1))
        except Exception:
            return 0.0
    layer_h   = _grab(r";\s*layer_height\s*=\s*([0-9.]+)")
    first_h   = (_grab(r";\s*initial_layer_print_height\s*=\s*([0-9.]+)") or
                 _grab(r";\s*first_layer_height\s*=\s*([0-9.]+)") or
                 layer_h)
    return layer_h, first_h


def _extract_thumbnail(data: bytes) -> str:
    """Extrahiert Base64-PNG-Thumbnail aus GCode (OrcaSlicer-Format)."""
    try:
        marker = b"; thumbnail begin"
        end_marker = b"; thumbnail end"
        start = data.find(marker)
        if start == -1:
            return ""
        start = data.find(b"\n", start) + 1
        end = data.find(end_marker, start)
        if end == -1:
            return ""
        lines = data[start:end].split(b"\n")
        b64 = b"".join(
            line[2:].strip() if line.startswith(b"; ") else line.strip()
            for line in lines
        )
        return b64.decode("ascii")
    except Exception:
        return ""


def _extract_filament_info(data: bytes) -> list[dict]:
  """Liest Filament-Farben/Materialien inkl. Tool-Reihenfolge aus Orca/Prusa-GCode.

  Gibt Liste von {slot_index, color_hex, material} in Tool-/Paint-Reihenfolge
  (T0, T1, ...) zurück.
  Sucht sowohl am Anfang als auch am Ende der Datei, da Orca große
  Thumbnail-Blöcke einfügen kann und Metadaten dann im Tail stehen.
  """
  try:
    head = data[:131072]
    tail = data[-131072:] if len(data) > 131072 else b""
    header = (head + b"\n" + tail).decode("utf-8", errors="ignore")
    colors, materials = [], []
    paint_count_hint = 0
    tool_filament_order = []
    for line in header.splitlines():
      if re.match(r"^\s*;\s*filament_colour\s*=", line):
        val = line.split("=", 1)[-1].strip()
        colors = [c.strip().lstrip("#") for c in val.split(";") if c.strip()]
      elif re.match(r"^\s*;\s*filament_multi_colour\s*=", line) and not colors:
        val = line.split("=", 1)[-1].strip()
        colors = [c.strip().lstrip("#") for c in val.split(";") if c.strip()]
      elif re.match(r"^\s*;\s*filament_type\s*=", line):
        val = line.split("=", 1)[-1].strip()
        parts = [m.strip() for m in re.split(r"[;,]", val) if m.strip()]
        materials = parts
        paint_count_hint = max(paint_count_hint, len(parts))
      elif re.match(r"^\s*;\s*filament_density\s*:", line):
        val = line.split(":", 1)[-1].strip()
        parts = [x.strip() for x in re.split(r"[;,]", val) if x.strip()]
        paint_count_hint = max(paint_count_hint, len(parts))
      elif re.match(r"^\s*;\s*filament_diameter\s*:", line):
        val = line.split(":", 1)[-1].strip()
        parts = [x.strip() for x in re.split(r"[;,]", val) if x.strip()]
        paint_count_hint = max(paint_count_hint, len(parts))
      elif re.match(r"^\s*;\s*filament\s*:", line):
        raw = line.split(":", 1)[-1]
        parsed = []
        for p in [x.strip() for x in raw.split(",") if x.strip()]:
          try:
            parsed.append(int(p))
          except Exception:
            pass
        if parsed:
          tool_filament_order = parsed
    total_paints = max(len(colors), len(materials), paint_count_hint)
    if tool_filament_order:
      total_paints = max(total_paints, max(tool_filament_order))
    if total_paints <= 0:
      return []

    # Keep full paint list visible; mark paints referenced by Orca tool order as used.
    if len(colors) < total_paints:
      colors.extend(["FFFFFF"] * (total_paints - len(colors)))
    if len(materials) < total_paints:
      materials.extend(["PLA"] * (total_paints - len(materials)))
    # Prefer actual tool-change commands from the GCode body.
    # This avoids forwarding paints that are present in metadata but never used.
    used_paints_zero_based = set()
    try:
      for m in re.finditer(br"(?m)^[ \t]*T([0-9]+)\b", data):
        used_paints_zero_based.add(int(m.group(1)))
    except Exception:
      used_paints_zero_based = set()

    # Fallback for slicers that only provide paint usage in header metadata.
    used_paints_from_header = set()
    for n in tool_filament_order:
      try:
        # Orca/Prusa filament: list is typically 1-based.
        used_paints_from_header.add(max(0, int(n) - 1))
      except Exception:
        pass

    result = []
    for i in range(total_paints):
      hex_color = colors[i] if i < len(colors) else "FFFFFF"
      result.append({
        "slot_index": i,
        "color_hex":  "#" + hex_color.upper() if hex_color else "#FFFFFF",
        "material":   materials[i] if i < len(materials) else "PLA",
        "is_used":    (i in used_paints_zero_based) if used_paints_zero_based else ((i in used_paints_from_header) if used_paints_from_header else True),
      })
    return result
  except Exception:
    return []


class GCodeStore:
    """Persistenter GCode-Store pro Bridge-Instanz (SQLite)."""

    def __init__(self, data_dir: str):
        os.makedirs(data_dir, exist_ok=True)
        self._gcode_dir = os.path.join(data_dir, "gcodes")
        os.makedirs(self._gcode_dir, exist_ok=True)
        db_path = os.path.join(data_dir, "kx-bridge.db")
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._init_schema()

    def _init_schema(self):
        with self._lock:
            self._conn.executescript("""
                CREATE TABLE IF NOT EXISTS gcode_files (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    path TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    uploaded_at TEXT NOT NULL,
                    thumbnail_b64 TEXT,
                    est_print_time_sec INTEGER,
                    filament_used_mm REAL,
                    layer_count INTEGER,
                    gcode_filaments TEXT,
                    objects_skip_parts TEXT,
                    svg_image TEXT,
                    web_unverified INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS print_jobs (
                    id TEXT PRIMARY KEY,
                    gcode_file_id TEXT NOT NULL,
                    printer_id TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    status TEXT NOT NULL,
                    duration_sec INTEGER,
                    filament_assignments TEXT,
                    abort_reason TEXT
                );
            """)
            # Migration: Spalte gcode_filaments nachrüsten falls DB älter
            try:
                self._conn.execute("ALTER TABLE gcode_files ADD COLUMN gcode_filaments TEXT")
                self._conn.commit()
            except Exception:
                pass
            # Migration: Spalten objects_skip_parts + svg_image (Part-Skip-Feature, v0.9.10)
            # Plus layer_height / first_layer_height (Obico Z-Höhe, v0.9.18)
            for col, typ in (
                ("objects_skip_parts", "TEXT"),
                ("svg_image", "TEXT"),
                ("layer_height", "REAL"),
                ("first_layer_height", "REAL"),
            ):
                try:
                    self._conn.execute(f"ALTER TABLE gcode_files ADD COLUMN {col} {typ}")
                    self._conn.commit()
                except Exception:
                    pass
            # Migration: Flag für Web-Uploads (Warnhinweis vor Druck)
            try:
                self._conn.execute("ALTER TABLE gcode_files ADD COLUMN web_unverified INTEGER NOT NULL DEFAULT 0")
                self._conn.commit()
            except Exception:
                pass

    def save_file(self, file_id: str, filename: str, data: bytes,
                  est_time_sec: int = 0, thumbnail_b64: str = "",
                  gcode_filaments: list | None = None,
                  web_unverified: bool = False,
                  layer_height: float = 0.0,
                  first_layer_height: float = 0.0) -> str:
        """Speichert GCode-Datei auf Disk und in DB. Gibt Pfad zurück."""
        safe_name = os.path.basename(filename)
        path = os.path.join(self._gcode_dir, safe_name)
        with open(path, "wb") as f:
            f.write(data)
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with self._lock:
            filaments_json = json.dumps(gcode_filaments) if gcode_filaments else None
            self._conn.execute(
                """INSERT OR REPLACE INTO gcode_files
                   (id, filename, path, size_bytes, uploaded_at, thumbnail_b64, est_print_time_sec, gcode_filaments, web_unverified, layer_height, first_layer_height)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (file_id, filename, path, len(data), now, thumbnail_b64 or None, est_time_sec or None, filaments_json, 1 if web_unverified else 0, layer_height or None, first_layer_height or None)
            )
            self._conn.commit()
        return path

    def list_files(self) -> list:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM gcode_files ORDER BY uploaded_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def get_file(self, file_id: str) -> dict | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM gcode_files WHERE id=?", (file_id,)
            ).fetchone()
        return dict(row) if row else None

    def get_file_by_name(self, filename: str) -> dict | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM gcode_files WHERE filename=? ORDER BY uploaded_at DESC LIMIT 1",
                (filename,)
            ).fetchone()
        return dict(row) if row else None

    def update_file_objects(self, filename: str, objects: list, svg: str = "") -> None:
        """Speichert Objekt-Liste + optionales SVG zu einer Datei (matcht via filename)."""
        if not filename:
            return
        with self._lock:
            self._conn.execute(
                "UPDATE gcode_files SET objects_skip_parts=?, svg_image=? "
                "WHERE filename=?",
                (json.dumps(objects), svg or "", filename),
            )
            self._conn.commit()

    def update_file_filaments(self, file_id: str, gcode_filaments: list | None) -> None:
      """Aktualisiert geparste GCode-Filamente für einen bestehenden DB-Eintrag."""
      with self._lock:
        self._conn.execute(
          "UPDATE gcode_files SET gcode_filaments=? WHERE id=?",
          (json.dumps(gcode_filaments) if gcode_filaments else None, file_id),
        )
        self._conn.commit()

    def clear_web_unverified(self, file_id: str) -> bool:
        with self._lock:
            cur = self._conn.execute(
                "UPDATE gcode_files SET web_unverified=0 WHERE id=?",
                (file_id,),
            )
            self._conn.commit()
        return cur.rowcount > 0

    def delete_file(self, file_id: str) -> bool:
        row = self.get_file(file_id)
        if not row:
            return False
        try:
            os.remove(row["path"])
        except OSError:
            pass
        with self._lock:
            self._conn.execute("DELETE FROM gcode_files WHERE id=?", (file_id,))
            self._conn.commit()
        return True

    def start_job(self, gcode_file_id: str, printer_id: str,
                  filament_assignments: list | None = None) -> str:
        job_id = str(uuid.uuid4())
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        assignments_json = json.dumps(filament_assignments) if filament_assignments else None
        with self._lock:
            self._conn.execute(
                """INSERT INTO print_jobs
                   (id, gcode_file_id, printer_id, started_at, status, filament_assignments)
                   VALUES (?,?,?,?,'printing',?)""",
                (job_id, gcode_file_id, printer_id, now, assignments_json)
            )
            self._conn.commit()
        return job_id

    def finish_job(self, job_id: str, status: str = "completed",
                   abort_reason: str = "") -> None:
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with self._lock:
            row = self._conn.execute(
                "SELECT started_at FROM print_jobs WHERE id=?", (job_id,)
            ).fetchone()
            duration = None
            if row:
                try:
                    import calendar
                    start = time.strptime(row["started_at"], "%Y-%m-%dT%H:%M:%SZ")
                    duration = int(time.time() - calendar.timegm(start))
                except Exception:
                    pass
            self._conn.execute(
                """UPDATE print_jobs SET ended_at=?, status=?, duration_sec=?, abort_reason=?
                   WHERE id=?""",
                (now, status, duration, abort_reason or None, job_id)
            )
            self._conn.commit()

    def list_jobs(self, limit: int = 50, offset: int = 0) -> list:
        with self._lock:
            rows = self._conn.execute(
                """SELECT j.*, f.filename, f.thumbnail_b64
                   FROM print_jobs j
                   LEFT JOIN gcode_files f ON j.gcode_file_id = f.id
                   ORDER BY j.started_at DESC LIMIT ? OFFSET ?""",
                (limit, offset)
            ).fetchall()
        return [dict(r) for r in rows]


class CameraCache:
    """Zentraler Kamera-Demuxer.

    Hält EINEN ffmpeg-Prozess offen, der den FLV-Stream vom Drucker liest
    und parallel zwei Outputs erzeugt:
      - MJPEG @ 2fps → letzter Frame im RAM für /api/camera/snapshot
      - MPEG-TS (-c:v copy) → Fanout an alle /api/camera/h264-Subscriber

    Damit:
      * Nur EINE FLV-Verbindung zum Drucker (löst Single-Client-Limit / 429)
      * Snapshot ist instant (Speicher-Read, kein ffmpeg-Spawn pro Request)
      * Mehrere parallele H.264-Konsumenten möglich (Plugin + Web-UI + …)

    Lazy-Start beim ersten Konsumenten, Auto-Restart bei ffmpeg-Crash.
    """

    JPEG_SOI = b"\xff\xd8"
    JPEG_EOI = b"\xff\xd9"
    TS_CHUNK = 65536

    def __init__(self):
        self._url: str = ""
        self.latest_jpeg: bytes = b""
        self.latest_jpeg_ts: float = 0.0
        self.h264_subscribers: "set[asyncio.Queue[bytes]]" = set()
        self._proc_jpeg: "asyncio.subprocess.Process | None" = None
        self._proc_h264: "asyncio.subprocess.Process | None" = None
        self._task_jpeg: "asyncio.Task | None" = None
        self._task_h264: "asyncio.Task | None" = None
        self._lock = asyncio.Lock()

    def set_url(self, url: str):
        self._url = url

    async def ensure_running(self):
        if self._proc_jpeg is None or self._proc_jpeg.returncode is not None:
            self._task_jpeg = asyncio.create_task(self._run_jpeg_loop())
        if self._proc_h264 is None or self._proc_h264.returncode is not None:
            self._task_h264 = asyncio.create_task(self._run_h264_loop())

    def _input_args(self, url: str) -> list[str]:
        args = ["-fflags", "nobuffer", "-flags", "low_delay"]
        if url.lower().startswith("rtsp://"):
            args += ["-probesize", "32", "-analyzeduration", "0", "-rtsp_transport", "tcp"]
        else:
            args += ["-probesize", "500000", "-analyzeduration", "500000"]
        return args

    async def _run_jpeg_loop(self):
        """Hält einen ffmpeg-Prozess am Leben der MJPEG@2fps in den Cache schreibt."""
        while True:
            url = self._url
            if not url:
                await asyncio.sleep(2.0)
                continue
            try:
                self._proc_jpeg = await asyncio.create_subprocess_exec(
                    _find_ffmpeg(), "-loglevel", "quiet",
                    *self._input_args(url), "-i", url,
                    "-vf", "fps=2",
                    "-f", "image2pipe", "-vcodec", "mjpeg", "-q:v", "3",
                    "-flush_packets", "1", "pipe:1",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.DEVNULL,
                )
            except Exception as e:
                log.warning(f"CameraCache: ffmpeg-jpeg start fehlgeschlagen: {e}")
                await asyncio.sleep(3.0)
                continue

            buf = b""
            try:
                while True:
                    chunk = await self._proc_jpeg.stdout.read(self.TS_CHUNK)
                    if not chunk:
                        break
                    buf += chunk
                    # extract complete JPEG frames
                    while True:
                        start = buf.find(self.JPEG_SOI)
                        if start == -1:
                            buf = b""
                            break
                        end = buf.find(self.JPEG_EOI, start + 2)
                        if end == -1:
                            buf = buf[start:]
                            break
                        self.latest_jpeg = buf[start:end + 2]
                        self.latest_jpeg_ts = time.time()
                        buf = buf[end + 2:]
            except Exception as e:
                log.debug(f"CameraCache: jpeg-loop unterbrochen: {e}")
            finally:
                # Kill + Wait — sonst bleibt der Child-Prozess als Zombie und
                # asyncio meldet "Unknown child pid …" beim nächsten reaper-Tick.
                if self._proc_jpeg is not None:
                    try:
                        self._proc_jpeg.kill()
                    except Exception:
                        pass
                    try:
                        await self._proc_jpeg.wait()
                    except Exception:
                        pass
                self._proc_jpeg = None
            await asyncio.sleep(2.0)  # restart delay

    async def _run_h264_loop(self):
        """Hält einen ffmpeg-Prozess am Leben der MPEG-TS an alle Subscriber fanoutet."""
        while True:
            url = self._url
            if not url:
                await asyncio.sleep(2.0)
                continue
            try:
                self._proc_h264 = await asyncio.create_subprocess_exec(
                    _find_ffmpeg(), "-loglevel", "quiet",
                    *self._input_args(url), "-i", url,
                    "-c:v", "copy", "-an",
                    "-f", "mpegts", "pipe:1",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.DEVNULL,
                )
            except Exception as e:
                log.warning(f"CameraCache: ffmpeg-h264 start fehlgeschlagen: {e}")
                await asyncio.sleep(3.0)
                continue

            try:
                while True:
                    chunk = await self._proc_h264.stdout.read(self.TS_CHUNK)
                    if not chunk:
                        break
                    # Fanout: nicht-blockierend pro Subscriber, langsame Clients
                    # bekommen ihren ältesten Chunk verworfen (Queue voll → drop).
                    for q in list(self.h264_subscribers):
                        if q.full():
                            try:
                                q.get_nowait()
                            except Exception:
                                pass
                        try:
                            q.put_nowait(chunk)
                        except Exception:
                            pass
            except Exception as e:
                log.debug(f"CameraCache: h264-loop unterbrochen: {e}")
            finally:
                if self._proc_h264 is not None:
                    try:
                        self._proc_h264.kill()
                    except Exception:
                        pass
                    try:
                        await self._proc_h264.wait()
                    except Exception:
                        pass
                self._proc_h264 = None
            await asyncio.sleep(2.0)


class KobraXBridge:
    def __init__(self, client: KobraXClient, args=None, store=None, printer_id: str = "1", all_bridges=None):
        self.client = client
        self._args = args
        self._printer_id = printer_id
        self._all_bridges = all_bridges if all_bridges is not None else {}
        self.ws_clients: set[web.WebSocketResponse] = set()
        # In-Memory KV-Store für Moonraker /server/database/item (moonraker-obico,
        # mainsail-presets etc.). Nicht persistent — überlebt keinen Restart.
        self._moonraker_kv_store: dict[str, dict] = {}
        # Slot→Orca-Filament-Profile-Mapping (aus config.ini [filament_profiles]).
        # Format: {slot_idx: {"id": "OGFL01", "vendor": "Polymaker"}}.
        # Wird in _build_lane_data verwendet, damit OrcaSlicer die konkrete
        # Marke ("PolyTerra PLA — Polymaker") statt nur "Generic PLA" anzeigt.
        try:
            import config_loader as _cl
            self._filament_profiles: dict[int, dict] = _cl.list_filament_profiles()
        except Exception:
            self._filament_profiles = {}
        self._last_state: dict = {}
        self._state = {
          "nozzle_temp":        0.0,
          "nozzle_target":      0.0,
          "bed_temp":           0.0,
          "bed_target":         0.0,
          "print_state":        "standby",
          "kobra_state":        "free",
          "filename":           "",
          "slicer_time":        0,
          "progress":           0.0,
          "print_duration":     0,
          "remain_time":        0,
          "curr_layer":         0,
          "total_layers":       0,
          # Layer-Heights pro aktuell laufender Datei (aus dem GCode-Header
          # geparst). Wird im Upload-Pfad + beim _fetch_from_store gesetzt.
          # Obico nutzt currentZ aus gcode_position[2] — die Bridge rechnet
          # currentZ aus curr_layer + diesen Werten in build_print_payload.
          "layer_height":       0.0,
          "first_layer_height": 0.0,
          "printer_name":       env_loader.get("BRIDGE_PRINTER_NAME", "Anycubic Kobra X"),
          "firmware_version":   "unknown",
          "upload_url":         "",
          "camera_url":         "",
          "fan_speed":          0,
          "light_on":           False,
          "light_brightness":   80,
          "taskid":             "-1",
          "print_speed_mode":   2,
          "connection_error":   "",
          "file_ready":         "",
          "filament_mode":      "toolhead",
          "ace_drying": {"status": 0, "target_temp": 0, "duration": 0, "remain_time": 0, "humidity": None, "current_temp": None},
        }
        self._ams_slots: list[dict] = []       # flat global list; each entry has global_index + box_id
        self._ams_loaded_slot: int = -1        # global slot index of currently loaded slot
        self._pending_load_slot: int = -1      # global slot index requested via /api/ams/feed type=1
        self._ace_box_ids: list[int] = []      # detected ACE unit IDs (0..3)
        self._ace_auto_feed: dict[int, int] = {}   # per-box auto_feed state (0/1)
        self._head_tools_model: int = -1
        self._filament_mode: str = "toolhead"
        self._last_uploaded_file: str = ""
        self._store = store if store is not None else GCodeStore(args.data_dir)
        self._serve_dir_path: str = self._store._gcode_dir
        self._current_job_id: str = ""
        self._camera_autostarted: bool = False
        self._camera_user_stopped: bool = False  # User hat Kamera während Druck manuell gestoppt
        self.camera_cache: CameraCache = CameraCache()

        self._thumbnail_b64: str = ""
        self._ace_dry_presets: dict[str, dict] = self._load_ace_dry_presets_config()

        # Part-Skip: zuletzt vom Drucker gemeldete Skip-Liste (v0.9.10)
        self._skip_state: dict = {"objects": [], "skipped": [], "ts": 0}

        # Theme-Name prüfen (keine Sonderzeichen oder Umlaute)
        raw_theme = (getattr(args, "ui_theme", None) or "default").strip()
        if not _UI_THEME_NAME_RE.match(raw_theme):
            log.warning("Invalid UI theme name %r – using default", raw_theme)
            raw_theme = "default"
        self._ui_theme = raw_theme
        self._index_tpl_cache: str | None = None
        self._index_tpl_cache_key: tuple[str, float] | None = None

        # Register MQTT push callbacks
        client.callbacks["tempature/report"]      = self._on_temp
        client.callbacks["print/report"]          = self._on_print
        client.callbacks["info/report"]           = self._on_info
        client.callbacks["file/report"]           = self._on_file
        client.callbacks["multiColorBox/report"]  = self._on_multicolor_box
        client.callbacks["light/report"]          = self._on_light
        client.callbacks["skip/report"]           = self._on_skip

    def _default_ace_dry_presets(self) -> dict[str, dict]:
        return {
            "pla": {"temp": 45, "duration_sec": 4 * 3600},
        "pla_plus": {"temp": 45, "duration_sec": 4 * 3600},
        "petg": {"temp": 50, "duration_sec": 4 * 3600},
        "tpu": {"temp": 55, "duration_sec": 4 * 3600},
        "abs_asa": {"temp": 45, "duration_sec": 8 * 3600},
        "pa_pc": {"temp": 55, "duration_sec": 12 * 3600},
        "custom_1": {"name": "Custom 1", "temp": 45, "duration_sec": 4 * 3600},
        "custom_2": {"name": "Custom 2", "temp": 45, "duration_sec": 4 * 3600},
        "custom_3": {"name": "Custom 3", "temp": 45, "duration_sec": 4 * 3600},
        }

    def _sanitize_ace_dry_presets(self, presets: dict) -> dict[str, dict]:
        out = self._default_ace_dry_presets()
        for key in list(out.keys()):
            src = presets.get(key) if isinstance(presets, dict) else None
            if not isinstance(src, dict):
                continue
            try:
                t = int(src.get("temp", out[key]["temp"]))
            except Exception:
                t = out[key]["temp"]
            try:
                d = int(src.get("duration_sec", out[key]["duration_sec"]))
            except Exception:
                d = out[key]["duration_sec"]
            out[key]["temp"] = max(30, min(80, t))
            out[key]["duration_sec"] = max(10 * 60, min(24 * 3600, d))
            if key.startswith("custom_"):
                name = str(src.get("name", out[key].get("name", key.replace("_", " ").title()))).strip()
                out[key]["name"] = name or out[key].get("name", "Custom")
        return out

    def _load_ace_dry_presets_config(self) -> dict[str, dict]:
        import configparser
        defaults = self._default_ace_dry_presets()
        cfg_path = self._find_config_path()
        if not cfg_path.is_file():
            return defaults
        cfg = configparser.ConfigParser()
        cfg.read(cfg_path, encoding="utf-8")
        sec = "ace_dry_presets"
        if not cfg.has_section(sec):
            return defaults
        out = {}
        for key, d in defaults.items():
            temp_k = f"{key}_temp"
            dur_k = f"{key}_duration_sec"
            try:
                temp = int(cfg.get(sec, temp_k, fallback=str(d["temp"])))
            except Exception:
                temp = d["temp"]
            try:
                dur = int(cfg.get(sec, dur_k, fallback=str(d["duration_sec"])))
            except Exception:
                dur = d["duration_sec"]
            out[key] = {
                "temp": max(30, min(80, temp)),
                "duration_sec": max(10 * 60, min(24 * 3600, dur)),
            }
            if key.startswith("custom_"):
              name_k = f"{key}_name"
              name = cfg.get(sec, name_k, fallback=str(d.get("name", key.replace("_", " ").title()))).strip()
              out[key]["name"] = name or str(d.get("name", "Custom"))
        return out

    # -------------------------------------------------------------------------
    # MQTT callbacks (called from reader thread)
    # -------------------------------------------------------------------------

    def _on_temp(self, payload: dict):
        d = payload.get("data") or {}
        self._state["nozzle_temp"]   = float(d.get("curr_nozzle_temp", 0))
        self._state["nozzle_target"] = float(d.get("target_nozzle_temp", 0))
        self._state["bed_temp"]      = float(d.get("curr_hotbed_temp", 0))
        self._state["bed_target"]    = float(d.get("target_hotbed_temp", 0))
        self._push_status_update()

    def _on_print(self, payload: dict):
        d = payload.get("data") or {}
        kobra_state = payload.get("state", "")
        self._state["print_state"]    = KOBRA_TO_KLIPPER_STATE.get(kobra_state, "printing")
        if kobra_state:
            self._state["kobra_state"] = kobra_state

        # Kamera bei Druckstart automatisch einschalten (Settings-Option).
        # Zentral hier, damit es alle Druck-Startwege abdeckt (OrcaSlicer + UI).
        # _camera_autostarted verhindert Mehrfach-Trigger pro Druck.
        if kobra_state == "printing":
            if (getattr(self._args, "camera_on_print", 0)
                    and not self._camera_autostarted
                    and not self._camera_user_stopped):
                self._camera_autostarted = True
                try:
                    self.client.start_camera()
                    log.info("Kamera bei Druckstart automatisch eingeschaltet")
                except Exception as e:
                    log.warning(f"Kamera-Autostart fehlgeschlagen: {e}")
        elif kobra_state in ("free", "finished", "stoped", "canceled"):
            self._camera_autostarted = False
            self._camera_user_stopped = False  # für nächsten Druck freigeben

        # Job-History: Druckstart erkennen
        if kobra_state == "printing" and not self._current_job_id:
            filename = d.get("filename", self._state.get("filename", ""))
            if filename:
                gf = self._store.get_file_by_name(filename)
                if gf:
                    self._current_job_id = self._store.start_job(
                        gcode_file_id=gf["id"],
                        printer_id=self._printer_id,
                    )
                    log.info(f"Job started: {self._current_job_id} for {filename}")

        # Job-History: Druckende erkennen
        if kobra_state in ("finished",) and self._current_job_id:
            self._store.finish_job(self._current_job_id, status="completed")
            log.info(f"Job abgeschlossen: {self._current_job_id}")
            self._current_job_id = ""
        elif kobra_state in ("stoped", "canceled") and self._current_job_id:
            self._store.finish_job(self._current_job_id, status="cancelled")
            log.info(f"Job abgebrochen: {self._current_job_id}")
            self._current_job_id = ""

        # Nach Druckende das Upload-Banner verschwinden lassen (Issue #29): der
        # Drucker meldet "finished" nach erfolgreichem Druck — file_ready wurde
        # bisher nur bei stoped/canceled geleert, dadurch kam das Banner zurück.
        if kobra_state == "finished":
            self._state["file_ready"] = ""
        if kobra_state in ("stoped", "canceled"):
            self._state["progress"] = 0.0
            self._state["filename"] = ""
            self._state["file_ready"] = ""
            self._state["print_duration"] = 0
            self._state["remain_time"] = 0
            self._state["slicer_time"] = 0
            self._state["layer_height"] = 0.0
            self._state["first_layer_height"] = 0.0
            self._thumbnail_b64 = ""
        self._state["filename"]       = d.get("filename", self._state["filename"])
        if "progress" in d:
            self._state["progress"]   = float(d["progress"]) / 100.0
        if "print_time" in d:
            self._state["print_duration"] = int(d["print_time"]) * 60
        if "remain_time" in d:
            self._state["remain_time"] = int(d["remain_time"]) * 60
        if "curr_layer" in d:
            self._state["curr_layer"] = d["curr_layer"]
        if "total_layers" in d:
            self._state["total_layers"] = d["total_layers"]
        if "taskid" in d:
            self._state["taskid"] = str(d["taskid"])
        settings = d.get("settings") or {}
        if "print_speed_mode" in settings:
            self._state["print_speed_mode"] = int(settings["print_speed_mode"])
        self._push_status_update()

    def _on_info(self, payload: dict):
        d = payload.get("data") or {}
        # MQTT-Name nur übernehmen wenn kein eigener Name gesetzt (env oder per-Drucker config)
        if not env_loader.get("BRIDGE_PRINTER_NAME") and not getattr(self, "_name_locked", False):
            self._state["printer_name"] = d.get("printerName", self._state["printer_name"])
        self._state["firmware_version"] = d.get("version", self._state["firmware_version"])
        # Der echte Druck-State steckt bei info/report im verschachtelten
        # project.state ("printing"/"paused"/…). Das oberste data.state ist nur
        # der Geräte-State ("busy"/"free") und würde "paused" verschlucken.
        project = d.get("project") or {}
        proj_state = project.get("state", "")
        kobra_state = proj_state or d.get("state", "")
        if kobra_state:
            self._state["print_state"] = KOBRA_TO_KLIPPER_STATE.get(kobra_state, "standby")
            self._state["kobra_state"] = kobra_state
            # Upload-Banner nach Druckende ausblenden (Issue #29) – der State kommt
            # je nach Drucker auch über info/report (project.state), nicht nur print/report.
            if kobra_state in ("finished", "stoped", "canceled"):
                self._state["file_ready"] = ""
            # Kamera-Autostart auch hier (OrcaSlicer meldet Start oft via info/report).
            # _camera_autostarted-Guard verhindert Doppel-Start mit _on_print.
            if kobra_state == "printing":
                if (getattr(self._args, "camera_on_print", 0)
                        and not self._camera_autostarted
                        and not self._camera_user_stopped):
                    self._camera_autostarted = True
                    try:
                        self.client.start_camera()
                        log.info("Kamera bei Druckstart automatisch eingeschaltet")
                    except Exception as e:
                        log.warning(f"Kamera-Autostart fehlgeschlagen: {e}")
            elif kobra_state in ("free", "finished", "stoped", "canceled"):
                self._camera_autostarted = False
                self._camera_user_stopped = False  # für nächsten Druck freigeben
        if project:
            if "filename" in project:
                self._state["filename"] = project["filename"]
            if "progress" in project:
                self._state["progress"] = float(project["progress"]) / 100.0
            if "print_time" in project:
                self._state["print_duration"] = int(project["print_time"]) * 60
            if "remain_time" in project:
                self._state["remain_time"] = int(project["remain_time"]) * 60
            if "curr_layer" in project:
                self._state["curr_layer"] = project["curr_layer"]
            if "total_layers" in project:
                self._state["total_layers"] = project["total_layers"]
        t = d.get("temp") or {}
        if t:
            self._state["nozzle_temp"]   = float(t.get("curr_nozzle_temp", 0))
            self._state["nozzle_target"] = float(t.get("target_nozzle_temp", 0))
            self._state["bed_temp"]      = float(t.get("curr_hotbed_temp", 0))
            self._state["bed_target"]    = float(t.get("target_hotbed_temp", 0))
        urls = d.get("urls") or {}
        if urls.get("fileUploadurl"):
            self._state["upload_url"] = urls["fileUploadurl"]
        if urls.get("rtspUrl"):
            self._state["camera_url"] = urls["rtspUrl"]
            self.camera_cache.set_url(urls["rtspUrl"])
        fan = d.get("fan_speed_pct")
        if fan is not None:
            self._state["fan_speed"] = int(fan)
        speed_mode = d.get("print_speed_mode")
        if speed_mode is not None:
            self._state["print_speed_mode"] = int(speed_mode)
        self._push_status_update()

    def _on_skip(self, payload: dict):
        """skip/report-Callback (Part-Skip-Feature, v0.9.10).

        Drucker meldet hier IMMER die Liste der bereits geskippten Objekte
        zurück (objects_skip_parts), egal ob auf query_obj oder nach skip/start.
        Die Gesamt-Objektliste kommt aus file/report.
        """
        d = payload.get("data") or {}
        skipped = d.get("objects_skip_parts") or d.get("skipped") or d.get("skipped_parts") or []
        # Liste immer (auch leer) übernehmen – sonst bleibt sie auf alten Stand
        self._skip_state = {
            "skipped":  list(skipped),
            "ts":       int(time.time()),
        }
        if payload.get("state") == "done" or payload.get("code") == 200:
            log.info(f"Skip-Antwort: state={payload.get('state')} code={payload.get('code')} skipped={skipped}")

    def _on_file(self, payload: dict):
        d = payload.get("data") or {}
        details = d.get("file_details") or {}
        thumb = details.get("thumbnail") or details.get("png_image") or ""
        if thumb:
            self._thumbnail_b64 = thumb
            log.info(f"Vorschaubild empfangen: {len(thumb)} Zeichen base64")
        # Part-Skip: Objekt-Liste + optionales SVG (v0.9.10)
        objs = details.get("objects_skip_parts") or []
        svg  = details.get("svg_image") or ""
        if objs:
            filename = d.get("filename") or details.get("filename") or self._last_uploaded_file
            if filename:
                try:
                    self._store.update_file_objects(filename, objs, svg)
                    log.info(f"Skip objects for {filename}: {len(objs)} ({'with SVG' if svg else 'no SVG'})")
                except Exception as e:
                    log.warning(f"update_file_objects fehlgeschlagen: {e}")
        self._push_status_update()

    @staticmethod
    def _detect_filament_mode(boxes: list, head_tools_model: int = -1) -> str:
        """Detect active filament topology mode.

        Modes:
        - toolhead: only toolhead slots
        - ace_direct: ACE channels directly mapped (no toolhead box present)
        - ace_hub: toolhead + ACE via hub (slot 4 as hub path)
        """
        toolhead = any(b.get("id") == -1 for b in boxes)
        ace = any(b.get("id", -1) >= 0 for b in boxes)
        if ace and toolhead:
            return "ace_hub"
        if ace:
            return "ace_direct"
        return "toolhead"

    @staticmethod
    def _aggregate_slots(boxes: list, mode: str = "toolhead") -> tuple:
        """Aggregate multi_color_box list into a flat global slot list."""
        toolhead = next((b for b in boxes if b.get("id") == -1), None)
        ace_boxes = sorted(
            [b for b in boxes if b.get("id", -1) >= 0],
            key=lambda b: b["id"]
        )

        global_slots: list = []
        global_loaded: int = -1

        if mode == "toolhead":
            if toolhead:
                for local_idx, s in enumerate(toolhead.get("slots") or []):
                    s = dict(s)
                    s["global_index"] = local_idx
                    s["box_id"] = -1
                    global_slots.append(s)
                loaded = toolhead.get("loaded_slot", -1)
                if loaded >= 0:
                    global_loaded = loaded
            return global_slots, global_loaded

        if mode == "ace_direct":
          # ace_direct exposes exactly 4 channels total.
          # If firmware reports multiple ACE boxes, keep only the first one.
          if ace_boxes:
            ace = ace_boxes[0]
            ace_id = ace["id"]
            for local_idx, s in enumerate((ace.get("slots") or [])[:4]):
              s = dict(s)
              s["global_index"] = local_idx
              s["box_id"] = ace_id
              global_slots.append(s)
            ace_loaded = ace.get("loaded_slot", -1)
            if 0 <= ace_loaded < 4:
              global_loaded = ace_loaded
            return global_slots, global_loaded

        # ace_hub
        if toolhead:
            for local_idx, s in enumerate((toolhead.get("slots") or [])[:3]):
                s = dict(s)
                s["global_index"] = local_idx
                s["box_id"] = -1
                global_slots.append(s)
            th_loaded = toolhead.get("loaded_slot", -1)
            if 0 <= th_loaded <= 2:
                global_loaded = th_loaded

        for ace in ace_boxes:
            ace_id = ace["id"]
            base = 3 + ace_id * 4
            for local_idx, s in enumerate(ace.get("slots") or []):
                s = dict(s)
                s["global_index"] = base + local_idx
                s["box_id"] = ace_id
                global_slots.append(s)
            ace_loaded = ace.get("loaded_slot", -1)
            if ace_loaded >= 0:
                global_loaded = base + ace_loaded

        return global_slots, global_loaded

    def _global_to_box_slot(self, global_index: int) -> tuple:
        """Convert a global slot index to (box_id, local_slot_index)."""
        for s in self._ams_slots:
            if s.get("global_index") == global_index:
                return s.get("box_id", -1), s.get("index", global_index)

        ace_present = any(s.get("box_id", -1) >= 0 for s in self._ams_slots)
        if self._filament_mode == "ace_direct" and ace_present:
            return global_index // 4, global_index % 4
        if not ace_present or global_index < 3:
            return -1, global_index
        offset = global_index - 3
        return offset // 4, offset % 4

    def _slot_to_print_ams_index(self, global_index: int) -> int:
      """Convert UI/global slot index to printer print/start ams_index.

      In ace_hub mode, print/start uses global channel numbering where
      toolhead channels occupy 1..3 and ACE0 starts at index 4.
      """
      idx = int(global_index)
      if self._filament_mode == "ace_hub":
        box_id, local_slot = self._global_to_box_slot(idx)
        if box_id >= 0:
          return 4 + box_id * 4 + int(local_slot)
        return idx
      return idx

    def _slot_usable_for_print(self, global_index: int) -> bool:
        """Whether a global slot can be used for current filament mode."""
        slot = next((s for s in self._ams_slots if int(s.get("global_index", -1)) == int(global_index)), None)
        if not slot:
            return False
        if int(slot.get("status", 0)) != 5:
            return False

        box_id = int(slot.get("box_id", -1))
        if self._filament_mode == "ace_hub":
          # In hub mode, toolhead channels (0..2) and ACE channels are both printable.
          return box_id == -1 or box_id >= 0
        if self._filament_mode == "ace_direct":
            return box_id >= 0
        return box_id == -1

    def _loaded_slots_for_print(self) -> list[tuple[int, dict]]:
        """Loaded slots filtered for current filament mode."""
        loaded = [
            (int(s.get("global_index", i)), s)
            for i, s in enumerate(self._ams_slots)
        if s.get("status") == 5 and self._slot_usable_for_print(int(s.get("global_index", i)))
        ]
        return loaded

    def _select_loaded_slots_for_print(self, warn_on_empty_default: bool = False) -> list[tuple[int, dict]]:
        """Return loaded slots, honoring default_ams_slot when configured."""
        default_slot = getattr(self._args, "default_ams_slot", "auto")
        all_loaded = self._loaded_slots_for_print()
        if default_slot == "auto":
            return all_loaded

        try:
            slot_idx = int(default_slot)
        except ValueError:
            return all_loaded

        selected = [(i, s) for i, s in all_loaded if i == slot_idx]
        if selected:
            return selected

        if warn_on_empty_default:
            log.warning(f"Standard-Slot {slot_idx} ist leer – fallback auf Auto")
        return all_loaded

    @staticmethod
    def _slot_color_rgba(slot: dict) -> list[int]:
        color = slot.get("color", [255, 255, 255])
        if isinstance(color, list) and len(color) >= 3:
            return [int(color[0]), int(color[1]), int(color[2]), 255]
        return [255, 255, 255, 255]

    def _build_auto_ams_box_mapping(
        self,
        warn_on_empty_default: bool = False,
        loaded_slots: list[tuple[int, dict]] | None = None,
    ) -> list[dict]:
        """Build print mapping from currently loaded slots (no explicit dialog assignments)."""
        loaded = loaded_slots
        if loaded is None:
            loaded = self._select_loaded_slots_for_print(warn_on_empty_default=warn_on_empty_default)
        return [
            {
                "paint_index": pidx,
                "ams_index": self._slot_to_print_ams_index(gidx),
                "paint_color": [255, 255, 255, 255],
                "ams_color": self._slot_color_rgba(s),
                "material_type": s.get("type", "PLA"),
            }
            for pidx, (gidx, s) in enumerate(loaded)
        ]

    def _build_assigned_ams_box_mapping(self, assignments: list) -> tuple[list[dict], int, int]:
        """Build print mapping from UI filament assignments.

        Returns (mapping, unused_count, invalid_count).
        """
        slot_by_global_index = {
            int(s.get("global_index", i)): s
            for i, s in enumerate(self._ams_slots)
        }
        ams_box_mapping: list[dict] = []
        unused_count = 0
        invalid_count = 0

        for i, a in enumerate(assignments):
            try:
                if a.get("is_used") is False:
                    unused_count += 1
                    continue
                global_slot = int(a["slot_index"])
            except (ValueError, TypeError, KeyError):
                invalid_count += 1
                continue

            if global_slot < 0:
                unused_count += 1
                continue
            if not self._slot_usable_for_print(global_slot):
                invalid_count += 1
                continue

            slot = slot_by_global_index.get(global_slot, {})
            ams_box_mapping.append({
                # Preserve slicer paint indices (can be sparse when paint 0 is unused).
                "paint_index": a.get("paint_index", i),
                "ams_index": self._slot_to_print_ams_index(global_slot),
                "paint_color": a.get("paint_color", [255, 255, 255, 255]),
                "ams_color": self._slot_color_rgba(slot),
                "material_type": slot.get("type", a.get("material", "PLA")),
            })

        return ams_box_mapping, unused_count, invalid_count

    def _box_local_to_global(self, box_id: int, local_slot: int, boxes: list) -> int:
        """Convert (box_id, local slot) to global slot index for current topology."""
        if box_id == -1:
            return local_slot
        if self._filament_mode == "ace_direct":
            return local_slot
        return 3 + box_id * 4 + local_slot

    def _slot_activity_map(self, boxes: list, global_loaded: int = -1) -> dict:
        """Build {global_slot_index: loading|unloading} from feed_status data."""
        activity: dict = {}
        primary_ace_id = -1
        if self._filament_mode == "ace_direct":
            ace_ids = sorted(int(b.get("id", -1)) for b in boxes if int(b.get("id", -1)) >= 0)
            if ace_ids:
                primary_ace_id = ace_ids[0]
        for box in boxes:
            if self._filament_mode == "ace_direct" and primary_ace_id >= 0 and int(box.get("id", -1)) != primary_ace_id:
                continue
            fs = box.get("feed_status") or {}
            current_status = int(fs.get("current_status", -1))
            local_slot = int(fs.get("slot_index", -1))
            feed_type = int(fs.get("type", -1))
            if current_status in (-1, 10, 11) or local_slot < 0:
                continue
            box_slots = box.get("slots") or []
            if local_slot >= len(box_slots) or (box_slots[local_slot] or {}).get("status") != 5:
                continue
            if feed_type == 1:
                act = "loading"
            elif feed_type == 2:
                act = "unloading"
            else:
                continue
            global_slot = self._box_local_to_global(int(box.get("id", -1)), local_slot, boxes)
            if feed_type == 1 and self._pending_load_slot >= 0 and global_slot != self._pending_load_slot:
                # Ignore transient firmware-reported loading slots that differ from the requested target.
                if global_loaded >= 0 and global_loaded != self._pending_load_slot:
                    activity[global_loaded] = "unloading"
                continue
            if feed_type == 1 and global_loaded >= 0 and global_slot != global_loaded:
                # During a slot swap the firmware reports the target slot immediately,
                # while the previously loaded slot is still being unloaded first.
                activity[global_loaded] = "unloading"
            activity[global_slot] = act
        return activity

    def _on_multicolor_box(self, payload: dict):
        data = payload.get("data") or {}
        boxes = data.get("multi_color_box") or []
        if not boxes:
            return
        self._head_tools_model = int(data.get("head_tools_model", self._head_tools_model))
        self._filament_mode = self._detect_filament_mode(boxes, self._head_tools_model)
        self._state["filament_mode"] = self._filament_mode

        global_slots, global_loaded = self._aggregate_slots(boxes, self._filament_mode)
        self._ams_loaded_slot = global_loaded
        self._update_ace_drying_state(data, boxes)
        for box in boxes:
            bid = int(box.get("id", -1))
            if 0 <= bid <= 3 and "auto_feed" in box:
                self._ace_auto_feed[bid] = int(box["auto_feed"])
        if self._pending_load_slot >= 0 and global_loaded == self._pending_load_slot:
          self._pending_load_slot = -1
        activity_map = self._slot_activity_map(boxes, global_loaded)
        for s in global_slots:
            s["activity"] = activity_map.get(s.get("global_index"), "")

        # Tip-Forming: nach Einziehen (status=10) oder Ausziehen (status=11)
        # schickt der originale Slicer automatisch type=3 (Extruder-Rückzug).
        # Check ALL boxes so ACE-triggered events are handled correctly.
        for box in boxes:
            fs = box.get("feed_status") or {}
            current_status = fs.get("current_status")
            slot_index = fs.get("slot_index", 0)
            box_id = box.get("id", -1)
            if current_status in (10, 11):
                def _tip_form(bi=box_id, si=slot_index, cs=current_status):
                    import time; time.sleep(2)
                    self.client.publish(
                        "multiColorBox", "feedFilament",
                        {"multi_color_box": [{"id": bi, "feed_status": {"slot_index": si, "type": 3}}]},
                        timeout=0
                    )
                    log.info(f"Tip-Forming (type=3) nach status={cs} box={bi} slot={si}")
                threading.Thread(target=_tip_form, daemon=True).start()

        if global_slots:
            self._ams_slots = global_slots
            log.info(f"AMS-Slots empfangen: {len(global_slots)}, loaded_slot={self._ams_loaded_slot}")
            self._push_status_update()

    def _update_ace_drying_state(self, data: dict, boxes: list):
        """Extract ACE drying state from multiColorBox report/getInfo payloads."""
        ace_ids = sorted({int(b.get("id", -1)) for b in boxes if int(b.get("id", -1)) >= 0})
        self._ace_box_ids = [i for i in ace_ids if 0 <= i <= 3]

        def _num_from(src: dict, keys: tuple[str, ...], default=None):
            for k in keys:
                v = src.get(k)
                if v is not None:
                    try:
                        return float(v)
                    except Exception:
                        return default
            return default

        def _humidity_from(src: dict, default=None):
            return _num_from(src, ("humidity", "current_humidity", "cur_humidity", "relative_humidity", "humidity_value"), default)

        def _current_temp_from(src: dict, default=None):
            return _num_from(src, ("current_temp", "cur_temp", "temperature", "temp", "drying_temp", "chamber_temp"), default)

        def _minutes_from(src: dict, key: str, default=0):
          raw = src.get(key, default)
          try:
            value = int(float(raw))
          except Exception:
            return int(default)
          # Some firmware payloads report dryer times in seconds while the UI uses minutes.
          if value > (24 * 60):
            return max(0, int(round(value / 60.0)))
          return max(0, value)

        per_unit: list[dict] = []
        for box in boxes:
            bid = int(box.get("id", -1))
            if bid < 0:
                continue

            bs = box.get("drying_status") or box.get("drying_settings")
            bs = bs if isinstance(bs, dict) else {}
            hu = _humidity_from(bs, _humidity_from(box))
            ct = _current_temp_from(bs, _current_temp_from(box))

            if bs or hu is not None or ct is not None:
                per_unit.append({
                    "id": bid,
                    "status": int(bs.get("status", 0)),
                    "target_temp": int(bs.get("target_temp", 0)),
                "duration": _minutes_from(bs, "duration", 0),
                "remain_time": _minutes_from(bs, "remain_time", 0),
                    "humidity": hu,
                    "current_temp": ct,
                })

        src = data.get("drying_status") or data.get("drying_settings")
        if not isinstance(src, dict):
            for box in boxes:
                if int(box.get("id", -1)) < 0:
                    continue
                cand = box.get("drying_status") or box.get("drying_settings")
                if isinstance(cand, dict):
                    src = cand
                    break

        if isinstance(src, dict):
          cur = self._state.get("ace_drying") or {}
          active = [u for u in per_unit if u.get("status", 0)]
          primary = active[0] if active else (per_unit[0] if per_unit else {})
          self._state["ace_drying"] = {
            "status": int(src.get("status", cur.get("status", 0))),
            "target_temp": int(src.get("target_temp", cur.get("target_temp", 0))),
            "duration": _minutes_from(src, "duration", cur.get("duration", 0)),
            "remain_time": _minutes_from(src, "remain_time", cur.get("remain_time", 0)),
            "humidity": _humidity_from(src, primary.get("humidity", cur.get("humidity"))),
            "current_temp": _current_temp_from(src, primary.get("current_temp", cur.get("current_temp"))),
            "units": per_unit,
          }
        elif per_unit:
            active = [u for u in per_unit if u.get("status", 0)]
            primary = active[0] if active else per_unit[0]
            self._state["ace_drying"] = {
                "status": int(primary.get("status", 0)),
                "target_temp": int(primary.get("target_temp", 0)),
                "duration": int(primary.get("duration", 0)),
                "remain_time": int(primary.get("remain_time", 0)),
                "humidity": primary.get("humidity"),
                "current_temp": primary.get("current_temp"),
                "units": per_unit,
            }

    def _on_light(self, payload: dict):
        d = payload.get("data") or {}
        self._state["light_on"]         = bool(d.get("status", 0))
        self._state["light_brightness"] = int(d.get("brightness", 80))
        self._push_status_update()

    # OrcaSlicer filament preset IDs (MoonrakerPrinterAgent.cpp mapping)
    # Default-Mapping pro Material-Typ wenn der User keinen Slot-Profil-
    # Override gesetzt hat. Für den Kobra X bevorzugen wir Anycubic-eigene
    # Filament-IDs aus den `@Anycubic Kobra X 0.4 nozzle`-Profilen — die
    # sind druckerspezifisch is_compatible und werden von OrcaSlicer direkt
    # gematched. Library-Fallbacks (OGF*) nur für Material-Typen ohne
    # Kobra-X-spezifisches Anycubic-Profil — deren @System-Profile haben
    # `compatible_printers: []` (= mit allen Druckern kompatibel).
    _TRAY_INFO_IDX = {
        # Anycubic-eigene Kobra-X-Profile
        "PLA":      "GFPLA",
        "PLA+":     "GFPLA+",
        "PLA SILK": "GFPLA Silk",
        "PETG":     "GFPETG",
        "ABS":      "GFABS",
        "ASA":      "GFASA",
        "TPU":      "GFTPU 95A",
        "PVA":      "GFPVA",
        # Kein Anycubic-Kobra-X-Profil → Library-Fallback
        "PLA-CF":   "OGFL98",
        "PETG-CF":  "OGFG98",
        "PA":       "OGFN99",
        "PA-CF":    "OGFN98",
        "PC":       "OGFC99",
        "HIPS":     "OGFS98",
    }

    def _build_lane_data(self) -> dict:
      """Baut BBL-AMS-JSON für OrcaSlicer DevFilaSystemParser::ParseV1_0.

      POSITIONSTREU: jeder physische Slot behält seine Position (tray id =
      Slot-Position). Leere Slots werden als Platzhalter-Tray gemeldet, NICHT
      weggefiltert/komprimiert — sonst rutschen die Farben auf falsche Positionen
      (z.B. Slot 1=gelb, 2=leer, 3=rot → rot dürfte nicht auf Position 2 landen).
      """
      slots = self._ams_slots
      total = len(slots)
      if total == 0:
        return {"ams": [], "ams_exist_bits": "0", "tray_exist_bits": "0"}

      ams_count = (total + 3) // 4
      ams_exist_bits = 0
      tray_exist_bits = 0
      ams_array = []

      for ams_id in range(ams_count):
        ams_exist_bits |= (1 << ams_id)
        tray_array = []
        max_slot = min(3, total - ams_id * 4 - 1)
        for slot_id in range(max_slot + 1):
          slot_index = ams_id * 4 + slot_id
          slot = slots[slot_index] if slot_index < total else {}
          occupied = slot.get("status") == 5

          if occupied:
            tray_exist_bits |= (1 << slot_index)
            color_raw = slot.get("color", [255, 255, 255])
            if isinstance(color_raw, list) and len(color_raw) >= 3:
              color_hex = "{:02X}{:02X}{:02X}FF".format(
                int(color_raw[0]), int(color_raw[1]), int(color_raw[2])
              )
            elif isinstance(color_raw, str) and len(color_raw) >= 6:
              color_hex = color_raw[:6].upper() + "FF"
            else:
              color_hex = "FFFFFFFF"
            material = slot.get("type", "PLA").upper()
            # User-Override aus config.ini [filament_profiles].slot_N_id
            # bekommt Vorrang vor dem Default-Mapping nach material-Type.
            # Vendor wird mitgesendet (tray_sub_brands + filament_vendor),
            # damit ein gepatchter OrcaSlicer den Match nach Marke + Type +
            # Farbe machen kann (analog SnapmakerPrinterAgent).
            # Zwei-Schicht-Resolution für den Filament-Hint an OrcaSlicer:
            #   1. User-Wahl (config.ini [filament_profiles]) — exakte Kontrolle
            #   2. Generic-Fallback (_TRAY_INFO_IDX) pro Material-Typ — kein
            #      Vendor-Hint, OrcaSlicer trifft dann sein eigenes Generic-Preset
            user_profile = self._filament_profiles.get(slot_index) or {}
            if user_profile.get("name"):
                vendor    = user_profile.get("vendor", "")
                fila_name = user_profile.get("name", "")
                tray_info_idx = user_profile.get("id") or self._TRAY_INFO_IDX.get(material, "OGFL99")
            else:
                # Default: Library-Generic-Profil (siehe _default_filament_name) —
                # ist mit allen Druckern kompatibel und garantiert sichtbar.
                # Der User wählt pro Slot bewusst eine konkrete Marke wenn er
                # eine will; Default bleibt neutral.
                fila_name = self._default_filament_name(material)
                vendor    = "Generic" if fila_name.startswith("Generic ") else ""
                tray_info_idx = self._lookup_filament_id(vendor, fila_name) or self._TRAY_INFO_IDX.get(material, "OGFL99")
            tray_array.append({
              "id": str(slot_id),
              "tag_uid": "0000000000000000",
              "tray_info_idx": tray_info_idx,
              "tray_type": material,
              "tray_color": color_hex,
              "tray_sub_brands": vendor,
              # OrcaSlicer-Empfangs-Patch PR #13719 erwartet `name` +
              # `vendor_name` pro Lane (Stufen-Matching: Vendor+Name → Name →
              # filament_id_by_type). Wir senden beide Schreibweisen mit
              # damit ältere Patch-Varianten + zukünftige Upstream-PRs beide
              # bedient sind.
              "name":         fila_name,
              "vendor_name":  vendor,
              # Aliase für ältere Patch-Varianten (Variante 2,
              # MoonrakerPrinterAgent.cpp): filament_id direkt (exakt),
              # sonst preset-Name per find_preset() auflösen.
              "filament_id":     tray_info_idx,
              "filament_vendor": vendor,
              "filament_name":   fila_name,
              "preset":          fila_name,
            })
          else:
            tray_array.append({
              "id": str(slot_id),
              "tag_uid": "0000000000000000",
              "tray_info_idx": "",
              "tray_type": "",
              "tray_color": "00000000",
              "tray_slot_placeholder": "1",
            })

        ams_array.append({"id": str(ams_id), "info": "0002", "tray": tray_array})

      return {
        "ams": ams_array,
        "ams_exist_bits": format(ams_exist_bits, "X"),
        "tray_exist_bits": format(tray_exist_bits, "X"),
      }

    @staticmethod
    def _layer_height_from_filename(fname: str) -> float:
        """OrcaSlicer-Default-Filename-Pattern: `<plate>_<material>_<layer>_<dur>.gcode`
        z.B. `adapter_e27_plate(01)_PLA_0.2_41m1s.gcode` → 0.2.

        Fallback wenn der GCode-Header nicht geparst wurde (z.B. Datei direkt am
        Slicer gestartet, oder vor v0.9.18 hochgeladen). Liefert 0.0 wenn das
        Pattern nicht greift."""
        import re
        if not fname:
            return 0.0
        m = re.search(r"_(0\.\d+)_(\d+[hms])", fname)
        if not m:
            return 0.0
        try:
            return float(m.group(1))
        except Exception:
            return 0.0

    def _estimate_current_z(self) -> float:
        """Schätzt die aktuelle Z-Höhe aus curr_layer + Layer-Heights.

        Der Drucker liefert keine echte Z-Position via MQTT, aber Obico
        (moonraker-obico/printer.py:267) liest currentZ aus `gcode_position[2]`.
        Wir rechnen das mit der layer_height aus dem GCode-Header zurück:
          z = first_layer_height + (curr_layer - 1) * layer_height

        Werte werden im Upload-Pfad gesetzt und nur bei Druckabbruch/-ende
        zurückgesetzt (Slot-/Farbänderungen ändern nichts daran). Falls die
        Werte fehlen (z.B. weil der Druck direkt am Slicer gestartet wurde
        ohne Upload über die Bridge), wird einmalig aus dem GCode-Store
        nachgeladen. Liefert 0.0 wenn nichts bekannt — Obico zeigt dann
        keinen Z-Wert."""
        s = self._state
        layer_h = float(s.get("layer_height") or 0.0)
        first_h = float(s.get("first_layer_height") or 0.0)
        fname = s.get("filename", "")
        if not layer_h and fname:
            try:
                gf = self._store.get_file_by_name(fname)
                if gf:
                    layer_h = float(gf.get("layer_height") or 0.0)
                    first_h = float(gf.get("first_layer_height") or layer_h)
            except Exception:
                pass
        if not layer_h and fname:
            # Letzter Fallback: OrcaSlicer-Default-Filename enthält die Layer-Height
            layer_h = self._layer_height_from_filename(fname)
            if layer_h and not first_h:
                first_h = layer_h
        if layer_h:
            # cache in state damit nicht jeder Build wieder den Store fragt
            s["layer_height"] = layer_h
            s["first_layer_height"] = first_h
        if not layer_h:
            return 0.0
        curr = int(s.get("curr_layer") or 0)
        if curr <= 0:
            return 0.0
        # Layer 1 = first_layer_height, Layer 2 = first + layer_h, …
        return round(first_h + max(0, curr - 1) * layer_h, 3)

    # -------------------------------------------------------------------------
    # WebSocket push
    # -------------------------------------------------------------------------

    def _push_status_update(self):
        if not self.ws_clients:
            return
        msg = {
            "jsonrpc": "2.0",
            "method":  "notify_status_update",
            "params": [self._build_printer_objects(), time.time()],
        }
        text = json.dumps(msg)
        dead = set()
        for ws in self.ws_clients:
            try:
                asyncio.run_coroutine_threadsafe(ws.send_str(text), ws._loop)
            except Exception:
                dead.add(ws)
        self.ws_clients -= dead

    def _build_mmu_object(self) -> dict:
      # POSITIONSTREU: ein Gate je physischem Slot, in Reihenfolge. Leere Slots
      # bekommen gate_status=0 (statt weggelassen zu werden) – sonst rutschen die
      # Farben in OrcaSlicer auf falsche Gates (Slot 1=gelb, 2=leer, 3=rot →
      # rot darf nicht auf Gate 1 landen). gate_status 0=leer, 1=verfügbar.
      slots = sorted(
        ((int(s.get("global_index", i)), s) for i, s in enumerate(self._ams_slots)),
        key=lambda item: item[0],
      )
      if not slots:
        return {}

      _TEMP = {"PLA": 210, "PETG": 230, "ABS": 240, "ASA": 250,
           "TPU": 220, "PA": 260, "PC": 270, "HIPS": 220}
      num_gates = len(slots)
      gate_status, gate_material, gate_color, gate_temperature, gate_color_rgb = [], [], [], [], []
      gate_filament_name = []
      for _global_index, slot in slots:
        occupied = slot.get("status") == 5
        gate_status.append(1 if occupied else 0)
        material = (slot.get("type") or "PLA").upper() if occupied else ""
        gate_material.append(material)
        c = slot.get("color", [0, 0, 0]) if occupied else [0, 0, 0]
        # Happy Hare erwartet gate_color als RRGGBB OHNE '#' (Klipper-Limitation).
        # Leerer Gate: leerer String + RGB [0,0,0].
        gate_color.append("{:02X}{:02X}{:02X}".format(*c[:3]) if occupied else "")
        gate_color_rgb.append([round(c[0]/255, 3), round(c[1]/255, 3), round(c[2]/255, 3)] if occupied else [0.0, 0.0, 0.0])
        gate_temperature.append(_TEMP.get(material, 210) if occupied else 0)
        # gate_filament_name aus User-Override oder Material-Default für den
        # HH-Pfad in OrcaSlicer (fetch_hh_filament_info). Wenn Orca den
        # HH-Pfad wählt (MMU-Erkennung), wertet PR #13719 dieses Feld als
        # Preset-Namen aus → 'Anycubic PLA' matched das druckerspezifische
        # Preset, leerer String führte vorher auf Generic PLA.
        if occupied:
          user_profile = self._filament_profiles.get(_global_index) or {}
          fila_name = user_profile.get("name") or self._default_filament_name(material)
          gate_filament_name.append(fila_name)
        else:
          gate_filament_name.append("")

      loaded_index_map = {global_index: idx for idx, (global_index, _) in enumerate(slots)}
      active_gate = loaded_index_map.get(int(self._ams_loaded_slot), -1)
      return {
        "num_gates":          num_gates,
        "enabled":            True,
        "gate_status":        gate_status,
        "gate_material":      gate_material,
        "gate_color":         gate_color,
        "gate_temperature":   gate_temperature,
        "gate_color_rgb":     gate_color_rgb,
        "gate_filament_name": gate_filament_name,
        "gate_spool_id":      [-1] * num_gates,
        "ttg_map":            list(range(num_gates)),
        "tool":               active_gate,
        "gate":               active_gate,
      }

    def _default_filament_name(self, material: str) -> str:
      """Default-Name für `gate_filament_name`/`name` in lane_data wenn kein
      User-Override gesetzt ist. Bewusste Designentscheidung: **immer
      Generic <Typ>** als Default — das Library-Profil ist `compatible_printers:[]`
      (= mit jedem Drucker kompatibel) und damit garantiert sichtbar.

      OrcaSlicer matcht dann das neutrale Generic-Preset und der User
      kann pro Slot eine konkrete Marke setzen wenn er das will."""
      if not material:
        return ""
      mat = material.upper().strip()
      profs = self._load_orca_filaments()
      def _match_type(p: dict) -> bool:
        pt = (p.get("type") or "").upper()
        return pt == mat or pt.startswith(mat + "-") or pt.startswith(mat + " ")
      # Library-Generic-Profil (immer is_visible+is_compatible)
      for p in profs:
        if p.get("vendor") == "Generic" and p.get("name", "").startswith("Generic ") and _match_type(p):
          return p.get("name", "")
      # Falls die Library-Generic für diesen exotischen Material-Typ fehlt,
      # liefern wir nichts — OrcaSlicer fällt auf filament_id_by_type zurück.
      return ""

    def _build_printer_objects(self) -> dict:
        s = self._state
        return {
            "extruder": {
                "temperature": s["nozzle_temp"],
                "target":      s["nozzle_target"],
                "power":       0.0,
            },
            "heater_bed": {
                "temperature": s["bed_temp"],
                "target":      s["bed_target"],
                "power":       0.0,
            },
            "print_stats": {
                "state":          s["print_state"],
                "filename":       s["filename"],
                "print_duration": s["print_duration"],
                "total_duration": s["print_duration"],
                "remain_time":    s["remain_time"],
                "info": {
                    "current_layer": s["curr_layer"],
                    "total_layer":   s["total_layers"],
                },
            },
            "display_status": {
                "progress": s["progress"],
                "message":  "",
            },
            "virtual_sdcard": {
                "progress":  s["progress"],
                "is_active": s["print_state"] == "printing",
                "file_path": s["filename"],
                # file_position approximiert: fraction × est_total_size.
                # Genauer Wert kommt aus dem Drucker nicht, Obico nutzt es nur als Anzeige.
                "file_position": int(s["progress"] * 1_000_000) if s["progress"] else 0,
            },
            "toolhead": {
                "position":         [0, 0, 0, 0],
                "homed_axes":       "xyz",
                "print_time":       s["print_duration"],
                "estimated_print_time": s["print_duration"],
            },
            "mmu": self._build_mmu_object(),
            # ── Moonraker-Kompatibilität für moonraker-obico ──
            "heaters": {
                "available_heaters": ["extruder", "heater_bed"],
                "available_sensors": [],
                "available_monitors": [],
            },
            "webhooks": {
                "state":         "ready",
                "state_message": "Printer is ready",
            },
            # speed_factor: 1=silent(0.5) / 2=standard(1.0) / 3=high(1.3) / 4=ultra(1.5)
            # Aktuelle Z-Höhe für Obico aus curr_layer + Layer-Heights schätzen
            # (Drucker liefert keine echte Z-Position per MQTT). gcode_position[2]
            # ist der Wert den moonraker-obico in printer.py als currentZ liest.
            "gcode_move": {
                "speed_factor":   {1: 0.5, 2: 1.0, 3: 1.3, 4: 1.5}.get(int(s.get("print_speed_mode") or 2), 1.0),
                "extrude_factor": 1.0,
                "speed":          0,
                "gcode_position": [0, 0, self._estimate_current_z(), 0],
                "absolute_coordinates": True,
                "absolute_extrude":     True,
                "homing_origin":  [0, 0, 0, 0],
                "position":       [0, 0, self._estimate_current_z(), 0],
            },
            "fan": {
                "speed": (int(s.get("fan_speed") or 0)) / 100.0,
                "rpm":   None,
            },
            # history (object): Obico abonniert es als Objekt; das eigentliche
            # /server/history/list-Endpoint liefert die echte Liste separat.
            "history": {
                "job_totals": {
                    "total_jobs":  0,
                    "total_time":  0,
                    "total_print_time": 0,
                    "total_filament_used": 0.0,
                    "longest_job": 0,
                    "longest_print": 0,
                },
                "current_job": None,
            },
            # Pseudo-Klipper-Macros für moonraker-obico:
            # - _OBICO_LAYER_CHANGE meldet die aktuelle Layer-Nr. Obico nutzt das
            #   für "first layer scan"-Trigger und layer-aligned Time-Lapse-Frames.
            #   Wir bedienen das aus dem MQTT-Stream (s["curr_layer"]).
            # - TIMELAPSE_TAKE_FRAME signalisiert, dass die aktuelle Pause vom
            #   Time-Lapse stammt (sonst würde Obico die Pause als User-Pause
            #   interpretieren). Wir setzen is_paused=False, weil unsere Pausen
            #   nie Time-Lapse-Pausen sind.
            "gcode_macro _OBICO_LAYER_CHANGE": {
                "current_layer":         int(s.get("curr_layer") or 0),
                "first_layer_scanning":  False,
                "first_layer_scan_enabled": False,
            },
            "gcode_macro TIMELAPSE_TAKE_FRAME": {
                "is_paused": False,
            },
            # configfile stub — Mobileraker und andere Clients crashen ohne
            # dieses Objekt (Missing field: configFile). Werte aus der
            # entschlüsselten avata_main.conf (ACCFG1.0 — Kobra X Firmware).
            "configfile": {
                "config": {},
                "settings": {
                    "printer": {
                        "kinematics":              "cartesian",
                        "max_velocity":            450,
                        "max_accel":               10000,
                        "max_z_velocity":          12,
                        "max_z_accel":             100,
                        "square_corner_velocity":  20.0,
                    },
                    "extruder": {
                        "nozzle_diameter":  0.4,
                        "min_temp":         0,
                        "max_temp":         320,
                        "min_extrude_temp": 10,
                    },
                    "heater_bed": {
                        "min_temp": 0,
                        "max_temp": 120,
                    },
                    "stepper_x": {"position_min": -18.5, "position_max": 280},
                    "stepper_y": {"position_min": -6.5,  "position_max": 272.5},
                    "stepper_z": {"position_min": -4,    "position_max": 262},
                    "virtual_sdcard": {"path": "/data/gcodes"},
                    "pause_resume":   {},
                    "display_status": {},
                },
                "warnings": [],
                "save_config_pending": False,
                "save_config_pending_items": {},
            },
        }

    # -------------------------------------------------------------------------
    # /kx/ API handlers (GCode Store, History, Filament)
    # -------------------------------------------------------------------------

    _CORS = {
        "Access-Control-Allow-Origin":  "*",
        "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }

    def _json_cors(self, data, status=200):
        return web.json_response(data, status=status, headers=self._CORS)

    async def handle_kx_options(self, request):
        return web.Response(status=204, headers=self._CORS)

    async def handle_kx_files(self, request):
        files = self._store.list_files()
        # Legacy-Einträge ohne gespeicherte Filament-Metadaten nachziehen,
        # damit Dialog links die GCode-Farben statt AMS-Slots zeigt.
        for f in files:
            needs_refresh = not f.get("gcode_filaments")
            if not needs_refresh:
                try:
                    cached = f.get("gcode_filaments")
                    parsed_cached = cached if isinstance(cached, list) else json.loads(cached)
                    needs_refresh = any("is_used" not in item for item in (parsed_cached or []))
                except Exception:
                    needs_refresh = True
            if not needs_refresh:
                continue
            path = f.get("path") or ""
            if not path or not os.path.isfile(path):
                continue
            try:
                with open(path, "rb") as fh:
                    parsed_filaments = _extract_filament_info(fh.read())
                if parsed_filaments:
                    f["gcode_filaments"] = json.dumps(parsed_filaments)
                    self._store.update_file_filaments(f["id"], parsed_filaments)
            except Exception:
                pass
        # Letzten Job-Status + Dauer pro Datei ergänzen
        jobs = self._store.list_jobs(limit=500)
        last_job: dict = {}
        for j in reversed(jobs):
            last_job[j["gcode_file_id"]] = j
        for f in files:
            f["web_unverified"] = bool(f.get("web_unverified"))
            lj = last_job.get(f["id"])
            f["last_print_status"]   = lj["status"]       if lj else None
            f["last_print_duration"] = lj["duration_sec"] if lj else None
            f["last_print_at"]       = lj["started_at"]   if lj else None
        return self._json_cors({"result": files})

    async def handle_kx_file_delete(self, request):
        file_id = request.match_info["file_id"]
        if self._store.delete_file(file_id):
            return self._json_cors({"result": "ok"})
        return self._json_cors({"error": "not found"}, status=404)

    async def handle_kx_file_download(self, request):
        file_id = request.match_info["file_id"]
        f = self._store.get_file(file_id)
        if not f:
            return self._json_cors({"error": "not found"}, status=404)
        path = f.get("path") or ""
        if not path or not os.path.isfile(path):
            return self._json_cors({"error": "not found"}, status=404)
        filename = os.path.basename(f.get("filename") or path)
        # RFC 5987: filename* mit URL-encoding für Sonderzeichen/UTF-8,
        # plus ASCII-fallback (alle " und \ aus filename strippen für den
        # quoted-string-Part).
        ascii_fallback = filename.encode("ascii", "replace").decode("ascii").replace('"', "").replace("\\", "")
        encoded = quote(filename, safe="")
        disposition = f'attachment; filename="{ascii_fallback}"; filename*=UTF-8\'\'{encoded}'
        return web.FileResponse(path, headers={"Content-Disposition": disposition})

    async def handle_kx_file_verify(self, request):
        file_id = request.match_info["file_id"]
        if self._store.clear_web_unverified(file_id):
            return self._json_cors({"result": "ok"})
        return self._json_cors({"error": "not found"}, status=404)

    async def handle_kx_filament_slots(self, request):
        slots = []
        for i, s in enumerate(self._ams_slots):
            gidx = int(s.get("global_index", i))
            profile = self._filament_profiles.get(gidx) or {}
            slots.append({
                "slot_index":  gidx,
                "material":    s.get("type", ""),
                "color_hex":   "#{:02X}{:02X}{:02X}".format(*s.get("color", [0,0,0])[:3]),
                "status":      "loaded" if s.get("status") == 5 else "empty",
                "nozzle_temp": 0,
                # Aktueller User-Override aus config.ini [filament_profiles]
                # — (vendor,name) ist eindeutig, id ist nur Hint.
                "filament_id":     profile.get("id", ""),
                "filament_vendor": profile.get("vendor", ""),
                "filament_name":   profile.get("name", ""),
            })
        return self._json_cors({"result": slots})

    async def handle_kx_filament_profiles(self, request):
        """Liefert die statische Liste der OrcaSlicer-Filament-Profile
        (aus bridge/data/orca_filaments.json — vom Generator-Script
        tools/gen_orca_filament_list.py erzeugt).

        Optional Filter via ?type=PLA / ?vendor=Polymaker.
        Frontend nutzt das für die Slot-Profile-Dropdown.
        """
        type_filter = request.rel_url.query.get("type", "").upper().strip()
        vendor_filter = request.rel_url.query.get("vendor", "").strip()
        profiles = self._load_orca_filaments()
        if type_filter:
            profiles = [p for p in profiles if p.get("type", "").upper() == type_filter]
        if vendor_filter:
            profiles = [p for p in profiles if p.get("vendor", "") == vendor_filter]
        return self._json_cors({"result": profiles})

    async def handle_kx_filament_profiles_user_list(self, request):
        """GET /kx/filament/profiles/user — nur die User-importierten Profile,
        für den Settings-Tab (Verwaltung mit Lösch-Buttons)."""
        path = self._orca_filaments_user_path()
        if not os.path.isfile(path):
            return self._json_cors({"result": []})
        try:
            with open(path, encoding="utf-8") as f:
                user_profiles = json.load(f) or []
        except Exception:
            user_profiles = []
        return self._json_cors({"result": user_profiles})

    async def handle_kx_filament_profiles_import(self, request):
        """POST /kx/filament/profiles/user — multipart-Upload mit einer
        ZIP-Datei oder mehreren `.json`-Files aus
        ~/.config/OrcaSlicer/user/<id>/filament/.

        Bestehende User-Profile mit gleichem (vendor, name)-Key werden
        überschrieben. Geparste Profile haben dasselbe Schema wie
        orca_filaments.json (id, name, vendor, type, color)."""
        import io, zipfile
        from orca_filaments import parse_profile_bytes
        added: list[dict] = []
        skipped: int = 0
        # System-Index für Inherits-Resolve: User-Profile referenzieren
        # System-Parents via "inherits" (z.B. "Generic PLA @System"). Damit
        # können wir filament_id/vendor/type/color aus dem System-Parent
        # ziehen wenn das User-Profil sie selbst nicht setzt.
        sys_idx = [p for p in self._load_orca_filaments() if not p.get("is_user")]
        try:
            reader = await request.multipart()
        except Exception:
            return self._json_cors({"error": "expected multipart"}, status=400)
        async for part in reader:
            if part.name not in ("file", "files", "upload"):
                continue
            blob = await part.read()
            fn   = (part.filename or "").lower()
            if fn.endswith(".zip"):
                try:
                    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
                        for inner in zf.namelist():
                            if not inner.lower().endswith(".json"):
                                continue
                            try:
                                with zf.open(inner) as zf_in:
                                    p = parse_profile_bytes(zf_in.read(), source_name=inner, system_index=sys_idx)
                            except Exception:
                                skipped += 1
                                continue
                            if p:
                                added.append(p)
                            else:
                                skipped += 1
                except zipfile.BadZipFile:
                    return self._json_cors({"error": "bad zip"}, status=400)
            elif fn.endswith(".json"):
                p = parse_profile_bytes(blob, source_name=fn, system_index=sys_idx)
                if p:
                    added.append(p)
                else:
                    skipped += 1

        if not added:
            return self._json_cors({"result": "ok", "added": 0, "skipped": skipped})

        # Merge mit existierender User-JSON (gleicher (vendor,name) → ersetzen)
        path = self._orca_filaments_user_path()
        existing: list[dict] = []
        if os.path.isfile(path):
            try:
                with open(path, encoding="utf-8") as f:
                    existing = json.load(f) or []
            except Exception:
                existing = []
        by_key = {(p.get("vendor"), p.get("name")): p for p in existing}
        for p in added:
            by_key[(p.get("vendor"), p.get("name"))] = p
        merged = sorted(by_key.values(), key=lambda x: (x.get("vendor",""), x.get("name","")))
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(merged, f, indent=2, ensure_ascii=False)
                f.write("\n")
        except Exception as e:
            return self._json_cors({"error": f"write failed: {e}"}, status=500)
        self._invalidate_filaments_cache()
        return self._json_cors({"result": "ok",
                                "added": len(added),
                                "skipped": skipped,
                                "total_user": len(merged)})

    async def handle_kx_filament_profiles_user_delete(self, request):
        """DELETE /kx/filament/profiles/user — löscht entweder einen einzelnen
        Eintrag (?vendor=…&name=…) oder alle wenn keine Query angegeben."""
        vendor = request.rel_url.query.get("vendor", "").strip()
        name   = request.rel_url.query.get("name", "").strip()
        path = self._orca_filaments_user_path()
        if not os.path.isfile(path):
            return self._json_cors({"result": "ok", "removed": 0})
        try:
            with open(path, encoding="utf-8") as f:
                existing = json.load(f) or []
        except Exception:
            existing = []
        before = len(existing)
        if vendor and name:
            existing = [p for p in existing
                        if not (p.get("vendor") == vendor and p.get("name") == name)]
        else:
            existing = []
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2, ensure_ascii=False)
                f.write("\n")
        except Exception as e:
            return self._json_cors({"error": str(e)}, status=500)
        self._invalidate_filaments_cache()
        return self._json_cors({"result": "ok",
                                "removed": before - len(existing),
                                "total_user": len(existing)})

    def _find_orca_filaments_json(self) -> str | None:
        """Findet die statische JSON-Datei. Liegt analog zu web/ unter _WEB_BASE/data/
        — in allen 3 Deployment-Modi:
          • Dev:     bridge/data/orca_filaments.json
          • Docker:  /app/data/orca_filaments.json (statisch im Image, NICHT das
                     Volume-data/ das Runtime-State enthält — siehe Dockerfile)
          • Onefile: sys._MEIPASS/data/orca_filaments.json
        Wenn das Volume-mounted /app/data/ den static-data überdeckt, liegt eine
        Kopie auch unter _WEB_BASE/data/ (= /app/ im Docker = derselbe Pfad).
        Bei Konflikt: zweite Suche unter ../bridge/data/ als Fallback für Dev-Setups."""
        candidates = [
            # Docker: COPY bridge/data → /app/static/ (data/ ist Volume → überdeckt)
            os.path.join(_WEB_BASE, "static", "orca_filaments.json"),
            os.path.join(_WEB_BASE, "data", "orca_filaments.json"),
        ]
        here = os.path.dirname(os.path.abspath(__file__))
        candidates.append(os.path.join(here, "data", "orca_filaments.json"))
        candidates.append(os.path.join(here, "..", "bridge", "data", "orca_filaments.json"))
        for c in candidates:
            if os.path.isfile(c):
                return c
        return None

    async def handle_kx_filament_slot_profile(self, request):
        """POST /kx/filament/slots/<idx>/profile — speichert oder löscht
        ein User-Override-Mapping für einen einzelnen AMS-Slot.

        Primärer Selector ist (vendor, name) — die ID ist im Orca-Datenmodell
        nicht eindeutig (136 Profile teilen sich z.B. 'OGFL99'). Die ID wird
        aus orca_filaments.json beim Speichern nachgeschlagen und als Hint
        mitgeführt für OrcaSlicer's `tray_info_idx`.

        Body: {"vendor": "Polymaker", "name": "PolyTerra PLA"}
              {"vendor": "", "name": ""} → Mapping entfernen
              (Backwards-Kompat: {"id":..., "vendor":...} wird akzeptiert,
              aber `name` ist seit v0.9.18 der primäre Selector.)
        """
        try:
            slot_idx = int(request.match_info.get("idx", "-1"))
        except ValueError:
            return self._json_cors({"error": "bad slot index"}, status=400)
        if slot_idx < 0:
            return self._json_cors({"error": "bad slot index"}, status=400)
        try:
            data = await request.json()
        except Exception:
            data = {}
        new_vendor = (data.get("vendor") or "").strip()
        new_name   = (data.get("name")   or "").strip()
        new_id     = (data.get("id")     or "").strip()  # Backwards-Kompat-Hint
        if new_vendor and new_name:
            # ID aus JSON lookup'en (nicht aus dem Request-Body, der könnte
            # veraltet sein oder ein Generic-Fallback).
            looked_up_id = self._lookup_filament_id(new_vendor, new_name)
            self._filament_profiles[slot_idx] = {
                "vendor": new_vendor,
                "name":   new_name,
                "id":     looked_up_id or new_id,
            }
        else:
            self._filament_profiles.pop(slot_idx, None)
        # Persistieren in config.ini
        try:
            import config_loader as _cl
            _cl.save_filament_profiles(self._filament_profiles)
        except Exception as e:
            log.warning(f"save_filament_profiles failed: {e}")
            return self._json_cors({"error": str(e)}, status=500)
        entry = self._filament_profiles.get(slot_idx, {})
        return self._json_cors({"result": "ok",
                                "slot_index": slot_idx,
                                "vendor": entry.get("vendor", ""),
                                "name":   entry.get("name", ""),
                                "id":     entry.get("id", "")})

    def _load_orca_filaments(self) -> list[dict]:
        """Lädt System- + User-Profile aus dem Cache. System-Profile kommen
        aus bridge/data/orca_filaments.json (Image-embedded), User-Profile
        aus <KX_DATA_DIR>/orca_filaments.user.json (Volume-persistent —
        überlebt Image-Updates). User-Profile bekommen ein `is_user: True`-
        Flag damit das Frontend sie markieren kann."""
        if getattr(self, "_orca_filaments_cache", None) is not None:
            return self._orca_filaments_cache
        merged: list[dict] = []
        # System
        sys_path = self._find_orca_filaments_json()
        if sys_path and os.path.isfile(sys_path):
            try:
                with open(sys_path, encoding="utf-8") as f:
                    merged.extend(json.load(f) or [])
            except Exception as e:
                log.warning(f"orca_filaments.json read error: {e}")
        # User
        usr_path = self._orca_filaments_user_path()
        if usr_path and os.path.isfile(usr_path):
            try:
                with open(usr_path, encoding="utf-8") as f:
                    for p in (json.load(f) or []):
                        p["is_user"] = True
                        merged.append(p)
            except Exception as e:
                log.warning(f"orca_filaments.user.json read error: {e}")
        self._orca_filaments_cache = merged
        return self._orca_filaments_cache

    def _orca_filaments_user_path(self) -> str:
        """Pfad zur User-Profile-JSON. Liegt im Volume-Mount (KX_DATA_DIR),
        damit Image-Updates die Daten nicht zerstören."""
        data_dir = os.environ.get("KX_DATA_DIR") or os.path.join(_WEB_BASE, "data")
        os.makedirs(data_dir, exist_ok=True)
        return os.path.join(data_dir, "orca_filaments.user.json")

    def _invalidate_filaments_cache(self):
        self._orca_filaments_cache = None

    def _lookup_filament_id(self, vendor: str, name: str) -> str:
        """Sucht in orca_filaments.json die filament_id zu einem (vendor,name)-
        Tupel. Liefert '' wenn nicht gefunden."""
        for p in self._load_orca_filaments():
            if p.get("vendor") == vendor and p.get("name") == name:
                return p.get("id", "")
        return ""

    async def handle_kx_history(self, request):
        limit  = int(request.rel_url.query.get("limit", 50))
        offset = int(request.rel_url.query.get("offset", 0))
        jobs   = self._store.list_jobs(limit=limit, offset=offset)
        return self._json_cors({"result": jobs})

    async def handle_kx_file_objects(self, request):
        """Liefert die Objekt-Liste + optionales SVG für eine Datei.

        GET /kx/files/{id}/objects → {"names": [...], "svg_b64": "..."}
        Wenn Datei noch keine Objekte hat (alter Eintrag): file/fileDetails
        beim Drucker abfragen und Antwort abwarten ist Aufgabe des Frontends
        (Reload nach Upload). Hier nur Datenbankstand zurückgeben.
        """
        fid = request.match_info.get("id", "")
        f = self._store.get_file(fid)
        if not f:
            return self._json_cors({"error": "file not found"}, status=404)
        try:
            names = json.loads(f.get("objects_skip_parts") or "[]")
        except Exception:
            names = []
        return self._json_cors({
            "result": {
                "names":   names,
                "svg_b64": f.get("svg_image") or "",
            }
        })

    async def handle_kx_skip(self, request):
        """Mid-Print Skip auslösen.

        POST /kx/skip  body={"names": ["..", ".."]}
        """
        try:
            body = await request.json()
        except Exception:
            return self._json_cors({"error": "invalid json"}, status=400)
        names = body.get("names") or []
        if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
            return self._json_cors({"error": "names must be list[str]"}, status=400)
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: self.client.skip_objects(names))
        except Exception as e:
            return self._json_cors({"error": str(e)}, status=502)
        return self._json_cors({"result": "ok", "names": names})

    async def handle_kx_skip_query(self, request):
        """Druck-Objektliste vom Drucker neu abfragen.

        POST /kx/skip/query  → triggert skip/query_obj, gibt zuletzt bekannten
        Stand zurück (skip/report kommt async, Frontend pollt /kx/skip/state).
        """
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: self.client.query_skip_objects())
        except Exception as e:
            return self._json_cors({"error": str(e)}, status=502)
        return self._json_cors({"result": self._skip_state})

    async def handle_kx_skip_state(self, request):
        """Aktueller Skip-State.

        Kombiniert:
        - Gesamt-Objektliste: aus dem GCode-Store, gematcht über den aktuell
          laufenden filename (file/report beim Druckstart hat die Liste gefüllt).
          skip/query_obj liefert nämlich NUR die bereits geskippten zurück,
          nicht die Gesamtliste.
        - Geskippt: aus self._skip_state (von skip/report aktualisiert).
        """
        filename = self._state.get("filename", "")
        all_objects: list[str] = []
        svg = ""
        if filename:
            try:
                f = self._store.get_file_by_name(filename)
                if f:
                    all_objects = json.loads(f.get("objects_skip_parts") or "[]")
                    svg = f.get("svg_image") or ""
            except Exception as e:
                log.warning(f"skip_state lookup failed: {e}")
        result = {
            "objects":  all_objects,
            "skipped":  list(self._skip_state.get("skipped", [])),
            "svg_b64":  svg,
            "ts":       self._skip_state.get("ts", 0),
            "filename": filename,
        }
        return self._json_cors({"result": result})

    async def handle_kx_printers(self, request):
        # Aktive Drucker (mit IP) sammeln
        active = [(pid, br) for pid, br in self._all_bridges.items()
                  if (br._args.printer_ip or "").strip()]
        # Host für bridge_url: Browser-Sicht beibehalten, aber niemals "localhost" exportieren –
        # sonst scheitern Fetches aus dem Browser, wenn die UI über die LAN-IP geöffnet ist.
        host = request.host.split(":")[0]
        if host in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
            host = ""
        out = []
        for pid, br in active:
            port = getattr(br._args, "port", 7125)
            # Nur bei Multi-Printer eine konkrete bridge_url setzen (Cross-Instance-Fetch).
            # Single-Printer: leere bridge_url → JS nutzt relative Pfade (gleiche Origin wie UI).
            bridge_url = ""
            if len(active) > 1 and host:
                bridge_url = f"http://{host}:{port}"
            out.append({
                "id":         pid,
                "name":       br._state.get("printer_name") or f"Drucker {pid}",
                "bridge_url": bridge_url,
                "printer_ip": br._args.printer_ip,
                "device_id":  br._args.device_id or "",
            })
        return self._json_cors({"result": out})

    async def handle_kx_print(self, request):
        """Druckstart aus dem GCode-Store mit optionalen Filament-Assignments."""
        try:
            body = await request.json()
        except Exception:
            return self._json_cors({"error": "invalid json"}, status=400)

        file_id = body.get("file_id")
        if not file_id:
            return self._json_cors({"error": "file_id required"}, status=400)

        gcode_file = self._store.get_file(file_id)
        if not gcode_file:
            return self._json_cors({"error": "file not found"}, status=404)

        # filament_assignments: [{slot_index, material, color_hex}, …]
        assignments = body.get("filament_assignments")
        # excluded_objects: ["name1","name2",...] – Pre-Print Skip (v0.9.10)
        excluded_objects = body.get("excluded_objects") or []
        if not isinstance(excluded_objects, list):
            excluded_objects = []

        if assignments:
          ams_box_mapping, unused_count, invalid_count = self._build_assigned_ams_box_mapping(assignments)
          if unused_count:
            log.debug(f"Skipped {unused_count} unused filament assignment(s) for mode={self._filament_mode}")
          if invalid_count:
            log.warning(f"Ignored {invalid_count} unusable filament assignment(s) for mode={self._filament_mode}")
            if not ams_box_mapping:
                return self._json_cors({"error": "no usable filament assignments for current filament mode"}, status=400)
        else:
            # Kein Dialog → alle belegten Slots wie bei normalem Upload-Druck
            ams_box_mapping = self._build_auto_ams_box_mapping()

        use_ams = len(ams_box_mapping) > 0
        auto_leveling = getattr(self._args, "auto_leveling", 1)
        filename = gcode_file["filename"]
        file_path = gcode_file["path"]

        # Datei über internes Serve-Endpoint bereitstellen
        url = f"http://localhost:{self._args.port}/serve/{os.path.basename(file_path)}"

        payload = {
            "taskid":       "-1",
            "url":          url,
            "filename":     filename,
            "md5":          "",
            "filepath":     None,
            "filetype":     1,
            "project_type": 1,
            "filesize":     gcode_file.get("size_bytes", 0),
            "ams_settings": {
                "use_ams":         use_ams,
                "ams_box_mapping": ams_box_mapping,
            },
            "task_settings": {
                "auto_leveling":          auto_leveling,
                "vibration_compensation": 0,
                "flow_calibration":       0,
                "dry_mode":               0,
                "ai_settings":   {"status": 0, "count": 0, "type": 1},
                "timelapse":     {"status": 0, "count": 0, "type": 64},
                "drying_settings": {"status": 0, "target_temp": 0, "duration": 0, "remain_time": 0},
                "model_objects_skip_parts": excluded_objects,
            },
        }

        log.info(f"KX-Store Druckstart: {filename}  ams={len(ams_box_mapping)} slots  assignments={bool(assignments)}  excluded={len(excluded_objects)}")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, lambda: self.client.publish("print", "start", payload, timeout=15.0)
        )
        if result is None:
            return self._json_cors({"error": "Keine Antwort vom Drucker"}, status=504)

        # Job in History starten
        self._current_job_id = self._store.start_job(
            gcode_file_id=gcode_file["id"],
            printer_id=getattr(self._args, "device_id", "unknown"),
            filament_assignments=assignments,
        )

        return self._json_cors({"result": "ok", "filename": filename})

    # -------------------------------------------------------------------------
    # HTTP handlers
    # -------------------------------------------------------------------------

    async def handle_server_info(self, request):
        return web.json_response({
            "result": {
                "klippy_connected": True,
                "klippy_state":     "ready",
                "components":       ["file_manager", "job_state", "virtual_sdcard"],
                "failed_components":[],
                "registered_directories": ["gcodes"],
                "warnings":         [],
                "websocket_count":  len(self.ws_clients),
                "moonraker_version": MOONRAKER_VERSION,
                "api_version":      [1, 3, 0],
                "api_version_string": "1.3.0",
            }
        })

    async def handle_printer_info(self, request):
        s = self._state
        return web.json_response({
            "result": {
                "state":           "ready",
                "state_message":   "Printer is ready",
                "hostname":        "kobrax-bridge",
                "klipper_path":    "/home/pi/klipper",
                "python_path":     "/home/pi/klippy-env/bin/python",
                "log_file":        "/tmp/klippy.log",
                "config_file":     "/home/pi/printer.cfg",
                "software_version": KLIPPER_VERSION,
                "cpu_info":        s["printer_name"],
            }
        })

    async def handle_machine_system_info(self, request):
        return web.json_response({
            "result": {
                "system_info": {
                    "cpu_info": {"cpu_count": 4, "bits": "64bit", "processor": "armv7l",
                                 "cpu_desc": "Anycubic Kobra X Bridge", "serial_number": "",
                                 "hardware_desc": "", "model": "Kobra X Bridge",
                                 "total_memory": 524288, "memory_units": "kB"},
                    "sd_info": {},
                    "distribution": {"name": "Linux", "id": "linux", "version": "1.0",
                                     "version_parts": {}, "like": "", "codename": ""},
                    "available_services": [],
                    "service_state": {},
                    "python": {"version": list(sys.version_info[:3]), "version_string": sys.version},
                    "network": {},
                    "canbus": {},
                }
            }
        })

    async def handle_objects_query(self, request):
        objects = self._build_printer_objects()
        requested = []
        query = request.rel_url.query
        if "objects" in query:
            requested = [x.strip() for x in str(query.get("objects", "")).split(",") if x.strip()]
        elif query:
            requested = [k for k in query.keys() if k]

        filtered = {k: objects[k] for k in requested if k in objects} if requested else objects
        return web.json_response({"result": {"status": filtered, "eventtime": time.time()}})

    async def handle_objects_list(self, request):
        return web.json_response({
            "result": {
                "objects": list(self._build_printer_objects().keys())
            }
        })

    async def handle_objects_subscribe(self, request):
        return web.json_response({
            "result": {
                "status": self._build_printer_objects(),
                "eventtime": time.time(),
            }
        })

    async def handle_files_list(self, request):
        filename = self._state.get("filename", "")
        files = []
        if filename:
            files.append({
                "path":     filename,
                "modified": time.time(),
                "size":     0,
                "permissions": "rw",
            })
        return web.json_response({"result": files})

    async def handle_files_metadata(self, request):
        """Moonraker /server/files/metadata — moonraker-obico-Plugin holt das
        einmal pro Druck und liest daraus `object_height` (für `currentZ`-
        Anzeige im Obico-UI: `mmProgress` braucht maxZ), `layer_count`,
        `layer_height` und `first_layer_height` (für die Layer-Berechnung).

        Quelle: aktueller `_state` + GCode-Store-Eintrag wenn vorhanden.
        Wenn Layer-Heights weder im State noch im Store sind, Fallback auf die
        OrcaSlicer-Default-Filename-Heuristik (`_layer_height_from_filename`)."""
        filename = request.rel_url.query.get("filename", "") or self._state.get("filename", "")
        if not filename:
            return web.json_response({"result": {}})
        s = self._state
        layer_h = float(s.get("layer_height") or 0.0)
        first_h = float(s.get("first_layer_height") or 0.0)
        total_layers = int(s.get("total_layers") or 0)
        est_time = int(s.get("slicer_time") or 0)
        size_bytes = 0
        try:
            gf = self._store.get_file_by_name(filename) or {}
            if not layer_h:
                layer_h = float(gf.get("layer_height") or 0.0)
                first_h = float(gf.get("first_layer_height") or layer_h)
            if not total_layers:
                total_layers = int(gf.get("layer_count") or 0)
            if not est_time:
                est_time = int(gf.get("est_print_time_sec") or 0)
            size_bytes = int(gf.get("size_bytes") or 0)
        except Exception:
            pass
        if not layer_h:
            layer_h = self._layer_height_from_filename(filename)
            if layer_h and not first_h:
                first_h = layer_h
        object_height = round(first_h + max(0, total_layers - 1) * layer_h, 3) if (layer_h and total_layers) else 0.0
        return web.json_response({"result": {
            "filename":           filename,
            "size":               size_bytes,
            "modified":           time.time(),
            "estimated_time":     est_time or None,
            "layer_height":       layer_h or None,
            "first_layer_height": first_h or None,
            "layer_count":        total_layers or None,
            "object_height":      object_height or None,
        }})

    # ── Moonraker-Stubs für moonraker-obico ──────────────────────────────────
    async def handle_access_api_key(self, request):
        """Moonraker /access/api_key — wir haben keine Auth, geben einen Dummy zurück.
        moonraker-obico stellt sonst eine WARNING ins Log."""
        return web.json_response({"result": "kx-bridge-no-auth-required"})

    async def handle_machine_update_status(self, request):
        """Moonraker /machine/update/status — Obico zeigt installierte Plugins damit."""
        return web.json_response({
            "result": {
                "busy":         False,
                "github_rate_limit":     60,
                "github_requests_remaining": 60,
                "github_limit_reset_time":   time.time() + 3600,
                "version_info": {},
            }
        })

    async def handle_history_list(self, request):
        """Moonraker /server/history/list — Job-Historie aus dem GCodeStore.

        moonraker-obico nutzt nur das letzte Element (limit=1, order=desc)."""
        try:
            limit = int(request.rel_url.query.get("limit", "50"))
        except ValueError:
            limit = 50
        try:
            jobs = self._store.list_jobs(limit=limit) or []
        except Exception:
            jobs = []
        # Mapping auf Moonraker-Schema. Moonraker liefert start_time als Unix-
        # Timestamp (float), nicht ISO-String — moonraker-obico parsed das mit
        # int(start_time) und crasht sonst.
        def _to_unix_ts(iso: str | None) -> float:
            if not iso:
                return 0.0
            try:
                from datetime import datetime
                # Format aus GCodeStore: "2026-05-27T21:22:25Z"
                dt = datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ")
                return dt.replace(tzinfo=__import__("datetime").timezone.utc).timestamp()
            except Exception:
                return 0.0
        result_jobs = []
        for j in jobs:
            start_ts = _to_unix_ts(j.get("started_at"))
            dur = j.get("duration_sec") or 0
            result_jobs.append({
                "job_id":       j.get("id"),
                "exists":       True,
                "end_time":     (start_ts + dur) if start_ts and dur else None,
                "filament_used": 0.0,
                "filename":     j.get("filename", ""),
                "metadata":     {},
                "print_duration": dur,
                "status":       j.get("status") or "completed",
                "start_time":   start_ts,
                "total_duration": dur,
            })
        return web.json_response({"result": {"count": len(result_jobs), "jobs": result_jobs}})

    async def handle_webcams_list(self, request):
        """Moonraker /server/webcams/list — Obico holt die Webcam-URLs hier.

        Wenn der Client von einem anderen Host kommt (z.B. moonraker-obico auf
        separatem Server), braucht er absolute URLs damit er den Stream erreicht.
        Host-Header mit localhost/127.0.0.1 wird durch die echte LAN-IP ersetzt."""
        host_hdr = request.headers.get("Host", "") if request else ""
        host_name = (host_hdr or "").split(":")[0]
        port_part = f":{host_hdr.split(':')[1]}" if ":" in (host_hdr or "") else f":{self._args.port}"
        local_ip  = getattr(self, "_local_ip", None) or host_name
        if host_name in ("localhost", "127.0.0.1", ""):
            host_name = local_ip
        base         = f"http://{host_name}{port_part}"
        stream_url   = f"{base}/api/camera/stream"
        snapshot_url = f"{base}/api/camera/snapshot"
        return web.json_response({
            "result": {
                "webcams": [
                    {
                        "name":         "KX-Bridge",
                        "location":     "printer",
                        "service":      "mjpegstreamer",
                        "enabled":      True,
                        "icon":         "mdiWebcam",
                        "target_fps":   5,
                        "target_fps_idle": 2,
                        "stream_url":   stream_url,
                        "snapshot_url": snapshot_url,
                        "flip_horizontal": False,
                        "flip_vertical":   False,
                        "rotation":     0,
                        "aspect_ratio": "16:9",
                        "extra_data":   {},
                    }
                ]
            }
        })

    async def handle_file_upload(self, request):
        log.info(f"Upload-Request: {request.method} {request.path_qs}  CT={request.headers.get('Content-Type','')[:60]}")
        ct = request.headers.get("Content-Type", "")
        if "multipart" not in ct:
            return web.json_response({"error": "expected multipart"}, status=400)
        auto_print = False
        web_upload = False
        reader = await request.multipart()
        file_data = None
        remote_filename = self._last_uploaded_file or "upload.gcode"

        async for part in reader:
            if part.name in ("file", "gcode", "upload_file"):
                remote_filename = part.filename or remote_filename
                file_data = await part.read()
                log.info(f"Multipart-Feld '{part.name}': {remote_filename} ({len(file_data)} bytes)")
            elif part.name == "path":
                val = (await part.read()).decode("utf-8", errors="replace").strip()
                if val:
                    remote_filename = val
            elif part.name == "print":
                val = (await part.read()).decode("utf-8", errors="replace").strip().lower()
                auto_print = val == "true"
            elif part.name == "web_upload":
                val = (await part.read()).decode("utf-8", errors="replace").strip().lower()
                web_upload = val == "true"
            else:
                log.debug(f"Unbekanntes Multipart-Feld: {part.name}")

        if not file_data:
            return web.json_response({"error": "no file received"}, status=400)

        file_md5   = hashlib.md5(file_data).hexdigest()
        file_size  = len(file_data)

        # Slicer-Zeitschätzung + Thumbnail aus GCode auslesen
        est_time = _parse_gcode_estimated_time(file_data)
        self._state["slicer_time"] = est_time
        thumbnail_b64 = _extract_thumbnail(file_data)
        gcode_filaments = _extract_filament_info(file_data)
        layer_h, first_h = _parse_gcode_layer_heights(file_data)
        self._state["layer_height"] = layer_h
        self._state["first_layer_height"] = first_h

        # Datei persistent im GCode-Store ablegen
        self._store.save_file(
            file_id=file_md5,
            filename=remote_filename,
            data=file_data,
            est_time_sec=est_time,
            thumbnail_b64=thumbnail_b64,
            gcode_filaments=gcode_filaments or None,
            web_unverified=web_upload,
            layer_height=layer_h,
            first_layer_height=first_h,
        )
        serve_path = os.path.join(self._serve_dir_path, os.path.basename(remote_filename))
        del file_data  # RAM freigeben

        self._last_uploaded_file = remote_filename
        log.info(f"Upload: {remote_filename} ({file_size} bytes) md5={file_md5} → Store + Drucker")

        # Datei per HTTP auf den Drucker hochladen (serve_path liegt bereits auf Disk)
        upload_url = self._state.get("upload_url") or None
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                None, self.client.upload_gcode, serve_path, remote_filename, upload_url
            )
        except Exception as e:
            log.error(f"Upload fehlgeschlagen: {e}")
            return web.json_response({"error": str(e)}, status=500)

        log.info(f"Upload erfolgreich: {result}")

        # Druck starten mit vollständigem Payload (inkl. serve-URL + md5 + size)
        serve_url = f"http://{request.host}/serve/{remote_filename}"

        # print=true im Multipart-Formular (Moonraker) oder Query-String → Druck starten
        # print=false oder fehlt → nur hochladen
        if not auto_print:
            auto_print = request.rel_url.query.get("print", "false").lower() == "true"

        # Thumbnail immer anfordern (Drucker antwortet async mit file/report)
        self._thumbnail_b64 = ""
        self.client.publish("file", "fileDetails", {"root": "local", "filename": remote_filename}, timeout=0)

        self._state["last_upload_url"]  = serve_url
        self._state["last_upload_md5"]  = file_md5
        self._state["last_upload_size"] = file_size

        if auto_print:
            log.info(f"Upload+Print (print=true): {remote_filename}")
            self._state["file_ready"] = ""
            loop = asyncio.get_event_loop()
            loop.run_in_executor(None, lambda: self._start_print(remote_filename, serve_url, file_md5, file_size, gcode_filaments=gcode_filaments))
        else:
            log.info(f"Nur hochgeladen (print=false): {remote_filename}")
            self._state["file_ready"] = remote_filename

        # OctoPrint-kompatibler Response (OrcaSlicer wertet refs aus)
        return web.json_response({
            "done": True,
            "files": {
                "local": {
                    "name": remote_filename,
                    "origin": "local",
                    "path": remote_filename,
                    "refs": {
                        "download": f"http://{request.host}/api/files/local/{remote_filename}",
                        "resource":  f"http://{request.host}/api/files/local/{remote_filename}",
                    }
                }
            },
            "result": {
                "item": {"path": remote_filename, "root": "gcodes"},
                "action": "create_file",
            }
        }, status=201)

    def _start_print(self, filename: str, url: str = "", md5: str = "", filesize: int = 0,
                     gcode_filaments: list | None = None):
        self._state["file_ready"] = ""
        loaded = self._select_loaded_slots_for_print(warn_on_empty_default=True)

        # Nur die im GCode TATSÄCHLICH genutzten Paints auf Slots mappen. OrcaSlicer
        # schreibt im Header alle konfigurierten Filamente (filament_colour=…;…;…;…),
        # nutzt aber oft nur eines (z.B. einfarbig → nur T3). Würden wir alle
        # belegten Slots mappen, erwartet der Drucker alle Farben und blockiert,
        # wenn ein anderer (ungenutzter) Slot leer ist. Die genutzten Paint-Indizes
        # liefert _extract_filament_info via is_used (echte T<n>-Tool-Changes).
        used_paint_indices = None
        if gcode_filaments:
            used = [int(f["slot_index"]) for f in gcode_filaments
                    if f.get("is_used") and "slot_index" in f]
            if used:
                used_paint_indices = set(used)

        if used_paint_indices is not None:
            # GCode-Paint-Index N entspricht AMS-Slot N (global_index). Nur belegte
            # genutzte Slots mappen; nicht-belegte genutzte → später Warnung möglich.
            loaded = [(gidx, s) for (gidx, s) in loaded if gidx in used_paint_indices]

        use_ams = len(loaded) > 0
        ams_box_mapping = self._build_auto_ams_box_mapping(loaded_slots=loaded)
        log.debug(f"AMS-Slots: {len(loaded)} gemappt (genutzte Paints: {used_paint_indices}) → {[i for i, _ in loaded]}")
        auto_leveling = getattr(self._args, "auto_leveling", 1)
        payload = {
            "taskid":       "-1",
            "url":          url,
            "filename":     filename,
            "md5":          md5,
            "filepath":     None,
            "filetype":     1,
            "project_type": 1,
            "filesize":     filesize,
            "ams_settings": {
                "use_ams":        use_ams,
                "ams_box_mapping": ams_box_mapping,
            },
            "task_settings": {
                "auto_leveling":            auto_leveling,
                "vibration_compensation":   0,
                "flow_calibration":         0,
                "dry_mode":                 0,
                "ai_settings":   {"status": 0, "count": 0, "type": 1},
                "timelapse":     {"status": 0, "count": 0, "type": 64},
                "drying_settings": {"status": 0, "target_temp": 0, "duration": 0, "remain_time": 0},
                "model_objects_skip_parts": [],
            },
        }
        log.info(f"print/start → {filename}  url={url}  ams={len(ams_box_mapping)} slots  mode={self._filament_mode}")
        result = self.client.publish("print", "start", payload, timeout=15.0)
        if result:
            log.info(f"Print start confirmed: state={result.get('state')}")
        else:
            log.warning("Druckstart: keine Antwort vom Drucker")

    def _theme_index_path(self) -> str:
        return os.path.join(_WEB_BASE, "web", "themes", self._ui_theme, "index.html")

    def _load_index_template_cached(self) -> str:
        path = self._theme_index_path()
        mtime = os.path.getmtime(path)
        key = (path, mtime)
        if self._index_tpl_cache is not None and self._index_tpl_cache_key == key:
            return self._index_tpl_cache
        with open(path, "r", encoding="utf-8") as f:
            self._index_tpl_cache = f.read()
        self._index_tpl_cache_key = key
        return self._index_tpl_cache

    def _ui_asset_cache_buster(self) -> str:
        base = os.path.join(_WEB_BASE, "web", "themes", self._ui_theme)
        mt = 0.0
        for fn in ("index.html", "style.css", "app.js"):
            try:
                mt = max(mt, os.path.getmtime(os.path.join(base, fn)))
            except OSError:
                pass
        return str(int(mt)) if mt else "0"

    async def handle_print_start(self, request):
        try:
            body = await request.json()
        except Exception:
            body = {}
        filename = (request.rel_url.query.get("filename")
                    or body.get("filename")
                    or self._last_uploaded_file)
        if not filename:
            return web.json_response({"error": "no filename"}, status=400)

        log.info(f"Druck starten: {filename}")

        # Optionale Slot-Auswahl aus dem Filament-Dialog
        filament_assignments = body.get("filament_assignments")
        # Pre-Print Skip (v0.9.10)
        excluded_objects = body.get("excluded_objects") or []
        if not isinstance(excluded_objects, list):
            excluded_objects = []
        if filament_assignments is not None:
          ams_box_mapping, unused_count, invalid_count = self._build_assigned_ams_box_mapping(filament_assignments)
          if unused_count:
            log.debug(f"Skipped {unused_count} unused filament assignment(s) for mode={self._filament_mode}")
          if invalid_count:
            log.warning(f"Ignored {invalid_count} unusable filament assignment(s) for mode={self._filament_mode}")
            if not ams_box_mapping:
                return web.json_response({"error": "no usable filament assignments for current filament mode"}, status=400)
        else:
            # AMS-Mapping aus gecachtem State — leere Slots (status != 5) überspringen
            ams_box_mapping = self._build_auto_ams_box_mapping()

        use_ams = len(ams_box_mapping) > 0
        auto_leveling = getattr(self._args, "auto_leveling", 1)
        url = self._state.get("last_upload_url", "")
        filesize = self._state.get("last_upload_size", 0)
        md5 = self._state.get("last_upload_md5", "")

        payload = {
            "taskid":       "-1",
            "url":          url,
            "filename":     filename,
            "md5":          md5,
            "filepath":     None,
            "filetype":     1,
            "project_type": 1,
            "filesize":     filesize,
            "ams_settings": {
                "use_ams":         use_ams,
                "ams_box_mapping": ams_box_mapping,
            },
            "task_settings": {
                "auto_leveling":          auto_leveling,
                "vibration_compensation": 0,
                "flow_calibration":       0,
                "dry_mode":               0,
                "ai_settings":   {"status": 0, "count": 0, "type": 0},
                "timelapse":     {"status": 0, "count": 0, "type": 0},
                "drying_settings": {"status": 0, "target_temp": 0, "duration": 0, "remain_time": 0},
                "model_objects_skip_parts": excluded_objects,
            },
        }

        log.info(
          f"print/start api=1 mode={self._filament_mode} "
          f"ams={len(ams_box_mapping)} slots assignments={filament_assignments is not None}"
        )

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, lambda: self.client.publish("print", "start", payload, timeout=15.0)
        )
        if result is None:
            return web.json_response({"error": "Keine Antwort vom Drucker"}, status=504)

        return web.json_response({"result": "ok"})

    async def handle_print_pause(self, request):
        loop = asyncio.get_event_loop()
        taskid = self._state.get("taskid", "-1")
        await loop.run_in_executor(None, lambda: self.client.pause_print(taskid))
        return web.json_response({"result": "ok"})

    async def handle_print_resume(self, request):
        loop = asyncio.get_event_loop()
        taskid = self._state.get("taskid", "-1")
        await loop.run_in_executor(None, lambda: self.client.resume_print(taskid))
        return web.json_response({"result": "ok"})

    async def handle_print_cancel(self, request):
        loop = asyncio.get_event_loop()
        taskid = self._state.get("taskid", "-1")
        await loop.run_in_executor(None, lambda: self.client.stop_print(taskid))
        return web.json_response({"result": "ok"})

    async def handle_api_file_ready_clear(self, request):
        self._state["file_ready"] = ""
        self._thumbnail_b64 = ""
        self._push_status_update()
        return web.json_response({"result": "ok"})

    async def handle_octoprint_version(self, request):
        return web.json_response({
            "api":     "0.1",
            "server":  "1.9.0",
            "text":    "OctoPrint (Kobra X Bridge)",
        })

    async def handle_kx_ui_asset(self, request):
        name = request.match_info.get("name", "").lstrip("/")
        ctype = _KX_UI_ASSETS.get(name)
        cache_control = "public, max-age=86400"

        if ctype is not None:
            path = os.path.join(_WEB_BASE, "web", "themes", self._ui_theme, name)
        else:
            m = _KX_UI_TRANSLATION_RE.match(name)
            if not m:
                raise web.HTTPNotFound()
            lang = m.group(1)
            ctype = "application/json"
            cache_control = "no-store"
            path = os.path.join(_WEB_BASE, "web", "translations", f"{lang}.json")

        try:
            raw = pathlib.Path(path).read_text(encoding="utf-8")
        except OSError:
            raise web.HTTPNotFound()
        if name == "app.js":
            raw = raw.replace("'__VERSION__'", f"'{self._read_version()}'")
        return web.Response(
            text=raw,
            content_type=ctype,
            headers={"Cache-Control": cache_control},
        )

    async def handle_index(self, request):
        try:
            tpl = self._load_index_template_cached()
        except OSError:
            p = self._theme_index_path()
            log.error("Web-UI Theme-Datei fehlt oder nicht lesbar: %s (Theme: %s)", p, self._ui_theme)
            return web.Response(
                text="<pre>KX-Bridge: index.html nicht gefunden.\nErwartet:\n"
                + html.escape(p, quote=True)
                + "</pre>",
                status=500,
                content_type="text/html; charset=utf-8",
            )
        page = tpl.replace("__UI_ASSETS_VER__", self._ui_asset_cache_buster())

        # CSS + JS INLINE einbetten statt nur zu verlinken. OrcaSlicers
        # eingebetteter Device-Tab-Webview lädt externe <link>/<script src>
        # NICHT (nur das nackte HTML) → ohne Inlining funktioniert dort kein
        # einziger Button (Issue #29). Im normalen Browser ist es ebenso korrekt.
        base = os.path.join(_WEB_BASE, "web", "themes", self._ui_theme)
        try:
            css = pathlib.Path(os.path.join(base, "style.css")).read_text(encoding="utf-8")
            page = page.replace(
                '<link rel="stylesheet" href="/kx/ui/style.css">',
                "<style>\n" + css + "\n</style>")
        except OSError:
            pass
        try:
            js = pathlib.Path(os.path.join(base, "app.js")).read_text(encoding="utf-8")
            js = js.replace("'__VERSION__'", f"'{self._read_version()}'")
            page = page.replace(
                '<script src="/kx/ui/app.js"></script>',
                "<script>\n" + js + "\n</script>")
        except OSError:
            pass

        return web.Response(text=page, content_type="text/html",
                            headers={"Cache-Control": "no-store, no-cache, must-revalidate"})

    async def handle_api_light(self, request):
        try:
            body = await request.json()
        except Exception:
            body = {}
        on         = bool(body.get("on", True))
        brightness = int(body.get("brightness", self._state["light_brightness"]))
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: self.client.publish(
            "light", "control",
            {"type": 3, "status": 1 if on else 0, "brightness": brightness},
            timeout=0
        ))
        self._state["light_on"]         = on
        self._state["light_brightness"] = brightness
        return web.json_response({"result": "ok"})

    async def handle_api_fan(self, request):
        try:
            body = await request.json()
        except Exception:
            body = {}
        speed = int(body.get("speed", 0))
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: self.client.publish(
            "fan", "setSpeed", {"fan_speed_pct": speed}, timeout=0
        ))
        self._state["fan_speed"] = speed
        return web.json_response({"result": "ok"})

    async def handle_api_connect(self, request):
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(None, self.client.connect)
            self._state["print_state"] = "standby"
            self._state["kobra_state"] = "free"
            log.info("Manuell verbunden")
            return web.json_response({"result": "connected"})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def handle_api_disconnect(self, request):
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(None, self.client.disconnect)
        except Exception:
            pass
        self._state["print_state"] = "error"
        self._state["kobra_state"] = "offline"
        log.info("Manuell getrennt")
        return web.json_response({"result": "disconnected"})

    async def handle_api_restart(self, request):
        log.info("Restart requested via API")
        response = web.json_response({"status": "restarting"})
        asyncio.get_event_loop().call_later(0.3, self._restart_bridge)
        return response

    async def handle_api_speed(self, request):
        try:
            body = await request.json()
        except Exception:
            body = {}
        mode = int(body.get("mode", 2))
        loop = asyncio.get_event_loop()
        taskid = self._state.get("taskid", "-1")
        await loop.run_in_executor(None, lambda: self.client.publish_web(
            "print", "update",
            {"taskid": taskid, "settings": {"print_speed_mode": mode}},
        ))
        self._state["print_speed_mode"] = mode
        return web.json_response({"result": "ok"})

    async def handle_api_ams_set_slot(self, request):
        try:
            body = await request.json()
        except Exception:
            body = {}
        index  = int(body.get("index", 0))   # global slot index
        mat    = str(body.get("type", "PLA")).upper()
        color  = body.get("color", [255, 255, 255])
        if not (isinstance(color, list) and len(color) == 3):
            return web.json_response({"error": "color must be [r,g,b]"}, status=400)
        box_id, local_slot = self._global_to_box_slot(index)
        loop = asyncio.get_event_loop()
        # setInfo geht über web/printer-Topic (wie tempature/set). Per
        # Workbench-Vue mqtt_setInfo verifiziert — via slicer/printer/ wurden
        # die Slot-Änderungen vom Drucker ignoriert und beim nächsten
        # multiColorBox/report mit dem alten Material überschrieben.
        def _send():
            self.client.publish_web(
                "multiColorBox", "setInfo",
                {"multi_color_box": [{"id": box_id, "slots": [{"index": local_slot, "type": mat, "color": color}]}]},
            )
            log.info(f"setInfo (web) global={index} box={box_id} local_slot={local_slot} type={mat} color={color}")
        await loop.run_in_executor(None, _send)
        # Optimistisches Update: cached slot sofort anpassen (Drucker echoed
        # gleich via multiColorBox/report — falls er den Befehl ignoriert,
        # überschreibt der Report das wieder).
        for s in self._ams_slots:
            if s.get("global_index") == index:
                s["type"]  = mat
                s["color"] = color
                break
        return web.json_response({"result": "ok"})

    async def handle_api_ams_feed(self, request):
        try:
            body = await request.json()
        except Exception:
            body = {}
        slot_index = int(body.get("slot_index", 0))
        feed_type  = int(body.get("type", 1))
        if feed_type == 1:
          self._pending_load_slot = slot_index
        # Ausziehen (type=2): wenn kein Slot explizit gewählt, den zuletzt geladenen nehmen
        if feed_type == 2 and self._ams_loaded_slot >= 0:
            slot_index = self._ams_loaded_slot
        box_id, local_slot = self._global_to_box_slot(slot_index)
        loop = asyncio.get_event_loop()
        def _send():
            resp = self.client.publish(
                "multiColorBox", "feedFilament",
                {"multi_color_box": [{"id": box_id, "feed_status": {"slot_index": local_slot, "type": feed_type}}]},
                timeout=5
            )
            log.info(f"feedFilament type={feed_type} global_slot={slot_index} box={box_id} local_slot={local_slot} loaded_slot={self._ams_loaded_slot} → {resp}")
        await loop.run_in_executor(None, _send)
        return web.json_response({"result": "ok"})

    async def handle_api_ace_auto_feed(self, request):
        try:
            body = await request.json()
        except Exception:
            body = {}

        ace_id_raw = body.get("ace_id", None)
        on_raw = body.get("on", None)
        if ace_id_raw is None or on_raw is None:
            return web.json_response({"error": "ace_id and on are required"}, status=400)
        try:
            ace_id = int(ace_id_raw)
            on = int(bool(on_raw))
        except Exception:
            return web.json_response({"error": "invalid parameters"}, status=400)
        if not (0 <= ace_id <= 3):
            return web.json_response({"error": "ace_id must be 0-3"}, status=400)

        payload = {"multi_color_box": [{"id": ace_id, "auto_feed": on}]}
        loop = asyncio.get_event_loop()
        # Fire-and-forget: setAutoFeed ACK arrives via multiColorBox/report callback.
        # Waiting for a response on that busy push topic causes false "code:0" rejections.
        await loop.run_in_executor(
            None,
            lambda: self.client.publish("multiColorBox", "setAutoFeed", payload, timeout=0)
        )
        self._ace_auto_feed[ace_id] = on
        self._state_dirty = True
        return web.json_response({"result": "ok", "ace_id": ace_id, "auto_feed": on})

    async def handle_api_ace_dry(self, request):
        try:
            body = await request.json()
        except Exception:
            body = {}

        action = str(body.get("action", "start")).lower()
        if action not in ("start", "stop"):
            return web.json_response({"error": "action must be 'start' or 'stop'"}, status=400)

        ace_ids = [i for i in self._ace_box_ids if 0 <= i <= 3]
        if not ace_ids:
            ace_ids = sorted({
                int(s.get("box_id", -1))
                for s in self._ams_slots
                if 0 <= int(s.get("box_id", -1)) <= 3
            })
        if not ace_ids and self._state.get("filament_mode") != "toolhead":
            ace_ids = [0]
        if not ace_ids:
            return web.json_response({"error": "ACE not detected"}, status=400)

        ace_id_raw = body.get("ace_id", None)
        if ace_id_raw is not None:
          try:
            ace_id = int(ace_id_raw)
          except Exception:
            return web.json_response({"error": "ace_id must be an integer"}, status=400)
          if ace_id not in ace_ids:
            return web.json_response({"error": f"ACE {ace_id + 1} not detected"}, status=400)
          ace_ids = [ace_id]

        if action == "start":
            target_temp = int(body.get("target_temp", 45))
            duration = int(body.get("duration", 240))
            target_temp = max(30, min(80, target_temp))
            duration = max(10, min(24 * 60, duration))
            humidity = (self._state.get("ace_drying") or {}).get("humidity")
            current_temp = (self._state.get("ace_drying") or {}).get("current_temp")
            drying_status = {
                "status": 1,
                "target_temp": target_temp,
                "duration": duration,
                "remain_time": duration,
            }
            ui_state = {
                "status": 1,
                "target_temp": target_temp,
                "duration": duration,
                "remain_time": duration,
                "humidity": humidity,
                "current_temp": current_temp,
            }
        else:
            drying_status = {"status": 0}
            humidity = (self._state.get("ace_drying") or {}).get("humidity")
            current_temp = (self._state.get("ace_drying") or {}).get("current_temp")
            ui_state = {
                "status": 0,
                "target_temp": 0,
                "duration": 0,
                "remain_time": 0,
                "humidity": humidity,
                "current_temp": current_temp,
            }

        payload = {
            "multi_color_box": [
                {"id": bid, "drying_status": dict(drying_status)}
                for bid in ace_ids
            ]
        }

        loop = asyncio.get_event_loop()

        def _send():
            return self.client.publish("multiColorBox", "setDry", payload, timeout=0)
        # Fire-and-forget: setDry ACK arrives via multiColorBox/report callback.
        # Waiting for a response on that busy push topic causes false "code:0" rejections.
        await loop.run_in_executor(None, _send)

        self._state["ace_drying"] = ui_state
        self._state_dirty = True
        return web.json_response({"result": "ok"})

    async def handle_api_axis(self, request):
        try:
            body = await request.json()
        except Exception:
            body = {}

        loop = asyncio.get_event_loop()
        action = str(body.get("action", "")).lower()

        if action == "turnoff":
            await loop.run_in_executor(None, lambda: self.client.publish(
                "axis", "turnOff", None, timeout=0
            ))
        else:
            axis = int(body.get("axis", 4))
            move_type = int(body.get("move_type", 2))
            distance = float(body.get("distance", 0))
            await loop.run_in_executor(None, lambda: self.client.publish(
                "axis", "move",
                {"axis": axis, "move_type": move_type, "distance": distance},
                timeout=0
            ))

        return web.json_response({"result": "ok"})

    async def handle_api_temperature(self, request):
        try:
            body = await request.json()
        except Exception:
            body = {}
        nozzle = body.get("nozzle")
        bed    = body.get("bed")
        loop = asyncio.get_event_loop()
        printing = self._state.get("print_state") == "printing"
        if printing:
            # During print: runtime update via web/printer topic, one setting at a time
            taskid = self._state.get("taskid", "-1")
            if nozzle is not None:
                n = int(float(nozzle))
                await loop.run_in_executor(None, lambda: self.client.publish_web(
                    "print", "update",
                    {"taskid": taskid, "settings": {"target_nozzle_temp": n}},
                ))
            if bed is not None:
                b = int(float(bed))
                await loop.run_in_executor(None, lambda: self.client.publish_web(
                    "print", "update",
                    {"taskid": taskid, "settings": {"target_hotbed_temp": b}},
                ))
        else:
            # Idle: tempature/set über `web/printer`-Topic mit `type`-Feld.
            # Live-Sniff 2026-05-29 vom Anycubic Slicer Next bestätigt:
            #   topic = web/printer/.../tempature
            #   data  = {"type": 0|1|2, "target_hotbed_temp": B, "target_nozzle_temp": N}
            # type-Werte (aus Workbench-Vue): 0=Nozzle, 1=Bed, 2=beide.
            # Ohne `type` ODER auf `slicer/printer`-Topic → Systemfehler am Drucker.
            if nozzle is not None and bed is not None:
                t, n, b = 2, int(float(nozzle)), int(float(bed))
            elif nozzle is not None:
                t, n, b = 0, int(float(nozzle)), 0
            elif bed is not None:
                t, n, b = 1, 0, int(float(bed))
            else:
                return web.json_response({"result": "ok"})
            await loop.run_in_executor(None, lambda: self.client.publish_web(
                "tempature", "set",
                {"type": t, "target_nozzle_temp": n, "target_hotbed_temp": b},
            ))
        return web.json_response({"result": "ok"})

    async def handle_api_camera(self, request):
        return web.json_response({"url": self._state["camera_url"]})

    async def handle_api_camera_start(self, request):
        loop = asyncio.get_event_loop()
        # Wait for pushStarted confirmation before returning
        result = await loop.run_in_executor(None, lambda: self.client.publish(
            "video", "startCapture", None, timeout=8.0
        ))
        state = (result or {}).get("state", "")
        log.info(f"Kamera startCapture: state={state}")
        return web.json_response({"result": "ok", "state": state})

    async def handle_api_camera_stop(self, request):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: self.client.publish(
            "video", "stopCapture", None, timeout=0
        ))
        # Verhindert dass der Autostart-Guard die Kamera während des
        # laufenden Drucks wieder einschaltet (State-Flicker-Problem).
        self._camera_user_stopped = True
        return web.json_response({"result": "ok"})

    async def handle_api_camera_snapshot(self, request):
        """Letzter JPEG-Frame aus dem CameraCache — instant aus dem RAM,
        keine eigene ffmpeg-Instanz mehr (verhindert Single-Client-429 am
        Drucker und ist ~1 s schneller)."""
        url = self._state.get("camera_url", "")
        if not url:
            return web.Response(status=503, text="Keine Kamera-URL bekannt")
        self.camera_cache.set_url(url)
        await self.camera_cache.ensure_running()
        # Initialer Warmup: bis zu 5 s auf ersten Frame warten
        deadline = time.time() + 5.0
        while not self.camera_cache.latest_jpeg and time.time() < deadline:
            await asyncio.sleep(0.1)
        jpeg = self.camera_cache.latest_jpeg
        if not jpeg:
            return web.Response(status=503, text="Noch kein Frame im Cache")
        # Wenn der letzte Frame älter als 10 s ist → der Cache-ffmpeg läuft
        # vermutlich nicht mehr stabil, trotzdem ausliefern aber Stale-Header.
        age = time.time() - self.camera_cache.latest_jpeg_ts
        headers = {"Cache-Control": "no-cache"}
        if age > 10:
            headers["X-Frame-Age"] = f"{age:.1f}"
        return web.Response(body=jpeg, content_type="image/jpeg", headers=headers)

    async def handle_camera_stream(self, request):
        """MJPEG proxy: FLV → MJPEG via ffmpeg, served as multipart/x-mixed-replace."""
        url = self._state.get("camera_url", "")
        if not url:
            return web.Response(status=503, text="Keine Kamera-URL bekannt")

        is_rtsp = url.lower().startswith("rtsp://")
        ffmpeg_input_args = [
            "-fflags", "nobuffer",
            "-flags", "low_delay",
        ]
        if is_rtsp:
            ffmpeg_input_args += ["-probesize", "32", "-analyzeduration", "0", "-rtsp_transport", "tcp"]
        else:
            ffmpeg_input_args += ["-probesize", "1000000", "-analyzeduration", "1000000"]

        # ffmpeg erst starten BEVOR der StreamResponse geöffnet wird
        # (damit wir bei Fehler noch eine normale HTTP-Response senden können)
        try:
            proc = await asyncio.create_subprocess_exec(
                _find_ffmpeg(), "-loglevel", "quiet",
                *ffmpeg_input_args,
                "-i", url,
                "-vf", "fps=15,scale=640:-1",
                "-f", "image2pipe",
                "-vcodec", "mjpeg",
                "-q:v", "3",
                "-flush_packets", "1",
                "pipe:1",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
        except (FileNotFoundError, OSError) as e:
            log.warning("Camera: ffmpeg not found – camera stream unavailable")
            return web.Response(status=503, text="ffmpeg not found")
        except Exception as e:
            log.warning(f"Kamera: ffmpeg konnte nicht gestartet werden: {e}")
            return web.Response(status=503, text=str(e))

        boundary = "kobraxframe"
        resp = web.StreamResponse(headers={
            "Content-Type": f"multipart/x-mixed-replace;boundary={boundary}",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        })
        await resp.prepare(request)

        buf = b""
        try:
            while True:
                chunk = await proc.stdout.read(65536)
                if not chunk:
                    break
                buf += chunk
                # Extract complete JPEG frames (SOI=FFD8, EOI=FFD9)
                while True:
                    start = buf.find(b"\xff\xd8")
                    if start == -1:
                        buf = b""
                        break
                    end = buf.find(b"\xff\xd9", start + 2)
                    if end == -1:
                        buf = buf[start:]
                        break
                    frame = buf[start:end + 2]
                    buf = buf[end + 2:]
                    header = (
                        f"--{boundary}\r\n"
                        f"Content-Type: image/jpeg\r\n"
                        f"Content-Length: {len(frame)}\r\n\r\n"
                    ).encode()
                    try:
                        await resp.write(header + frame + b"\r\n")
                    except Exception:
                        return resp
        except Exception as e:
            log.warning(f"Kamera-Stream unterbrochen: {e}")
        finally:
            try:
                proc.kill()
            except Exception:
                pass
            try:
                await proc.wait()
            except Exception:
                pass

        return resp

    async def handle_camera_h264(self, request):
        """H.264-Passthrough als MPEG-TS, gespeist aus dem zentralen
        CameraCache-Fanout. Erlaubt mehrere parallele Konsumenten ohne
        zusätzliche FLV-Verbindung zum Drucker (Single-Client-Limit)."""
        url = self._state.get("camera_url", "")
        if not url:
            return web.Response(status=503, text="Keine Kamera-URL bekannt")
        self.camera_cache.set_url(url)
        await self.camera_cache.ensure_running()

        q: asyncio.Queue[bytes] = asyncio.Queue(maxsize=64)
        self.camera_cache.h264_subscribers.add(q)

        resp = web.StreamResponse(headers={
            "Content-Type": "video/mp2t",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        })
        await resp.prepare(request)
        try:
            while True:
                chunk = await q.get()
                try:
                    await resp.write(chunk)
                except (ConnectionResetError, asyncio.CancelledError):
                    break
        except Exception as e:
            log.warning(f"H.264-Stream unterbrochen: {e}")
        finally:
            self.camera_cache.h264_subscribers.discard(q)
        return resp

    async def handle_serve_file(self, request):
        """Liefert hochgeladene G-Code-Dateien vom Temp-Verzeichnis (für Drucker-Download)."""
        filename = os.path.basename(request.match_info.get("filename", ""))
        serve_path = os.path.join(self._serve_dir_path, filename)
        if not os.path.isfile(serve_path):
            return web.Response(status=404, text="not found")
        size = os.path.getsize(serve_path)
        log.info(f"Printer downloading file: {filename} ({size} bytes)")
        return web.FileResponse(serve_path, headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        })

    async def handle_api_state(self, request):
        s = self._state
        # Slicer-Zeit + Thumbnail sind nur flüchtig im State (werden beim Upload
        # gesetzt). Nach Browser-Reload oder bei OrcaSlicer-Direktdruck (Datei kam
        # nicht über den UI-Upload) fehlen sie → aus dem GCode-Store anhand des
        # laufenden Dateinamens nachladen.
        slicer_time = s["slicer_time"]
        thumbnail = self._thumbnail_b64
        fname = s.get("filename", "")
        if fname and (not slicer_time or not thumbnail):
            try:
                gf = self._store.get_file_by_name(fname)
                if gf:
                    if not slicer_time and gf.get("est_print_time_sec"):
                        slicer_time = int(gf["est_print_time_sec"])
                    if not thumbnail and gf.get("thumbnail_b64"):
                        thumbnail = gf["thumbnail_b64"]
            except Exception:
                pass
        return web.json_response({
            "printer_name":     s["printer_name"],
            "firmware_version": s["firmware_version"],
            "print_state":      s["print_state"],
            "kobra_state":      s["kobra_state"],
            "nozzle_temp":      s["nozzle_temp"],
            "nozzle_target":    s["nozzle_target"],
            "bed_temp":         s["bed_temp"],
            "bed_target":       s["bed_target"],
            "progress":         s["progress"],
            "print_duration":   s["print_duration"],
            "remain_time":      s["remain_time"],
            "curr_layer":       s["curr_layer"],
            "total_layers":     s["total_layers"],
            "z_mm":             self._estimate_current_z(),
            "filename":         s["filename"],
            "slicer_time":      slicer_time,
            "camera_url":       s["camera_url"],
            "fan_speed":        s["fan_speed"],
            "print_speed_mode": s["print_speed_mode"],
            "web_upload_warning": getattr(self._args, "web_upload_warning", 1),
            "light_on":         s["light_on"],
            "light_brightness": s["light_brightness"],
            "ams_slots":        self._ams_slots,
            "ams_loaded_slot":  self._ams_loaded_slot,
            "filament_mode":    s.get("filament_mode", self._filament_mode),
            "ace_drying":       s.get("ace_drying", {"status": 0, "target_temp": 0, "duration": 0, "remain_time": 0, "humidity": None, "current_temp": None}),
            "ace_units":        list(self._ace_box_ids),
            "ace_auto_feed":    dict(self._ace_auto_feed),
            "ace_dry_presets":  self._ace_dry_presets,
            "thumbnail":        thumbnail,
            "connection_error": s["connection_error"],
            "file_ready":       s["file_ready"],
            "version":          self._read_version(),
        })

    async def handle_moonraker_database(self, request):
        """OrcaSlicer Filament-Sync: /server/database/item?namespace=lane_data&key=lanes (AFC-Format)"""
        namespace = request.rel_url.query.get("namespace", "")
        key       = request.rel_url.query.get("key", "")

        if namespace == "lane_data":
            await asyncio.get_event_loop().run_in_executor(None, self._get_ams_slots_fresh)
            lanes = self._build_lane_data()
            log.info(f"AMS-Sync: {len(lanes)} Lanes an OrcaSlicer")
            return web.json_response({
                "result": {
                    "namespace": "lane_data",
                    "key":       key or "lanes",
                    "value":     lanes,
                }
            })

        if namespace in ("AFC", "afc-install", "happy_hare"):
            return web.json_response({
                "result": {"namespace": namespace, "key": key, "value": None}
            })

        # mainsail/presets: Obico fragt nach Temperatur-Presets. Schema wird in
        # find_all_thermal_presets als data['value']['presets'].values() ausgewertet,
        # also brauchen wir mindestens {presets: {}} damit kein Crash.
        if namespace == "mainsail":
            if key == "presets":
                return web.json_response({
                    "result": {"namespace": "mainsail", "key": "presets",
                               "value": {"presets": {}}}
                })
            return web.json_response({
                "result": {"namespace": "mainsail", "key": key, "value": {}}
            })

        # obico-namespace: in-memory KV-Store für Plugin-Settings (key=printer_id etc.)
        if namespace == "obico":
            store = self._moonraker_kv_store.setdefault("obico", {})
            if key and key in store:
                return web.json_response({
                    "result": {"namespace": "obico", "key": key, "value": store[key]}
                })
            return web.json_response({
                "result": {"namespace": "obico", "key": key, "value": store if not key else None}
            })

        return web.json_response(
            {"error": {"code": 404, "message": f"Namespace '{namespace}' not found"}},
            status=404
        )

    async def handle_moonraker_database_post(self, request):
        """POST /server/database/item — KV-Store-Write (von moonraker-obico verwendet).
        moonraker-obico sendet namespace/key/value als form-urlencoded POST-params."""
        # Versuche JSON, fallback auf form-data, fallback auf Query-Params
        namespace = ""
        key       = ""
        value     = None
        try:
            data = await request.json()
            if isinstance(data, dict):
                namespace = data.get("namespace", "")
                key       = data.get("key", "")
                value     = data.get("value")
        except Exception:
            try:
                form = await request.post()
                namespace = form.get("namespace", "") or ""
                key       = form.get("key", "") or ""
                value     = form.get("value")
            except Exception:
                pass
        if not namespace:
            namespace = request.rel_url.query.get("namespace", "")
        if not key:
            key = request.rel_url.query.get("key", "")
        if namespace and key:
            store = self._moonraker_kv_store.setdefault(namespace, {})
            store[key] = value
            return web.json_response({
                "result": {"namespace": namespace, "key": key, "value": value}
            })
        return web.json_response({"error": {"code": 400, "message": "namespace + key required"}}, status=400)

    async def handle_database_list(self, request):
        """OrcaSlicer prüft welche Namespaces vorhanden sind um MMU-Typ zu erkennen."""
        return web.json_response({"result": {"namespaces": ["lane_data", "mainsail", "obico"]}})

    def _get_ams_slots_fresh(self):
        """Frische Slot-Daten per getInfo holen, Fallback auf gecachte."""
        resp = self.client.publish("multiColorBox", "getInfo", None, timeout=5)
        if resp and resp.get("data"):
            data = resp["data"]
            self._head_tools_model = int(data.get("head_tools_model", self._head_tools_model))
            boxes = data.get("multi_color_box") or []
            if boxes:
                self._update_ace_drying_state(data, boxes)
                self._filament_mode = self._detect_filament_mode(boxes, self._head_tools_model)
                self._state["filament_mode"] = self._filament_mode
                global_slots, global_loaded = self._aggregate_slots(boxes, self._filament_mode)
                activity_map = self._slot_activity_map(boxes, global_loaded)
                for s in global_slots:
                    s["activity"] = activity_map.get(s.get("global_index"), "")
                if global_slots:
                    self._ams_slots = global_slots
                self._ams_loaded_slot = global_loaded
        return self._ams_slots

    # ─── Settings ────────────────────────────────────────────────────────────

    def _find_config_path(self) -> pathlib.Path:
        """Gibt den Pfad zur config.ini zurück."""
        if hasattr(env_loader, "find_config_path"):
            return env_loader.find_config_path()
        # Fallback für alten env_loader
        script_dir = pathlib.Path(_BASE)
        for base in (script_dir, script_dir.parent):
            p = base / "config" / "config.ini"
            if p.is_file():
                return p
        return script_dir / "config" / "config.ini"

    async def handle_api_settings_get(self, request):
        return web.json_response({
            "printer_name":     self._state.get("printer_name", ""),
            "printer_ip":       self._args.printer_ip,
            "mqtt_port":        self._args.mqtt_port,
            "username":         self._args.username,
            "password":         self._args.password,
            "mode_id":          self._args.mode_id,
            "device_id":        self._args.device_id,
            "default_ams_slot": getattr(self._args, "default_ams_slot", "auto"),
            "auto_leveling":    getattr(self._args, "auto_leveling", 1),
            "camera_on_print":  getattr(self._args, "camera_on_print", 0),
            "web_upload_warning": getattr(self._args, "web_upload_warning", 1),
            "ace_dry_presets":  self._ace_dry_presets,
        })

    async def handle_api_settings_post(self, request):
        import configparser
        data = await request.json()
        config_path = self._find_config_path()
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Bestehende config.ini lesen (Kommentare gehen verloren, aber Werte bleiben)
        cfg = configparser.ConfigParser()
        if config_path.is_file():
            cfg.read(config_path, encoding="utf-8")

        # Sections sicherstellen
        for section in ("connection", "print", "bridge", "ace_dry_presets"):
            if not cfg.has_section(section):
                cfg.add_section(section)

        printer_ip = str(data.get("printer_ip", self._args.printer_ip or "")).split(":")[0]
        cfg.set("connection", "printer_ip", printer_ip)
        cfg.set("connection", "mqtt_port",  str(data.get("mqtt_port",  self._args.mqtt_port or 9883)))
        cfg.set("connection", "username",   str(data.get("username",   self._args.username  or "")))
        cfg.set("connection", "password",   str(data.get("password",   self._args.password  or "")))
        cfg.set("connection", "mode_id",    str(data.get("mode_id",    self._args.mode_id   or "")))
        cfg.set("connection", "device_id",  str(data.get("device_id",  self._args.device_id or "")))
        cfg.set("print",      "default_ams_slot", str(data.get("default_ams_slot", getattr(self._args, "default_ams_slot", "auto"))))
        cfg.set("print",      "auto_leveling",    str(data.get("auto_leveling",    getattr(self._args, "auto_leveling",    1))))
        cfg.set("print",      "camera_on_print",  str(int(bool(data.get("camera_on_print", getattr(self._args, "camera_on_print", 0))))))
        cfg.set("print",      "web_upload_warning", str(int(bool(data.get("web_upload_warning", getattr(self._args, "web_upload_warning", 1))))))
        if not cfg.has_option("bridge", "poll_interval"):
            cfg.set("bridge", "poll_interval", "3")
        printer_name = str(data.get("printer_name", "")).strip()
        if printer_name:
            cfg.set("bridge", "printer_name", printer_name)
        elif cfg.has_option("bridge", "printer_name"):
            cfg.remove_option("bridge", "printer_name")

        incoming_presets = data.get("ace_dry_presets") if isinstance(data, dict) else None
        presets = self._sanitize_ace_dry_presets(incoming_presets if isinstance(incoming_presets, dict) else self._ace_dry_presets)
        for key, val in presets.items():
          cfg.set("ace_dry_presets", f"{key}_temp", str(val["temp"]))
          cfg.set("ace_dry_presets", f"{key}_duration_sec", str(val["duration_sec"]))
          if key.startswith("custom_"):
            cfg.set("ace_dry_presets", f"{key}_name", str(val.get("name", key.replace("_", " ").title())))
        self._ace_dry_presets = presets

        with open(config_path, "w", encoding="utf-8") as f:
            f.write("# KX-Bridge Konfigurationsdatei\n\n")
            cfg.write(f)
        log.info(f"Settings gespeichert in {config_path}")
        # Response senden, dann Neustart
        response = web.json_response({"status": "restarting"})
        asyncio.get_event_loop().call_later(0.3, self._restart_bridge)
        return response

    async def handle_kx_printer_add(self, request):
        """Fügt einen Drucker hinzu: holt Credentials via IP, schreibt [printer_N], Neustart."""
        try:
            body = await request.json()
        except Exception:
            return self._json_cors({"error": "invalid json"}, status=400)
        ip   = str(body.get("printer_ip", "")).strip().split(":")[0]
        name = str(body.get("name", "")).strip()
        if not ip:
            return self._json_cors({"error": "printer_ip required"}, status=400)
        try:
            creds = await _kx_fetch_credentials(ip)
        except Exception as e:
            return self._json_cors({"error": f"Drucker nicht erreichbar oder Fehler: {e}"}, status=502)

        import configparser
        config_path = self._find_config_path()
        cfg = configparser.ConfigParser()
        if config_path.is_file():
            cfg.read(config_path, encoding="utf-8")

        # Vorhandene [printer_N]-Sektionen + belegte http_ports ermitteln
        n = 1
        existing_ports: set[int] = set()
        while cfg.has_section(f"printer_{n}"):
            p = cfg[f"printer_{n}"]
            if p.get("http_port"):
                try:
                    existing_ports.add(int(p["http_port"]))
                except ValueError:
                    pass
            n += 1

        # Kein [printer_N], aber ein befüllter [connection]? → als printer_1 migrieren
        # (leerer [connection] = kein bestehender Drucker → nicht migrieren, neuer wird printer_1)
        if n == 1 and cfg.has_section("connection") and (cfg["connection"].get("printer_ip") or "").strip():
            c = cfg["connection"]
            cfg.add_section("printer_1")
            cfg.set("printer_1", "name", self._state.get("printer_name") or "Kobra X")
            for k in ("printer_ip", "mqtt_port", "username", "password", "mode_id", "device_id"):
                if c.get(k):
                    cfg.set("printer_1", k, c.get(k))
            cfg.set("printer_1", "http_port", "7125")
            existing_ports.add(7125)
            n = 2

        # Neuen Drucker als [printer_n] anlegen, freien Port wählen
        new_port = 7125 + (n - 1)
        while new_port in existing_ports:
            new_port += 1
        sec = f"printer_{n}"
        cfg.add_section(sec)
        cfg.set(sec, "name",       name or creds["model"])
        cfg.set(sec, "printer_ip", creds["printer_ip"])
        cfg.set(sec, "mqtt_port",  "9883")
        cfg.set(sec, "username",   creds["username"])
        cfg.set(sec, "password",   creds["password"])
        cfg.set(sec, "mode_id",    creds["mode_id"])
        cfg.set(sec, "device_id",  creds["device_id"])
        cfg.set(sec, "http_port",  str(new_port))

        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as f:
            f.write("# KX-Bridge Konfigurationsdatei\n\n")
            cfg.write(f)
        log.info(f"Printer '{name or creds['model']}' added as {sec} (port {new_port})")
        response = self._json_cors({"status": "restarting", "section": sec, "http_port": new_port})
        asyncio.get_event_loop().call_later(0.5, self._restart_bridge)
        return response

    async def handle_kx_printer_remove(self, request):
        """Entfernt einen Drucker aus config.ini, dann Neustart.

        - Multi-Modus: [printer_N] wird gelöscht, übrige umnummeriert (printer_3 → printer_2),
          printer_1 bekommt immer http_port 7125.
        - Einzel-Modus (kein [printer_N], nur [connection]): pid "1" leert den [connection]-Block
          → Bridge startet im Offline-Modus auf 7125, UI bleibt erreichbar.
        - Wird der letzte [printer_N] entfernt: alle weg → ebenfalls "leerer" Zustand.
        """
        pid = str(request.match_info.get("pid", "")).strip()
        if not pid:
            return self._json_cors({"error": "printer id required"}, status=400)

        import configparser
        config_path = self._find_config_path()
        cfg = configparser.ConfigParser()
        if config_path.is_file():
            cfg.read(config_path, encoding="utf-8")

        has_printer_sections = cfg.has_section("printer_1")
        target = f"printer_{pid}"

        if has_printer_sections:
            if not cfg.has_section(target):
                return self._json_cors({"error": f"{target} nicht gefunden"}, status=404)
            # Alle [printer_N] einsammeln (außer der zu löschenden), neu nummerieren
            kept = []
            n = 1
            while cfg.has_section(f"printer_{n}"):
                if str(n) != pid:
                    kept.append(dict(cfg[f"printer_{n}"]))
                cfg.remove_section(f"printer_{n}")
                n += 1
            for i, sec_data in enumerate(kept, start=1):
                sec = f"printer_{i}"
                cfg.add_section(sec)
                for k, v in sec_data.items():
                    cfg.set(sec, k, v)
                cfg.set(sec, "http_port", str(7125 + i - 1))
            remaining = len(kept)
            # War das der letzte Drucker? Dann auch [connection] leeren → wirklich "kein Drucker"
            if remaining == 0 and cfg.has_section("connection"):
                for k in ("printer_ip", "username", "password", "device_id"):
                    cfg.set("connection", k, "")
        else:
            # Einzel-Modus: nur pid "1" ist gültig (Pseudo-Eintrag aus handle_kx_printers)
            if pid != "1":
                return self._json_cors({"error": "kein Drucker mit dieser ID"}, status=404)
            # [connection]-Werte leeren → Bridge startet ohne Drucker
            if cfg.has_section("connection"):
                for k in ("printer_ip", "username", "password", "device_id"):
                    cfg.set("connection", k, "")
            remaining = 0

        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as f:
            f.write("# KX-Bridge Konfigurationsdatei\n\n")
            cfg.write(f)
        log.info(f"Drucker {target} entfernt ({remaining} verbleibend)")
        response = self._json_cors({"status": "restarting", "removed": target, "remaining": remaining})
        asyncio.get_event_loop().call_later(0.5, self._restart_bridge)
        return response

    def _restart_bridge(self):
        log.info("Bridge wird neu gestartet …")
        # config_loader cached config.ini-Werte in os.environ ("nur wenn nicht gesetzt").
        # Bei einem Restart muss environ bereinigt werden, sonst liest der neue Prozess
        # die alten Werte statt der geänderten config.ini.
        for _k in ("PRINTER_IP", "MQTT_PORT", "MQTT_USERNAME", "MQTT_PASSWORD",
                   "MODE_ID", "DEVICE_ID", "DEFAULT_AMS_SLOT", "AUTO_LEVELING",
                   "CAMERA_ON_PRINT", "WEB_UPLOAD_WARNING", "BRIDGE_PRINTER_NAME"):
            os.environ.pop(_k, None)

        in_docker = os.path.exists("/.dockerenv") or os.environ.get("KX_IN_DOCKER")
        if in_docker:
            # Docker/systemd: Prozess beenden reicht – der Supervisor startet neu (frische environ)
            log.info("Container environment detected – exiting for supervisor restart")
            os._exit(0)

        frozen = getattr(sys, "frozen", False)

        # Linux: os.execv ersetzt das Prozess-Image direkt – sauber auch bei PyInstaller-Onefile
        # (subprocess+exit würde dort am gelöschten _MEIxxxx-Temp-Verzeichnis scheitern).
        if sys.platform != "win32":
            exe = sys.executable
            try:
                if frozen:
                    os.execv(exe, [exe] + sys.argv[1:])
                else:
                    os.execv(exe, [exe] + sys.argv)
            except Exception as e:
                log.error(f"Restart (execv) fehlgeschlagen: {e} – bitte Bridge manuell neu starten")
                os._exit(1)

        # Windows: os.execv ist dort kaputt (neue PID, alter Prozess kehrt zurück) → subprocess
        cmd = ([sys.executable] + sys.argv[1:]) if frozen else ([sys.executable] + sys.argv)
        try:
            subprocess.Popen(cmd, cwd=os.getcwd(),
                             creationflags=(subprocess.DETACHED_PROCESS
                                            | subprocess.CREATE_NEW_PROCESS_GROUP))
        except Exception as e:
            log.error(f"Restart fehlgeschlagen: {e} – bitte Bridge manuell neu starten")
        os._exit(0)

    # ─── Update ──────────────────────────────────────────────────────────────

    STABLE_RELEASE_API = "https://gitea.it-drui.de/api/v1/repos/viewit/KX-Bridge-Release/releases?limit=1"
    DEV_RELEASE_API    = "https://gitea.it-drui.de/api/v1/repos/viewit/KX-Bridge-Release/releases?limit=10&pre-release=true"
    GITEA_RAW_BASE     = "https://gitea.it-drui.de/viewit/KX-Bridge-Release/raw/tag"

    def _read_version(self) -> str:
        # PyInstaller-Onefile entpackt VERSION (per kx-bridge.spec datas) nach
        # sys._MEIPASS — daher _WEB_BASE statt _BASE benutzen.
        for base in (pathlib.Path(_WEB_BASE), pathlib.Path(_BASE), pathlib.Path(_BASE).parent):
            p = base / "VERSION"
            if p.is_file():
                return p.read_text(encoding="utf-8").strip()
        return "unknown"

    def _write_version(self, version: str):
        for base in (pathlib.Path(_BASE), pathlib.Path(_BASE).parent):
            p = base / "VERSION"
            if p.is_file():
                p.write_text(version + "\n", encoding="utf-8")
                return
        (pathlib.Path(_BASE) / "VERSION").write_text(version + "\n", encoding="utf-8")

    @staticmethod
    def _parse_version(v: str) -> "tuple[int, ...]":
        """'v0.9.1-beta1' → (0, 9, 1)  –  nur numerische Teile vor dem ersten '-'"""
        v = v.lstrip("v").split("-")[0]
        parts = re.split(r"[.\s]+", v)
        result = []
        for p in parts:
            try:
                result.append(int(p))
            except ValueError:
                break
        return tuple(result) or (0,)

    async def handle_api_log_stream(self, request):
        """SSE-Endpoint: sendet Log-Einträge live an den Browser."""
        resp = web.StreamResponse(headers={
            "Content-Type":  "text/event-stream",
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        })
        await resp.prepare(request)
        # Zuerst Ring-Buffer senden
        for entry in list(_log_buffer):
            data = json.dumps(entry, ensure_ascii=False)
            await resp.write(f"data: {data}\n\n".encode())
        # Dann live streamen
        q: asyncio.Queue = asyncio.Queue()
        _log_sse_queues.append(q)
        try:
            while True:
                entry = await asyncio.wait_for(q.get(), timeout=25)
                data = json.dumps(entry, ensure_ascii=False)
                await resp.write(f"data: {data}\n\n".encode())
        except asyncio.TimeoutError:
            await resp.write(b": keepalive\n\n")
        except (ConnectionResetError, Exception):
            pass
        finally:
            _log_sse_queues.remove(q) if q in _log_sse_queues else None
        return resp

    async def handle_api_log_download(self, request):
        """Gibt alle gepufferten Log-Einträge als Plaintext zum Download."""
        header = (f"# KX-Bridge Log  |  Version {self._read_version()}  |  "
                  f"{time.strftime('%Y-%m-%d %H:%M:%S')}  |  {len(_log_buffer)} Einträge\n")
        lines = [f"[{e['ts']}] {e['lvl']:<7} {e['name']}: {e['msg']}" for e in _log_buffer]
        text = header + "\n".join(lines) + "\n"
        fname = f"kx-bridge-log_{time.strftime('%Y%m%d-%H%M%S')}.txt"
        return web.Response(
            body=text.encode("utf-8"),
            content_type="text/plain",
            headers={"Content-Disposition": f'attachment; filename="{fname}"'},
        )

    async def handle_api_update_check(self, request):
        current = self._read_version()
        is_dev = "-dev+" in current
        api_url = self.DEV_RELEASE_API if is_dev else self.STABLE_RELEASE_API
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        return web.json_response({"error": f"Gitea HTTP {resp.status}"}, status=502)
                    releases = await resp.json(content_type=None)
            if not releases:
                return web.json_response({"error": "Keine Releases gefunden"}, status=404)
            # Dev: neuestes Release mit "-dev+" im Tag suchen
            if is_dev:
                dev_releases = [r for r in releases if "-dev+" in r.get("tag_name", "")]
                if not dev_releases:
                    return web.json_response({"error": "Keine Dev-Releases gefunden"}, status=404)
                data = dev_releases[0]
            else:
                data = releases[0]
            tag = data.get("tag_name", "")
            latest = tag.lstrip("v")
            if is_dev:
                update_available = tag != f"v{current}"
            else:
                update_available = self._parse_version(tag) > self._parse_version(current)
            download_url = f"{self.GITEA_RAW_BASE}/{tag}/kobrax_moonraker_bridge.py"
            return web.json_response({
                "current":          current,
                "latest":           latest,
                "update_available": update_available,
                "tag":              tag,
                "download_url":     download_url,
                "changelog":        data.get("body", ""),
            })
        except Exception as e:
            return web.json_response({"error": str(e)}, status=502)

    # Bridge-Python-Module, die das Self-Update mitziehen muss. Wird nur die
    # Hauptdatei ersetzt, crasht die neue Version ggf. mit ModuleNotFoundError.
    # Hinweis: das Frontend liegt seit dem Theme-System unter web/themes/<name>/
    # (keine flache .py mehr); Theme-Dateien werden vom Self-Update derzeit NICHT
    # mitgeladen – Theme-Änderungen kommen über Docker-Image/Binary-Update.
    _UPDATE_FILES = [
        "kobrax_moonraker_bridge.py",
        "kobrax_client.py",
        "config_loader.py",
        "env_loader.py",
    ]

    async def handle_api_update_apply(self, request):
        data = await request.json()
        new_tag = data.get("tag", "")
        if getattr(sys, "frozen", False):
            return web.json_response(
                {"error": "Self-Update wird im Binary-Modus nicht unterstützt – "
                          "bitte neue Binary/Docker-Image laden."}, status=400)
        if not new_tag:
            return web.json_response({"error": "tag fehlt"}, status=400)

        app_dir = pathlib.Path(__file__).resolve().parent
        try:
            # Phase 1: ALLE Dateien herunterladen (in .new), nichts ersetzen.
            downloaded: list[tuple[pathlib.Path, bytes]] = []
            async with aiohttp.ClientSession() as session:
                for fname in self._UPDATE_FILES:
                    url = f"{self.GITEA_RAW_BASE}/{new_tag}/{fname}"
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                        if resp.status != 200:
                            # _web_assets.py o.ä. existiert evtl. in älteren Tags nicht –
                            # Hauptdatei ist Pflicht, optionale dürfen fehlen.
                            if fname == "kobrax_moonraker_bridge.py":
                                return web.json_response(
                                    {"error": f"Download {fname}: HTTP {resp.status}"}, status=502)
                            log.warning(f"Update: {fname} not found in release ({resp.status}) – skipped")
                            continue
                        downloaded.append((app_dir / fname, await resp.read()))
            # Phase 2: atomar ersetzen (erst nach komplettem, erfolgreichem Download)
            for path, content in downloaded:
                tmp = path.with_suffix(path.suffix + ".new")
                tmp.write_bytes(content)
                os.replace(tmp, path)
            self._write_version(new_tag.lstrip("v"))
            log.info(f"Update auf {new_tag} installiert ({len(downloaded)} Dateien), starte neu …")
        except Exception as e:
            return web.json_response({"error": str(e)}, status=502)
        response = web.json_response({"status": "updating"})
        asyncio.get_event_loop().call_later(0.3, self._restart_bridge)
        return response

    async def handle_catchall(self, request):
        body = await request.read()
        log.warning(f"UNBEKANNT {request.method} {request.path_qs}  body={body[:200]}")
        return web.json_response({"result": {}}, status=200)

    async def handle_favicon(self, request):
        # Minimales 1x1 ICO damit der Browser nicht 404 loggt
        ico = bytes([
            0,0,1,0,1,0,1,1,0,0,1,0,24,0,40,0,0,0,22,0,0,0,40,0,0,0,
            1,0,0,0,2,0,0,0,1,0,24,0,0,0,0,0,4,0,0,0,0,0,0,0,0,0,0,0,
            0,0,0,0,0,0,0,0,255,102,0,0,0,0,0,0
        ])
        return web.Response(body=ico, content_type="image/x-icon")

    # -------------------------------------------------------------------------
    # Klipper G-Code-Script Emulation für moonraker-obico
    # -------------------------------------------------------------------------

    async def _exec_gcode_script(self, script: str) -> str:
        """Mappt eine Klipper- oder Marlin-G-Code-Zeile auf einen MQTT-Befehl
        an den Kobra X. Unterstützt:
        - PAUSE / M25, RESUME / M24, CANCEL_PRINT / M0/M1/M524/ABORT
        - M104 S<temp>                         → Nozzle-Temperatur
        - M140 S<temp>                         → Bett-Temperatur
        - SET_HEATER_TEMPERATURE HEATER=extruder TARGET=200   (Klipper)
        - SET_HEATER_TEMPERATURE HEATER=heater_bed TARGET=60  (Klipper)
        Unbekannte Scripts werden mit 'ok' quittiert (Obico schickt z.B. G28
        zum Home, das ignoriert die Bridge stillschweigend)."""
        if not script:
            return "ok"
        s = script.strip().upper()
        loop = asyncio.get_event_loop()

        def _parse_marlin_temp(line: str) -> int | None:
            """Aus 'M104 S200' oder 'M140 S60' den Temperatur-Wert ziehen."""
            try:
                return int(line.split("S", 1)[1].split()[0])
            except Exception:
                return None

        def _parse_klipper_set_heater(line: str) -> tuple[str | None, int | None]:
            """Aus 'SET_HEATER_TEMPERATURE HEATER=extruder TARGET=143' die
            Heater-ID + Target rausziehen. Heater ist 'extruder' oder
            'heater_bed', Target ist int. Liefert (None,None) bei Fehler."""
            heater = None
            target = None
            for part in line.split():
                if part.startswith("HEATER="):
                    heater = part.split("=", 1)[1].strip().lower()
                elif part.startswith("TARGET="):
                    try:
                        target = int(float(part.split("=", 1)[1]))
                    except Exception:
                        pass
            return heater, target

        async def _set_temps(nozzle: int | None, bed: int | None):
            """Setzt Nozzle/Bed-Temperatur über den richtigen MQTT-Pfad —
            druckend: print/update mit taskid, idle: tempature/set mit beiden."""
            is_printing = self._state.get("print_state") in ("printing", "paused")
            if is_printing:
                taskid = self._state.get("taskid", "")
                if nozzle is not None:
                    await loop.run_in_executor(None, lambda: self.client.publish_web(
                        "print", "update",
                        {"taskid": taskid, "settings": {"target_nozzle_temp": int(nozzle)}},
                    ))
                if bed is not None:
                    await loop.run_in_executor(None, lambda: self.client.publish_web(
                        "print", "update",
                        {"taskid": taskid, "settings": {"target_hotbed_temp": int(bed)}},
                    ))
            else:
                # Idle: tempature/set via web/printer-Topic mit type-Feld
                # (Live-Sniff 2026-05-29). type: 0=Nozzle, 1=Bed, 2=beide.
                if nozzle is not None and bed is not None:
                    t, n, b = 2, int(nozzle), int(bed)
                elif nozzle is not None:
                    t, n, b = 0, int(nozzle), 0
                elif bed is not None:
                    t, n, b = 1, 0, int(bed)
                else:
                    return
                await loop.run_in_executor(None, lambda: self.client.publish_web(
                    "tempature", "set",
                    {"type": t, "target_nozzle_temp": n, "target_hotbed_temp": b},
                ))

        try:
            if s in ("PAUSE", "M25"):
                await loop.run_in_executor(None, self.client.pause_print)
            elif s in ("RESUME", "M24"):
                await loop.run_in_executor(None, self.client.resume_print)
            elif s in ("CANCEL_PRINT", "M0", "M1", "M524", "ABORT"):
                await loop.run_in_executor(None, self.client.stop_print)
            elif s.startswith("M104 "):
                t = _parse_marlin_temp(s)
                if t is not None:
                    log.info(f"gcode.script: Nozzle-Target {t}°C (M104)")
                    await _set_temps(t, None)
            elif s.startswith("M140 "):
                t = _parse_marlin_temp(s)
                if t is not None:
                    log.info(f"gcode.script: Bed-Target {t}°C (M140)")
                    await _set_temps(None, t)
            elif s.startswith("SET_HEATER_TEMPERATURE"):
                heater, target = _parse_klipper_set_heater(s)
                if target is not None and heater:
                    if heater == "extruder":
                        log.info(f"gcode.script: Nozzle-Target {target}°C (Klipper)")
                        await _set_temps(target, None)
                    elif heater in ("heater_bed", "bed"):
                        log.info(f"gcode.script: Bed-Target {target}°C (Klipper)")
                        await _set_temps(None, target)
                    else:
                        log.debug(f"gcode.script: unbekannter Heater '{heater}' ignoriert")
            else:
                # Unbekanntes Script: stillschweigend OK quittieren.
                log.debug(f"gcode.script ignored: {s[:60]}")
        except Exception as e:
            log.warning(f"gcode.script {s[:30]}: {e}")
        return "ok"

    async def handle_printer_gcode_script(self, request):
        """HTTP POST /printer/gcode/script — Klipper-G-Code-Wrapper (siehe _exec_gcode_script)."""
        script = ""
        if request.method == "POST":
            try:
                body = await request.json()
                if isinstance(body, dict):
                    script = body.get("script", "") or ""
            except Exception:
                pass
        if not script:
            script = request.rel_url.query.get("script", "")
        result = await self._exec_gcode_script(script)
        return web.json_response({"result": result})

    # -------------------------------------------------------------------------
    # WebSocket handler
    # -------------------------------------------------------------------------

    async def handle_websocket(self, request):
        ws = web.WebSocketResponse(heartbeat=30)
        await ws.prepare(request)
        ws._loop = asyncio.get_event_loop()
        self.ws_clients.add(ws)
        log.info(f"WS client verbunden ({len(self.ws_clients)} gesamt)")

        # Send klippy_ready notification
        await ws.send_str(json.dumps({
            "jsonrpc": "2.0",
            "method":  "notify_klippy_ready",
            "params":  [],
        }))
        # Send initial status
        await ws.send_str(json.dumps({
            "jsonrpc": "2.0",
            "method":  "notify_status_update",
            "params":  [self._build_printer_objects(), time.time()],
        }))

        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                await self._handle_ws_rpc(ws, msg.data)
            elif msg.type in (aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSE):
                break

        self.ws_clients.discard(ws)
        log.info(f"WS client getrennt ({len(self.ws_clients)} verbleibend)")
        return ws

    async def _handle_ws_rpc(self, ws: web.WebSocketResponse, raw: str):
        try:
            req = json.loads(raw)
        except Exception:
            return
        rpc_id = req.get("id")
        method  = req.get("method", "")
        log.info(f"WS RPC: {method}  params={str(req.get('params',''))[:120]}")
        params  = req.get("params") or {}
        if isinstance(params, list):
            params = params[0] if params else {}

        result = None
        error  = None

        try:
            if method in ("printer.info", "printer_info"):
                result = {
                    "state":           "ready",
                    "state_message":   "Printer is ready",
                    "hostname":        "kobrax-bridge",
                    "software_version": KLIPPER_VERSION,
                    "cpu_info":        self._state["printer_name"],
                    "klipper_path":    "/home/pi/klipper",
                    "python_path":     "/home/pi/klippy-env/bin/python",
                }
            elif method in ("server.info", "server_info"):
                result = {
                    "klippy_connected": True,
                    "klippy_state":     "ready",
                    "moonraker_version": MOONRAKER_VERSION,
                    "components":       [],
                    "failed_components": [],
                    "registered_directories": ["gcodes"],
                    "warnings":         [],
                }
            elif method in ("printer.objects.list",):
                result = {"objects": list(self._build_printer_objects().keys())}
            elif method in ("printer.objects.query", "printer.objects.get"):
                objects = params.get("objects", {})
                all_objs = self._build_printer_objects()
                if objects:
                    filtered = {k: all_objs.get(k, {}) for k in objects}
                else:
                    filtered = all_objs
                result = {"status": filtered, "eventtime": time.time()}
            elif method == "printer.objects.subscribe":
                objects = params.get("objects", {})
                all_objs = self._build_printer_objects()
                if objects:
                    filtered = {k: all_objs.get(k, {}) for k in objects}
                else:
                    filtered = all_objs
                result = {"status": filtered, "eventtime": time.time()}
            elif method == "printer.print.start":
                filename = params.get("filename", self._last_uploaded_file)
                loop = asyncio.get_event_loop()
                resp = await loop.run_in_executor(
                    None, lambda: self.client.publish("print", "start",
                        {"filename": filename, "use_ams": False}, timeout=15.0)
                )
                result = "ok" if resp else "timeout"
            elif method == "printer.print.pause":
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.client.pause_print)
                result = "ok"
            elif method == "printer.print.resume":
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.client.resume_print)
                result = "ok"
            elif method == "printer.print.cancel":
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.client.stop_print)
                result = "ok"
            elif method == "machine.system_info":
                result = {"system_info": {"cpu_info": {"cpu_desc": "Kobra X Bridge"}}}
            elif method == "server.files.list":
                result = []
            # ── moonraker-obico passthru-Targets ──
            elif method == "printer.gcode.script":
                script = (params.get("script") or "").strip().upper() if isinstance(params, dict) else ""
                result = await self._exec_gcode_script(script)
            elif method in ("server.connection.identify",):
                # Obico identifiziert sich beim Connect. Connection-ID egal.
                result = {"connection_id": 1}
            elif method == "connection.register_remote_method":
                # Obico registriert obico_remote_event-Callback. Wir akzeptieren leer.
                result = "ok"
            elif method == "server.webcams.list":
                # WS-Variante: absolute URL mit echter LAN-IP statt localhost
                _lip = getattr(self, "_local_ip", None) or "127.0.0.1"
                _base = f"http://{_lip}:{self._args.port}"
                result = {"webcams": [{
                    "name": "KX-Bridge", "location": "printer", "service": "mjpegstreamer",
                    "enabled": True,
                    "stream_url":   f"{_base}/api/camera/stream",
                    "snapshot_url": f"{_base}/api/camera/snapshot",
                    "flip_horizontal": False, "flip_vertical": False, "rotation": 0,
                    "target_fps": 5, "aspect_ratio": "16:9",
                }]}
            elif method == "server.history.list":
                # Reuse HTTP-Handler-Logik (Moonraker-Schema mit Unix-TS).
                try:
                    jobs = self._store.list_jobs(limit=50) or []
                except Exception:
                    jobs = []
                from datetime import datetime, timezone as _tz
                def _ts(iso):
                    try:
                        return datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=_tz.utc).timestamp()
                    except Exception:
                        return 0.0
                result = {"count": len(jobs), "jobs": [
                    {"job_id": j.get("id"), "exists": True, "filename": j.get("filename",""),
                     "status": j.get("status") or "completed",
                     "print_duration": j.get("duration_sec") or 0,
                     "total_duration": j.get("duration_sec") or 0,
                     "start_time": _ts(j.get("started_at")),
                     "end_time":   (_ts(j.get("started_at")) + (j.get("duration_sec") or 0)) if j.get("started_at") and j.get("duration_sec") else None,
                     "filament_used": 0.0, "metadata": {}}
                    for j in jobs
                ]}
            elif method == "machine.update.status":
                result = {"busy": False, "version_info": {}}
            elif method == "server.files.metadata":
                # Obico fragt nach Metadaten zu einer Datei (filename in params)
                fname = (params or {}).get("filename") if isinstance(params, dict) else None
                meta = {}
                if fname:
                    try:
                        rec = self._store.get_file_by_filename(fname) if hasattr(self._store, "get_file_by_filename") else None
                    except Exception:
                        rec = None
                    if rec:
                        meta = {
                            "filename": rec.get("filename"),
                            "size":     rec.get("size_bytes") or 0,
                            "modified": time.time(),
                            "estimated_time": rec.get("est_print_time_sec") or 0,
                            "thumbnails": [],
                        }
                result = meta
            else:
                log.debug(f"Unbekannte RPC-Methode: {method}")
                result = {}
        except Exception as e:
            log.error(f"RPC error for {method}: {e}")
            error = {"code": -32603, "message": str(e)}

        if rpc_id is not None:
            response = {"jsonrpc": "2.0", "id": rpc_id}
            if error:
                response["error"] = error
            else:
                response["result"] = result
            await ws.send_str(json.dumps(response))

    # -------------------------------------------------------------------------
    # Poll loop (sync, runs in executor)
    # -------------------------------------------------------------------------

    def _printer_reachable(self) -> bool:
        """TCP-Probe auf den MQTT-Port – kein ICMP nötig, kein root erforderlich."""
        import socket as _socket
        try:
            with _socket.create_connection(
                (self._args.printer_ip, self._args.mqtt_port), timeout=2.0
            ):
                return True
        except OSError:
            return False

    def _poll_loop(self, stop_event: threading.Event):
        _offline = self._state["kobra_state"] == "offline"
        _probe_interval = 10.0   # Sekunden zwischen TCP-Probes im Offline-Modus

        while not stop_event.is_set():
            # ── Offline-Modus: warten bis Drucker wieder erreichbar ──────────
            if _offline:
                if self._printer_reachable():
                    log.info("Drucker erreichbar – stelle MQTT-Verbindung her …")
                    try:
                        self.client.connect()
                        _offline = False
                        self._state["print_state"] = "standby"
                        self._state["kobra_state"] = "free"
                        self._state["connection_error"] = ""
                        log.info("MQTT-Verbindung wiederhergestellt")
                    except Exception as e:
                        err = _mqtt_error_msg(e)
                        self._state["connection_error"] = err
                        log.warning(f"Verbindungsaufbau fehlgeschlagen: {err}")
                        stop_event.wait(_probe_interval)
                        continue
                else:
                    stop_event.wait(_probe_interval)
                    continue

            # ── Online-Modus: normaler Poll ──────────────────────────────────
            try:
                info = self.client.query_info()
                if info:
                    self._on_info(info)
                # Während Druck: print/report direkt abfragen
                if self._state["print_state"] in ("printing", "preheating",
                                                   "auto_leveling", "checking", "init"):
                    print_r = self.client.publish("print", "query", timeout=3.0)
                    if print_r:
                        self._on_print(print_r)
                box = self.client.query_multicolor_box()
                if box:
                    data = box.get("data") or {}
                    self._head_tools_model = int(data.get("head_tools_model", self._head_tools_model))
                    boxes = data.get("multi_color_box") or []
                    if boxes:
                        self._update_ace_drying_state(data, boxes)
                        self._filament_mode = self._detect_filament_mode(boxes, self._head_tools_model)
                        self._state["filament_mode"] = self._filament_mode
                        global_slots, global_loaded = self._aggregate_slots(boxes, self._filament_mode)
                        activity_map = self._slot_activity_map(boxes, global_loaded)
                        for s in global_slots:
                            s["activity"] = activity_map.get(s.get("global_index"), "")
                        if global_slots:
                            self._ams_slots = global_slots
                        self._ams_loaded_slot = global_loaded
            except Exception as e:
                log.warning(f"Poll-Fehler: {e}")
                # Prüfen ob Drucker wirklich weg ist
                if not self._printer_reachable():
                    log.info("Drucker nicht erreichbar – wechsle in Offline-Modus")
                    self._state["print_state"] = "error"
                    self._state["kobra_state"] = "offline"
                    self._state["connection_error"] = f"Printer unreachable ({self._args.printer_ip})"
                    try:
                        self.client.disconnect()
                    except Exception:
                        pass
                    _offline = True
            stop_event.wait(3.0)


# ---------------------------------------------------------------------------
# App factory + main
# ---------------------------------------------------------------------------

def _mqtt_error_msg(exc: Exception) -> str:
    msg = str(exc)
    if "20020005" in msg:
        return "Wrong MQTT credentials (username, password or device ID incorrect)"
    return msg


@web.middleware
async def cors_middleware(request, handler):
    if request.method == "OPTIONS":
        return web.Response(status=204, headers={
            "Access-Control-Allow-Origin":  "*",
            "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        })
    resp = await handler(request)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp


def build_app(bridge: KobraXBridge) -> web.Application:
    app = web.Application(
        client_max_size=256 * 1024 * 1024,
        middlewares=[cors_middleware],
    )
    r = app.router

    # Moonraker API
    r.add_get("/server/info",                bridge.handle_server_info)
    r.add_get("/printer/info",               bridge.handle_printer_info)
    r.add_get("/machine/system_info",        bridge.handle_machine_system_info)
    r.add_get("/printer/objects/list",       bridge.handle_objects_list)
    r.add_get("/printer/objects/query",      bridge.handle_objects_query)
    r.add_get("/printer/objects/subscribe",  bridge.handle_objects_subscribe)
    r.add_post("/printer/objects/subscribe", bridge.handle_objects_subscribe)
    r.add_get("/server/files/list",          bridge.handle_files_list)
    r.add_get("/server/files/metadata",      bridge.handle_files_metadata)
    r.add_post("/server/files/upload",       bridge.handle_file_upload)
    r.add_post("/printer/print/start",       bridge.handle_print_start)
    r.add_post("/printer/print/pause",       bridge.handle_print_pause)
    r.add_post("/printer/print/resume",      bridge.handle_print_resume)
    r.add_post("/printer/print/cancel",      bridge.handle_print_cancel)

    # Moonraker-Stubs für moonraker-obico
    r.add_get("/access/api_key",             bridge.handle_access_api_key)
    r.add_get("/machine/update/status",      bridge.handle_machine_update_status)
    r.add_get("/server/history/list",        bridge.handle_history_list)
    r.add_get("/server/webcams/list",        bridge.handle_webcams_list)
    r.add_post("/printer/gcode/script",      bridge.handle_printer_gcode_script)

    # OctoPrint compatibility (OrcaSlicer probes this + uploads here)
    r.add_get("/api/version",                bridge.handle_octoprint_version)
    r.add_post("/api/files/local",           bridge.handle_file_upload)
    r.add_post("/api/files/{path:.*}",       bridge.handle_file_upload)

    # Moonraker database (OrcaSlicer AMS-Sync)
    r.add_get("/server/database/item",       bridge.handle_moonraker_database)
    r.add_post("/server/database/item",      bridge.handle_moonraker_database_post)
    r.add_get("/server/database/list",       bridge.handle_database_list)

    # New API endpoints
    r.add_post("/api/light",               bridge.handle_api_light)
    r.add_post("/api/fan",                 bridge.handle_api_fan)
    r.add_post("/api/connect",             bridge.handle_api_connect)
    r.add_post("/api/disconnect",          bridge.handle_api_disconnect)
    r.add_post("/api/restart",             bridge.handle_api_restart)
    r.add_post("/api/speed",               bridge.handle_api_speed)
    r.add_post("/api/ams/feed",            bridge.handle_api_ams_feed)
    r.add_post("/api/ams/set_slot",        bridge.handle_api_ams_set_slot)
    r.add_post("/api/ace/auto_feed",        bridge.handle_api_ace_auto_feed)
    r.add_post("/api/ace/dry",             bridge.handle_api_ace_dry)
    r.add_post("/api/axis",                bridge.handle_api_axis)
    r.add_post("/api/temperature",         bridge.handle_api_temperature)
    r.add_get("/api/camera",               bridge.handle_api_camera)
    r.add_get("/api/camera/stream",        bridge.handle_camera_stream)
    r.add_get("/api/camera/h264",          bridge.handle_camera_h264)
    r.add_get("/api/camera/snapshot",      bridge.handle_api_camera_snapshot)
    r.add_post("/api/camera/start",        bridge.handle_api_camera_start)
    r.add_post("/api/camera/stop",         bridge.handle_api_camera_stop)
    r.add_get("/api/state",                bridge.handle_api_state)
    r.add_get("/api/settings",             bridge.handle_api_settings_get)
    r.add_post("/api/settings",            bridge.handle_api_settings_post)
    r.add_get("/api/update/check",         bridge.handle_api_update_check)
    r.add_post("/api/update/apply",        bridge.handle_api_update_apply)
    r.add_post("/api/file_ready/clear",    bridge.handle_api_file_ready_clear)
    r.add_get("/api/log/stream",           bridge.handle_api_log_stream)
    r.add_get("/api/log/download",         bridge.handle_api_log_download)
    r.add_get("/serve/{filename}",         bridge.handle_serve_file)
    # /kx/ GCode Store + History + Filament
    r.add_get("/kx/printers",              bridge.handle_kx_printers)
    r.add_post("/kx/printers/add",         bridge.handle_kx_printer_add)
    r.add_delete("/kx/printers/{pid}",     bridge.handle_kx_printer_remove)
    r.add_post("/kx/print",               bridge.handle_kx_print)
    r.add_get("/kx/files",                bridge.handle_kx_files)
    r.add_delete("/kx/files/{file_id}",    bridge.handle_kx_file_delete)
    r.add_get("/kx/files/{file_id}/download", bridge.handle_kx_file_download)
    r.add_post("/kx/files/{file_id}/verify", bridge.handle_kx_file_verify)
    r.add_get("/kx/filament/slots",        bridge.handle_kx_filament_slots)
    r.add_get("/kx/filament/profiles",     bridge.handle_kx_filament_profiles)
    r.add_post("/kx/filament/slots/{idx}/profile", bridge.handle_kx_filament_slot_profile)
    # Custom-Profile-Import (Issue #41) — User lädt eigene Orca-Filament-
    # Profile als ZIP/JSON hoch (z.B. aus ~/.config/OrcaSlicer/user/<id>/filament/),
    # weil die Bridge typischerweise nicht auf demselben Host wie OrcaSlicer läuft.
    r.add_get("/kx/filament/profiles/user",    bridge.handle_kx_filament_profiles_user_list)
    r.add_post("/kx/filament/profiles/user",   bridge.handle_kx_filament_profiles_import)
    r.add_delete("/kx/filament/profiles/user", bridge.handle_kx_filament_profiles_user_delete)
    r.add_get("/kx/history",               bridge.handle_kx_history)
    r.add_get("/kx/ui/{name:.*}",          bridge.handle_kx_ui_asset)
    r.add_get("/kx/files/{id}/objects",    bridge.handle_kx_file_objects)
    r.add_post("/kx/skip",                 bridge.handle_kx_skip)
    r.add_post("/kx/skip/query",           bridge.handle_kx_skip_query)
    r.add_get("/kx/skip/state",            bridge.handle_kx_skip_state)
    r.add_route("OPTIONS", "/kx/{path:.*}", bridge.handle_kx_options)

    # Root + Printer-Routen (Single-Page, JS liest Pathname)
    r.add_get("/",                           bridge.handle_index)
    r.add_get(r"/printer{num:\d+}",          bridge.handle_index)
    r.add_get("/favicon.ico",               bridge.handle_favicon)

    # WebSocket
    r.add_get("/websocket",                  bridge.handle_websocket)

    # Catch-all: alle unbekannten Requests loggen statt 404
    r.add_route("*", "/{path:.*}",           bridge.handle_catchall)

    return app


def _build_per_printer_args(base_args, p: dict):
    """Kopiere CLI-Args, überschreibe mit Druckereintrag aus config.ini."""
    import copy
    a = copy.copy(base_args)
    a.printer_ip = p.get("printer_ip") or base_args.printer_ip
    a.mqtt_port  = int(p.get("mqtt_port") or base_args.mqtt_port)
    a.username   = p.get("username")  or base_args.username
    a.password   = p.get("password")  or base_args.password
    a.mode_id    = p.get("mode_id")   or base_args.mode_id
    a.device_id  = p.get("device_id") or base_args.device_id
    a.port       = int(p.get("http_port") or base_args.port)
    return a


async def run_bridge(args):
    printers = env_loader.list_printers()
    multi_mode = bool(printers)
    if not printers:
        printers = [{
            "id":         "1",
            "name":       getattr(args, "printer_name", None) or "Anycubic Kobra X",
            "printer_ip": args.printer_ip,
            "mqtt_port":  args.mqtt_port,
            "username":   args.username,
            "password":   args.password,
            "mode_id":    args.mode_id,
            "device_id":  args.device_id,
            "http_port":  args.port,
        }]

    store = GCodeStore(args.data_dir)
    all_bridges: dict = {}
    runners = []
    stop_event = threading.Event()
    loop = asyncio.get_event_loop()

    for idx, p in enumerate(printers):
        pid = str(p.get("id") or (idx + 1))
        per_args = _build_per_printer_args(args, p)
        # Default-Port-Konvention: 7125 + (id-1) wenn kein http_port gesetzt
        if not p.get("http_port") and multi_mode:
            try:
                per_args.port = 7125 + (int(pid) - 1)
            except ValueError:
                per_args.port = 7125 + idx

        client = KobraXClient(
            host=per_args.printer_ip,
            port=per_args.mqtt_port,
            username=per_args.username,
            password=per_args.password,
            mode_id=per_args.mode_id,
            device_id=per_args.device_id,
            client_id=f"kobrax_bridge_{pid}",
        )
        bridge = KobraXBridge(
            client, args=per_args, store=store,
            printer_id=pid, all_bridges=all_bridges,
        )
        # printer_name aus config.ini übernehmen falls gesetzt
        if p.get("name"):
            bridge._state["printer_name"] = p["name"]
            bridge._name_locked = True
        all_bridges[pid] = bridge

        log.info(f"[Drucker {pid}] Verbinde mit {per_args.printer_ip}:{per_args.mqtt_port} …")
        try:
            await loop.run_in_executor(None, client.connect)
            log.info(f"[Drucker {pid}] MQTT verbunden")
        except Exception as e:
            err = _mqtt_error_msg(e)
            log.warning(f"[Drucker {pid}] Verbindung fehlgeschlagen: {err} – Offline-Modus")
            bridge._state["print_state"] = "error"
            bridge._state["kobra_state"] = "offline"
            bridge._state["connection_error"] = err

        threading.Thread(
            target=bridge._poll_loop, args=(stop_event,),
            daemon=True, name=f"poll-{pid}",
        ).start()

        app = build_app(bridge)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, args.host, per_args.port)
        await site.start()
        runners.append((runner, client, pid))
        log.info(f"[Printer {pid}] Bridge running on http://{args.host}:{per_args.port}")

    import socket as _socket
    try:
        with _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM) as _s:
            _s.connect(("8.8.8.8", 80))
            _local_ip = _s.getsockname()[0]
    except Exception:
        _local_ip = args.host
    # An alle Bridge-Instanzen weitergeben — wird für absolute Webcam-URLs genutzt
    for _b in all_bridges.values():
        _b._local_ip = _local_ip
    log.info(f"OrcaSlicer → Klipper → Host: {_local_ip}  Ports: " +
             ", ".join(str(getattr(b._args, 'port', 0)) for b in all_bridges.values()))
    log.info("Ctrl-C zum Beenden")

    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        stop_event.set()
        for runner, client, pid in runners:
            try:
                await runner.cleanup()
            except Exception:
                pass
            try:
                client.disconnect()
            except Exception:
                pass
        log.info("Bridge beendet")


def _default_data_dir() -> str:
    """Persistenz-Verzeichnis: Docker setzt KX_DATA_DIR, Binary nutzt <exe-dir>/data,
    Dev-Script nutzt <repo>/data (oder /app/data falls vorhanden)."""
    if os.environ.get("KX_DATA_DIR"):
        return os.environ["KX_DATA_DIR"]
    if getattr(sys, "frozen", False):
        return os.path.join(os.path.dirname(sys.executable), "data")
    if os.path.isdir("/app"):
        return "/app/data"
    return os.path.normpath(os.path.join(_BASE, "..", "data"))


def main():
    parser = argparse.ArgumentParser(description="Moonraker-Bridge für Anycubic Kobra X")
    parser.add_argument("--printer-ip",  default=env_loader.PRINTER_IP,
                        help="IP-Adresse des Druckers")
    parser.add_argument("--mqtt-port",   type=int, default=env_loader.MQTT_PORT)
    parser.add_argument("--username",    default=env_loader.USERNAME)
    parser.add_argument("--password",    default=env_loader.PASSWORD)
    parser.add_argument("--mode-id",     default=env_loader.MODE_ID)
    parser.add_argument("--device-id",       default=env_loader.DEVICE_ID)
    parser.add_argument("--default-ams-slot",default=env_loader.DEFAULT_AMS_SLOT)
    parser.add_argument("--auto-leveling",   type=int, default=env_loader.AUTO_LEVELING)
    parser.add_argument("--camera-on-print", type=int, default=env_loader.CAMERA_ON_PRINT)
    parser.add_argument("--web-upload-warning", type=int, default=env_loader.WEB_UPLOAD_WARNING)

    parser.add_argument("--host",            default="0.0.0.0",
                        help="Bind-Adresse für den Bridge-Server")
    parser.add_argument("--port",        type=int, default=7125,
                        help="HTTP/WS-Port (Moonraker-Standard: 7125)")
    parser.add_argument("--data-dir",    default=_default_data_dir(),
                        help="Persistenz-Verzeichnis für GCode-Store und DB")
    parser.add_argument(
        "--ui-theme",
        default=os.environ.get("KX_UI_THEME", "default"),
        metavar="NAME",
        help="Web-UI-Theme (Ordner web/themes/NAME/, Standard: default). "
        "Alternativ: Umgebungsvariable KX_UI_THEME.",
    )
    args = parser.parse_args()
    if args.printer_ip and ":" in args.printer_ip:
        args.printer_ip = args.printer_ip.split(":")[0]

    # Windows braucht ProactorEventLoop für asyncio.create_subprocess_exec
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(run_bridge(args))


if __name__ == "__main__":
    main()
