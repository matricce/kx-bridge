"""
kobrax_moonraker_bridge.py – Moonraker-kompatibler HTTP/WebSocket-Bridge für Anycubic Kobra X

Emuliert die Moonraker/Klipper-API damit OrcaSlicer den Kobra X direkt ansteuern kann.

Verwendung:
  python kobrax_moonraker_bridge.py --printer-ip 192.168.178.94

OrcaSlicer-Konfiguration:
  Drucker-Typ: Klipper  |  Host: 127.0.0.1  |  Port: 7125
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

# Bei PyInstaller-Binary liegt alles neben sys.executable, sonst neben __file__
_BASE = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _BASE)
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

# Ring-Buffer für Browser-Log-Stream (letzte 200 Einträge)
import collections as _collections
_log_buffer: "_collections.deque[dict]" = _collections.deque(maxlen=500)
_log_sse_queues: "list[asyncio.Queue]" = []

class _BrowserLogHandler(logging.Handler):
    """Sendet Log-Records in den Ring-Buffer und alle offenen SSE-Queues."""
    _fmt = logging.Formatter(datefmt="%H:%M:%S")

    def emit(self, record: logging.LogRecord):
        entry = {
            "ts":    self._fmt.formatTime(record, "%H:%M:%S"),
            "lvl":   record.levelname,
            "name":  record.name,
            "msg":   record.getMessage(),
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
        log.info(f"Slicer-Schätzzeit: {secs}s ({m.group(1).strip()})")
    return secs


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
    """Liest filament_colour + filament_type aus GCode-Header (OrcaSlicer/PrusaSlicer).

    Gibt Liste von {color_hex, material} pro Slot zurück, leer wenn nicht gefunden.
    Liest nur die ersten 8KB (Header-Bereich).
    """
    try:
        header = data[:8192].decode("utf-8", errors="ignore")
        colors, materials = [], []
        for line in header.splitlines():
            if line.startswith("; filament_colour"):
                val = line.split("=", 1)[-1].strip()
                colors = [c.strip().lstrip("#") for c in val.split(";") if c.strip()]
            elif line.startswith("; filament_type"):
                val = line.split("=", 1)[-1].strip()
                materials = [m.strip() for m in val.split(";") if m.strip()]
        if not colors:
            return []
        result = []
        for i, hex_color in enumerate(colors):
            result.append({
                "slot_index": i,
                "color_hex":  "#" + hex_color.upper() if hex_color else "#FFFFFF",
                "material":   materials[i] if i < len(materials) else "PLA",
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
                    gcode_filaments TEXT
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

    def save_file(self, file_id: str, filename: str, data: bytes,
                  est_time_sec: int = 0, thumbnail_b64: str = "",
                  gcode_filaments: list | None = None) -> str:
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
                   (id, filename, path, size_bytes, uploaded_at, thumbnail_b64, est_print_time_sec, gcode_filaments)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (file_id, filename, path, len(data), now, thumbnail_b64 or None, est_time_sec or None, filaments_json)
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


class KobraXBridge:
    def __init__(self, client: KobraXClient, args=None, store=None, printer_id: str = "1", all_bridges=None):
        self.client = client
        self._args = args
        self._printer_id = printer_id
        self._all_bridges = all_bridges if all_bridges is not None else {}
        self.ws_clients: set[web.WebSocketResponse] = set()
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
        }
        self._ams_slots: list[dict] = []
        self._ams_loaded_slot: int = -1
        self._last_uploaded_file: str = ""
        self._store = store if store is not None else GCodeStore(args.data_dir)
        self._serve_dir_path: str = self._store._gcode_dir
        self._current_job_id: str = ""

        self._thumbnail_b64: str = ""

        # Register MQTT push callbacks
        client.callbacks["tempature/report"]      = self._on_temp
        client.callbacks["print/report"]          = self._on_print
        client.callbacks["info/report"]           = self._on_info
        client.callbacks["file/report"]           = self._on_file
        client.callbacks["multiColorBox/report"]  = self._on_multicolor_box
        client.callbacks["light/report"]          = self._on_light

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
                    log.info(f"Job gestartet: {self._current_job_id} für {filename}")

        # Job-History: Druckende erkennen
        if kobra_state in ("finished",) and self._current_job_id:
            self._store.finish_job(self._current_job_id, status="completed")
            log.info(f"Job abgeschlossen: {self._current_job_id}")
            self._current_job_id = ""
        elif kobra_state in ("stoped", "canceled") and self._current_job_id:
            self._store.finish_job(self._current_job_id, status="cancelled")
            log.info(f"Job abgebrochen: {self._current_job_id}")
            self._current_job_id = ""

        if kobra_state in ("stoped", "canceled"):
            self._state["progress"] = 0.0
            self._state["filename"] = ""
            self._state["file_ready"] = ""
            self._state["print_duration"] = 0
            self._state["remain_time"] = 0
            self._state["slicer_time"] = 0
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
        kobra_state = d.get("state", "")
        if kobra_state:
            self._state["print_state"] = KOBRA_TO_KLIPPER_STATE.get(kobra_state, "standby")
            self._state["kobra_state"] = kobra_state
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
        fan = d.get("fan_speed_pct")
        if fan is not None:
            self._state["fan_speed"] = int(fan)
        speed_mode = d.get("print_speed_mode")
        if speed_mode is not None:
            self._state["print_speed_mode"] = int(speed_mode)
        self._push_status_update()

    def _on_file(self, payload: dict):
        d = payload.get("data") or {}
        details = d.get("file_details") or {}
        thumb = details.get("thumbnail") or details.get("png_image") or ""
        if thumb:
            self._thumbnail_b64 = thumb
            log.info(f"Vorschaubild empfangen: {len(thumb)} Zeichen base64")
        self._push_status_update()

    def _on_multicolor_box(self, payload: dict):
        boxes = (payload.get("data") or {}).get("multi_color_box") or []
        if not boxes:
            return
        box = boxes[0]
        slots = box.get("slots") or []
        loaded = box.get("loaded_slot", -1)
        if loaded != -1:
            self._ams_loaded_slot = loaded
        # Tip-Forming: nach Einziehen (status=10) oder Ausziehen (status=11)
        # schickt der originale Slicer automatisch type=3 (Extruder-Rückzug)
        fs = box.get("feed_status") or {}
        current_status = fs.get("current_status")
        slot_index = fs.get("slot_index", 0)
        if current_status in (10, 11):
            import threading
            def _tip_form():
                import time; time.sleep(2)
                self.client.publish(
                    "multiColorBox", "feedFilament",
                    {"multi_color_box": [{"id": -1, "feed_status": {"slot_index": slot_index, "type": 3}}]},
                    timeout=0
                )
                log.info(f"Tip-Forming (type=3) nach status={current_status} slot={slot_index}")
            threading.Thread(target=_tip_form, daemon=True).start()
        if slots:
            self._ams_slots = slots
            log.info(f"AMS-Slots empfangen: {len(slots)}, loaded_slot={self._ams_loaded_slot}")
            self._push_status_update()

    def _on_light(self, payload: dict):
        d = payload.get("data") or {}
        self._state["light_on"]         = bool(d.get("status", 0))
        self._state["light_brightness"] = int(d.get("brightness", 80))
        self._push_status_update()

    # OrcaSlicer filament preset IDs (MoonrakerPrinterAgent.cpp mapping)
    _TRAY_INFO_IDX = {
        "PLA":      "OGFL99", "PLA-CF":   "OGFL98", "PLA SILK": "OGFL96",
        "PETG":     "OGFG99", "PETG-CF":  "OGFG98",
        "ABS":      "OGFB99", "ASA":      "OGFB98",
        "TPU":      "OGFT99", "PA":       "OGFP99", "PA-CF":    "OGFP98",
        "PC":       "OGFC99", "HIPS":     "OGFH99", "PVA":      "OGFV99",
    }

    def _build_lane_data(self) -> dict:
        """Baut BBL-AMS-JSON für OrcaSlicer DevFilaSystemParser::ParseV1_0."""
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
                    tray_info_idx = self._TRAY_INFO_IDX.get(material, "OGFL99")
                    tray_array.append({
                        "id":           str(slot_id),
                        "tag_uid":      "0000000000000000",
                        "tray_info_idx": tray_info_idx,
                        "tray_type":    material,
                        "tray_color":   color_hex,
                    })
                else:
                    tray_array.append({
                        "id":                str(slot_id),
                        "tag_uid":           "0000000000000000",
                        "tray_info_idx":     "",
                        "tray_type":         "",
                        "tray_color":        "00000000",
                        "tray_slot_placeholder": "1",
                    })

            ams_array.append({"id": str(ams_id), "info": "0002", "tray": tray_array})

        return {
            "ams":             ams_array,
            "ams_exist_bits":  format(ams_exist_bits, "X"),
            "tray_exist_bits": format(tray_exist_bits, "X"),
        }

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
        slots = self._ams_slots
        if not slots:
            return {}
        _TEMP = {"PLA": 210, "PETG": 230, "ABS": 240, "ASA": 250,
                 "TPU": 220, "PA": 260, "PC": 270, "HIPS": 220}
        num_gates = len(slots)
        gate_status, gate_material, gate_color, gate_temperature, gate_color_rgb = [], [], [], [], []
        for slot in slots:
            occupied = slot.get("status") == 5
            gate_status.append(1 if occupied else 0)
            material = slot.get("type", "PLA").upper() if occupied else ""
            gate_material.append(material)
            c = slot.get("color", [0, 0, 0])
            if occupied:
                gate_color.append("#{:02X}{:02X}{:02X}".format(*c[:3]))
                gate_color_rgb.append([round(c[0]/255, 3), round(c[1]/255, 3), round(c[2]/255, 3)])
            else:
                gate_color.append("")
                gate_color_rgb.append([0.0, 0.0, 0.0])
            gate_temperature.append(_TEMP.get(material, 210) if occupied else 0)
        return {
            "num_gates":          num_gates,
            "enabled":            True,
            "gate_status":        gate_status,
            "gate_material":      gate_material,
            "gate_color":         gate_color,
            "gate_temperature":   gate_temperature,
            "gate_color_rgb":     gate_color_rgb,
            "gate_filament_name": [""] * num_gates,
            "gate_spool_id":      [-1] * num_gates,
            "ttg_map":            list(range(num_gates)),
            "tool":               max(self._ams_loaded_slot, 0),
            "gate":               max(self._ams_loaded_slot, 0),
        }

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
            },
            "toolhead": {
                "position":         [0, 0, 0, 0],
                "homed_axes":       "xyz",
                "print_time":       s["print_duration"],
                "estimated_print_time": s["print_duration"],
            },
            "mmu": self._build_mmu_object(),
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
        # Letzten Job-Status + Dauer pro Datei ergänzen
        jobs = self._store.list_jobs(limit=500)
        last_job: dict = {}
        for j in reversed(jobs):
            last_job[j["gcode_file_id"]] = j
        for f in files:
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

    async def handle_kx_filament_slots(self, request):
        slots = []
        for i, s in enumerate(self._ams_slots):
            slots.append({
                "slot_index":  i,
                "material":    s.get("type", ""),
                "color_hex":   "#{:02X}{:02X}{:02X}".format(*s.get("color", [0,0,0])[:3]),
                "status":      "loaded" if s.get("status") == 5 else "empty",
                "nozzle_temp": 0,
            })
        return self._json_cors({"result": slots})

    async def handle_kx_history(self, request):
        limit  = int(request.rel_url.query.get("limit", 50))
        offset = int(request.rel_url.query.get("offset", 0))
        jobs   = self._store.list_jobs(limit=limit, offset=offset)
        return self._json_cors({"result": jobs})

    async def handle_kx_printers(self, request):
        host = request.host.split(":")[0]
        out = []
        for pid, br in self._all_bridges.items():
            if not (br._args.printer_ip or "").strip():
                continue  # "leerer" Drucker (kein IP) – nicht in der Liste anzeigen
            port = getattr(br._args, "port", 7125)
            out.append({
                "id":         pid,
                "name":       br._state.get("printer_name") or f"Drucker {pid}",
                "bridge_url": f"http://{host}:{port}",
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

        if assignments:
            ams_box_mapping = [
                {
                    "paint_index":   a.get("paint_index", i),
                    "ams_index":     a["slot_index"],
                    "paint_color":   a.get("paint_color", [255, 255, 255, 255]),
                    "ams_color":     a.get("ams_color",   [255, 255, 255, 255]),
                    "material_type": a.get("material", "PLA"),
                }
                for i, a in enumerate(assignments)
            ]
        else:
            # Kein Dialog → alle belegten Slots wie bei normalem Upload-Druck
            default_slot = getattr(self._args, "default_ams_slot", "auto")
            all_loaded = [(i, s) for i, s in enumerate(self._ams_slots) if s.get("status") == 5]
            if default_slot != "auto":
                try:
                    slot_idx = int(default_slot)
                    loaded = [(i, s) for i, s in all_loaded if i == slot_idx] or all_loaded
                except ValueError:
                    loaded = all_loaded
            else:
                loaded = all_loaded
            ams_box_mapping = [
                {
                    "paint_index":   i,
                    "ams_index":     i,
                    "paint_color":   [255, 255, 255, 255],
                    "ams_color":     [255, 255, 255, 255],
                    "material_type": s.get("type", "PLA"),
                }
                for i, s in loaded
            ]

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
                "model_objects_skip_parts": [],
            },
        }

        log.info(f"KX-Store Druckstart: {filename}  ams={len(ams_box_mapping)} slots  assignments={bool(assignments)}")
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
        # filter by requested objects if specified
        requested = dict(request.rel_url.query)
        if requested:
            filtered = {k: objects[k] for k in requested if k in objects}
        else:
            filtered = objects
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

    async def handle_file_upload(self, request):
        log.info(f"Upload-Request: {request.method} {request.path_qs}  CT={request.headers.get('Content-Type','')[:60]}")
        ct = request.headers.get("Content-Type", "")
        if "multipart" not in ct:
            return web.json_response({"error": "expected multipart"}, status=400)
        auto_print = False
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

        # Datei persistent im GCode-Store ablegen
        self._store.save_file(
            file_id=file_md5,
            filename=remote_filename,
            data=file_data,
            est_time_sec=est_time,
            thumbnail_b64=thumbnail_b64,
            gcode_filaments=gcode_filaments or None,
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
            loop.run_in_executor(None, lambda: self._start_print(remote_filename, serve_url, file_md5, file_size))
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

    def _start_print(self, filename: str, url: str = "", md5: str = "", filesize: int = 0):
        self._state["file_ready"] = ""
        default_slot = getattr(self._args, "default_ams_slot", "auto")
        all_loaded = [(i, s) for i, s in enumerate(self._ams_slots) if s.get("status") == 5]
        if default_slot != "auto":
            try:
                slot_idx = int(default_slot)
                loaded = [(i, s) for i, s in all_loaded if i == slot_idx]
                if not loaded:
                    log.warning(f"Standard-Slot {slot_idx} ist leer – fallback auf Auto")
                    loaded = all_loaded
            except ValueError:
                loaded = all_loaded
        else:
            loaded = all_loaded
        use_ams = len(loaded) > 0
        ams_box_mapping = [
            {
                "paint_index":  i,
                "ams_index":    i,
                "paint_color":  [255, 255, 255, 255],
                "ams_color":    [255, 255, 255, 255],
                "material_type": s.get("type", "PLA"),
            }
            for i, s in loaded
        ]
        log.info(f"AMS-Slots: {len(loaded)}/{len(self._ams_slots)} belegt → {[i for i,_ in loaded]}")
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
        log.info(f"print/start → {filename}  url={url}  ams={len(self._ams_slots)} slots")
        result = self.client.publish("print", "start", payload, timeout=15.0)
        if result:
            log.info(f"Druckstart bestätigt: state={result.get('state')}")
        else:
            log.warning("Druckstart: keine Antwort vom Drucker")

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
        if filament_assignments is not None:
            ams_box_mapping = [
                {
                    "paint_index":   a.get("paint_index", i),
                    "ams_index":     a["slot_index"],
                    "paint_color":   a.get("paint_color", [255, 255, 255, 255]),
                    "ams_color":     a.get("ams_color",   [255, 255, 255, 255]),
                    "material_type": a.get("material", "PLA"),
                }
                for i, a in enumerate(filament_assignments)
            ]
        else:
            # AMS-Mapping aus gecachtem State — leere Slots (status != 5) überspringen
            default_slot = getattr(self._args, "default_ams_slot", "auto")
            all_loaded = [(i, s) for i, s in enumerate(self._ams_slots) if s.get("status") == 5]
            if default_slot != "auto":
                try:
                    slot_idx = int(default_slot)
                    loaded = [(i, s) for i, s in all_loaded if i == slot_idx] or all_loaded
                except ValueError:
                    loaded = all_loaded
            else:
                loaded = all_loaded
            ams_box_mapping = [
                {
                    "paint_index":   i,
                    "ams_index":     i,
                    "paint_color":   [255, 255, 255, 255],
                    "ams_color":     [255, 255, 255, 255],
                    "material_type": s.get("type", "PLA"),
                }
                for i, s in loaded
            ]

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
                "model_objects_skip_parts": [],
            },
        }

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

    async def handle_index(self, request):
        html = r"""<!DOCTYPE html>
<html lang="de" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>KX-Bridge</title>
<style>
:root{
  --bg:#1a1a1f;--card:#24242c;--raised:#2e2e3a;--border:#3a3a4a;
  --txt:#f0f0f5;--txt2:#8888aa;--accent:#00c8ff;--accent2:#ff6b35;
  --ok:#4cde80;--err:#ff4d6d;--warn:#ffb020;
  --font:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  --mono:"JetBrains Mono","Fira Code",monospace;
}
[data-theme=light]{
  --bg:#f0f0f5;--card:#fff;--raised:#e8e8f0;--border:#d0d0e0;
  --txt:#1a1a2e;--txt2:#666680;
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--txt);font-family:var(--font);font-size:14px;min-height:100vh;display:flex;flex-direction:column}
a{color:var(--accent);text-decoration:none}

/* ── HEADER ── */
header{background:var(--card);border-bottom:1px solid var(--border);
  display:flex;align-items:center;gap:12px;padding:0 20px;height:52px;
  position:sticky;top:0;z-index:100}
.logo{font-size:18px;font-weight:700;color:var(--accent);letter-spacing:-.02em}
.hname{font-size:13px;color:var(--txt2)}
.hbadge{display:flex;align-items:center;gap:6px;font-size:12px;font-weight:600;
  padding:4px 10px;border-radius:20px;background:var(--raised);color:var(--txt2);
  text-transform:uppercase;letter-spacing:.04em}
.hbadge.printing{background:#0d2d1a;color:var(--ok)}
.hbadge.complete{background:#0d1f38;color:#60b0ff}
.hbadge.error{background:#2d0d0d;color:var(--err)}
.hbadge .dot{width:7px;height:7px;border-radius:50%;background:currentColor}
.hbadge.printing .dot{animation:pulse 1.4s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.25}}
.theme-btn{background:none;border:1px solid var(--border);color:var(--txt2);
  border-radius:8px;padding:6px 10px;cursor:pointer;font-size:13px;transition:.15s}
.theme-btn:hover{border-color:var(--accent);color:var(--accent)}
.conn-btn{border-radius:8px;padding:6px 12px;cursor:pointer;font-size:13px;
  font-weight:600;border:none;transition:.15s}
.conn-btn.disconnected{background:var(--accent);color:#fff}
.conn-btn.disconnected:hover{opacity:.85}
.conn-btn.connected{background:transparent;border:1px solid var(--border);color:var(--txt2)}
.conn-btn.connected:hover{border-color:#e05;color:#e05}

/* ── LAYOUT ── */
.layout{display:flex;flex:1;min-height:0}
nav.sidebar{width:200px;background:var(--card);border-right:1px solid var(--border);
  display:flex;flex-direction:column;padding:12px 8px;gap:2px;flex-shrink:0}
.nav-btn{background:none;border:none;color:var(--txt2);text-align:left;
  padding:9px 12px;border-radius:8px;cursor:pointer;font-size:13px;
  display:flex;align-items:center;gap:10px;transition:.12s;width:100%}
.nav-btn:hover{background:var(--raised);color:var(--txt)}
.nav-btn.active{background:var(--raised);color:var(--accent)}
.nav-icon{font-size:16px;width:20px;text-align:center}
main{flex:1;overflow-y:auto;padding:20px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px}

/* ── CARD ── */
.card{background:var(--card);border:1px solid var(--border);border-radius:12px;
  padding:18px;transition:box-shadow .15s,transform .15s}
.card:hover{box-shadow:0 4px 20px rgba(0,0,0,.3);transform:translateY(-1px)}
.card-title{font-size:11px;text-transform:uppercase;letter-spacing:.1em;color:var(--txt2);
  margin-bottom:14px;display:flex;align-items:center;gap:8px}
.card-title span{font-size:14px}

/* ── HERO ── */
.hero{grid-column:1/-1;display:grid;grid-template-columns:1fr 320px;gap:16px}
@media(max-width:900px){.hero{grid-template-columns:1fr}}
.cam-wrap{background:#0a0a0e;border-radius:10px;overflow:hidden;
  min-height:180px;max-height:320px;display:flex;align-items:center;justify-content:center;position:relative}
.cam-wrap img,.cam-wrap video{width:100%;max-height:320px;height:auto;display:block;object-fit:contain}
.cam-placeholder{color:var(--txt2);font-size:13px;text-align:center;padding:20px}
@keyframes spin{to{transform:rotate(360deg)}}
.cam-spinner{width:40px;height:40px;border:3px solid rgba(255,255,255,.15);
  border-top-color:var(--accent);border-radius:50%;animation:spin .8s linear infinite;display:none}
.cam-overlay{position:absolute;bottom:0;left:0;right:0;
  background:linear-gradient(transparent,rgba(0,0,0,.75));padding:14px}
.cam-toggle{position:absolute;top:10px;right:10px;background:rgba(0,0,0,.5);
  border:1px solid rgba(255,255,255,.2);color:#fff;border-radius:8px;
  padding:6px 10px;cursor:pointer;font-size:12px;backdrop-filter:blur(4px)}
.cam-toggle:hover{background:rgba(0,0,0,.7)}

/* ── PROGRESS ── */
.hero-info{display:flex;flex-direction:column;gap:12px}
.pct-big{font-size:52px;font-weight:700;line-height:1;color:var(--txt)}
.pct-big small{font-size:20px;font-weight:400;color:var(--txt2)}
.progress-bar{height:8px;background:var(--raised);border-radius:4px;overflow:hidden;margin:4px 0}
.progress-fill{height:100%;background:linear-gradient(90deg,var(--accent),#0080cc);
  border-radius:4px;transition:width .6s ease}
.meta-row{display:flex;justify-content:space-between;font-size:12px;color:var(--txt2)}
.layer-badge{background:var(--raised);border-radius:6px;padding:4px 8px;
  font-family:var(--mono);font-size:12px;color:var(--txt)}
.fname{font-size:12px;color:var(--txt2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
  background:var(--raised);border-radius:6px;padding:6px 8px}

/* ── PRINT CONTROLS ── */
.ctrl-btns{display:flex;gap:8px;flex-wrap:wrap}
.btn{border:none;border-radius:8px;padding:10px 16px;font-size:13px;font-weight:600;
  cursor:pointer;transition:opacity .15s,transform .1s;white-space:nowrap}
.btn:hover{opacity:.85;transform:translateY(-1px)}
.btn:active{transform:translateY(0)}
.btn-start{background:var(--ok);color:#0d2010}
.btn-pause{background:var(--raised);color:var(--txt);border:1px solid var(--border)}
.btn-resume{background:#0d2d1a;color:var(--ok);border:1px solid var(--ok)}
.btn-cancel{background:#2d0d0d;color:var(--err);border:1px solid var(--err)}
.btn-accent{background:var(--accent);color:#001a24}
.btn-sm{padding:7px 12px;font-size:12px}
.spd-btn{flex:1;border:1.5px solid var(--border);background:var(--raised);color:var(--txt);
  border-radius:10px;padding:14px 8px;font-size:13px;font-weight:600;cursor:pointer;
  transition:all .15s;display:flex;flex-direction:column;align-items:center;gap:4px}
.spd-btn:hover{border-color:var(--accent);color:var(--accent)}
.spd-btn.spd-active{border-color:var(--accent);background:rgba(0,200,255,.12);color:var(--accent)}
.spd-btn .spd-icon{font-size:22px}
.spd-bar{height:4px;border-radius:2px;background:var(--border);margin-top:10px;overflow:hidden}
.spd-bar-fill{height:100%;border-radius:2px;background:linear-gradient(90deg,var(--accent2),var(--accent));transition:width .3s}

/* ── TIME CARDS ── */
.time-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-top:8px}
.time-block{background:var(--raised);border-radius:10px;padding:10px 12px}
.time-label{font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:var(--txt2);margin-bottom:4px}
.time-val{font-size:20px;font-weight:700;font-family:var(--mono);color:var(--txt)}
/* ── TEMPS ── */
.temp-pair{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.temp-card-inner{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.temp-block{background:var(--raised);border-radius:10px;padding:14px;position:relative}
.temp-label{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--txt2);margin-bottom:6px}
.temp-row{display:flex;align-items:baseline;gap:6px}
.temp-val{font-size:30px;font-weight:700;font-family:var(--mono)}
.temp-unit{font-size:14px;color:var(--txt2)}
.temp-target{font-size:11px;color:var(--txt2);margin-top:2px}
.temp-arc{position:absolute;top:12px;right:12px}
.temp-edit{display:flex;gap:6px;margin-top:10px}
.temp-input{background:var(--bg);border:1px solid var(--border);color:var(--txt);
  border-radius:6px;padding:5px 8px;font-size:13px;font-family:var(--mono);width:70px}
.temp-input:focus{outline:none;border-color:var(--accent)}
.chart-wrap{margin-top:12px}
canvas.tchart{width:100%;height:60px;display:block;border-radius:6px;background:var(--raised)}

/* ── MOTION ── */
.joypad{display:grid;grid-template-columns:repeat(3,52px);
  grid-template-rows:repeat(3,52px);gap:6px;justify-content:center;margin:8px auto}
.joy{background:var(--raised);border:1px solid var(--border);color:var(--txt);
  border-radius:10px;font-size:18px;cursor:pointer;transition:.12s;
  display:flex;align-items:center;justify-content:center}
.joy:hover{background:var(--accent);color:#001a24;border-color:var(--accent)}
.joy:active{transform:scale(.93)}
.joy.home{font-size:14px;background:var(--bg)}
.step-btns{display:flex;gap:6px;justify-content:center;flex-wrap:wrap;margin-top:10px}
.step-btn{background:var(--raised);border:1px solid var(--border);color:var(--txt2);
  border-radius:6px;padding:5px 10px;font-size:12px;cursor:pointer;transition:.12s}
.step-btn.active,.step-btn:hover{background:var(--accent);color:#001a24;border-color:var(--accent)}
.home-btns{display:flex;gap:6px;flex-wrap:wrap;margin-top:10px;justify-content:center}

/* ── AMS ── */
.ams-slots{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}
.ams-slot{background:var(--raised);border-radius:10px;padding:10px;text-align:center;
  border:2px solid transparent;transition:.2s;position:relative}
.ams-slot.active{border-color:var(--slot-color,var(--accent));
  box-shadow:0 0 12px rgba(var(--slot-rgb,0,200,255),.3)}
.slot-circle{width:36px;height:36px;border-radius:50%;margin:0 auto 6px;border:2px solid rgba(255,255,255,.15)}
.slot-label{font-size:11px;color:var(--txt2);font-family:var(--mono)}
.slot-material{font-size:12px;font-weight:600;margin-bottom:2px}

/* ── LIGHT + FAN ── */
.toggle-row{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px}
.toggle-label{font-size:13px;font-weight:600}
.toggle{position:relative;width:44px;height:24px;cursor:pointer}
.toggle input{opacity:0;width:0;height:0;position:absolute}
.toggle-track{width:44px;height:24px;background:var(--raised);border-radius:12px;
  border:1px solid var(--border);transition:.25s;display:block}
.toggle input:checked+.toggle-track{background:var(--accent)}
.toggle-thumb{position:absolute;top:3px;left:3px;width:18px;height:18px;
  background:#fff;border-radius:50%;transition:.25s;pointer-events:none}
.toggle input:checked~.toggle-thumb{transform:translateX(20px)}
.slider-row{display:flex;align-items:center;gap:10px;margin-top:8px}
.slider-label{font-size:12px;color:var(--txt2);width:80px}
.slider{flex:1;-webkit-appearance:none;height:4px;border-radius:2px;
  background:var(--raised);outline:none;cursor:pointer}
.slider::-webkit-slider-thumb{-webkit-appearance:none;width:16px;height:16px;
  border-radius:50%;background:var(--accent);cursor:pointer;transition:.1s}
.slider::-webkit-slider-thumb:hover{transform:scale(1.2)}
.slider-val{font-family:var(--mono);font-size:12px;color:var(--txt);width:30px;text-align:right}

/* ── CONSOLE ── */
.console{background:#0a0a0e;border-radius:8px;padding:10px;font-family:var(--mono);
  font-size:11px;color:#8888aa;overflow-y:auto;line-height:1.6}
.console .ts{color:#444;margin-right:6px}
.console .msg-info{color:#8888aa}
.console .msg-ok{color:var(--ok)}
.console .msg-err{color:var(--err)}
.console .msg-warn{color:var(--warn)}

/* ── PANELS ── */
.panel{display:none}
.panel.active{display:block}

/* ── MODAL ── */
.modal-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);
  z-index:200;align-items:center;justify-content:center;padding:16px}
.modal-overlay.open{display:flex}
.modal-box{background:var(--card);border:1px solid var(--border);border-radius:14px;
  width:100%;max-width:480px;max-height:90vh;overflow-y:auto;padding:24px;
  display:flex;flex-direction:column;gap:18px}
.modal-header{display:flex;align-items:center;justify-content:space-between}
.modal-title{font-size:15px;font-weight:700;color:var(--txt)}
.modal-close{background:none;border:none;color:var(--txt2);font-size:20px;
  cursor:pointer;padding:4px 8px;border-radius:6px}
.modal-close:hover{background:var(--raised);color:var(--txt)}
.modal-section{font-size:10px;text-transform:uppercase;letter-spacing:.1em;
  color:var(--txt2);margin-bottom:6px;margin-top:4px}
.modal-field{display:flex;flex-direction:column;gap:4px;margin-bottom:10px}
.modal-field label{font-size:12px;color:var(--txt2)}
.modal-field input{background:var(--raised);border:1px solid var(--border);
  border-radius:7px;color:var(--txt);padding:7px 10px;font-size:13px;width:100%}
.modal-field input:focus{outline:none;border-color:var(--accent)}
.poll-btns{display:flex;gap:8px}
.poll-btn{flex:1;padding:7px;background:var(--raised);border:1px solid var(--border);
  border-radius:7px;color:var(--txt2);cursor:pointer;font-size:13px;transition:all .15s}
.poll-btn.active{background:var(--accent);border-color:var(--accent);color:#000;font-weight:600}
.update-row{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.update-status{font-size:12px;color:var(--txt2);flex:1;min-width:0}
.modal-save{width:100%;padding:10px;background:var(--accent);border:none;
  border-radius:8px;color:#000;font-weight:700;font-size:14px;cursor:pointer;margin-top:4px}
.modal-save:hover{opacity:.88}

/* ── BOTTOM NAV (mobile) ── */
nav.bottom-nav{display:none;position:fixed;bottom:0;left:0;right:0;
  background:var(--card);border-top:1px solid var(--border);
  justify-content:space-around;padding:8px 0 max(8px,env(safe-area-inset-bottom))}
.bnav-btn{background:none;border:none;color:var(--txt2);display:flex;
  flex-direction:column;align-items:center;gap:3px;cursor:pointer;font-size:10px;padding:4px 8px}
.bnav-btn.active{color:var(--accent)}
.bnav-icon{font-size:20px}

/* ── Tablet (769–1100px): schmale Sidebar ── */
@media(min-width:769px) and (max-width:1100px){
  nav.sidebar{width:52px;padding:12px 4px}
  .nav-btn .nav-text{display:none}
  .nav-btn{justify-content:center;padding:10px}
  .nav-icon{width:auto}
  .grid{grid-template-columns:repeat(2,1fr)}
  .hero{grid-template-columns:1fr}
}

/* ── Mobile (≤768px): Bottom-Nav, 1-Spalte ── */
@media(max-width:768px){
  nav.sidebar{display:none}
  nav.bottom-nav{display:flex}
  main{padding:10px;padding-bottom:72px}

  /* Header kompakt */
  header{padding:0 12px;gap:8px}
  .hname{display:none}

  /* 1-Spalten-Grid, full-width spans funktionieren weiterhin */
  .grid{grid-template-columns:1fr;gap:12px}

  /* Hero: Kamera über Info */
  .hero{grid-template-columns:1fr}
  .cam-wrap{max-height:220px}

  /* Temp-Pair und Temp-Card übereinander */
  .temp-pair{grid-template-columns:1fr}
  .temp-card-inner{grid-template-columns:1fr}

  /* AMS: 2 Spalten */
  .ams-slots{grid-template-columns:repeat(2,1fr)}

  /* Joypad etwas kleiner */
  .joypad{grid-template-columns:repeat(3,44px);grid-template-rows:repeat(3,44px);gap:5px}
  .joy{font-size:16px}

  /* Buttons größere Touch-Targets */
  .btn{padding:10px 14px;font-size:13px}
  .btn-sm{padding:8px 12px}
  .step-btn{padding:8px 12px;font-size:13px}

  /* Modal vollbreite auf kleinen Screens */
  .modal-box{padding:16px;border-radius:10px}
  .poll-btns{gap:6px}
}
</style>
</head>
<body>

<div id="conn-error-banner" style="display:none;background:#c0392b;color:#fff;padding:10px 18px;font-size:14px;text-align:center;position:sticky;top:0;z-index:999;"></div>
<div id="file-ready-banner" style="display:none;background:#1a6e3c;color:#fff;padding:10px 18px;font-size:14px;text-align:center;position:sticky;top:0;z-index:998;display:none;align-items:center;justify-content:center;gap:12px;flex-wrap:wrap">
  <span>📄 <span id="file-ready-name"></span></span>
  <button id="file-ready-btn" onclick="startReadyFile()"
    style="padding:5px 16px;background:#fff;color:#1a6e3c;border:none;border-radius:6px;font-weight:700;cursor:pointer;font-size:13px"></button>
  <button id="file-slots-btn" onclick="startReadyFileWithSlots()"
    style="padding:5px 16px;background:rgba(255,255,255,0.15);color:#fff;border:1px solid rgba(255,255,255,0.5);border-radius:6px;font-weight:700;cursor:pointer;font-size:13px"></button>
  <button id="file-cancel-btn" onclick="cancelReadyFile()"
    style="padding:5px 16px;background:rgba(255,255,255,0.15);color:#fff;border:1px solid rgba(255,255,255,0.5);border-radius:6px;font-weight:700;cursor:pointer;font-size:13px"></button>
</div>

<header>
  <div class="logo">⬡ KX-Bridge</div>
  <div style="flex:1"></div>
  <div id="printer-dropdown-wrap" style="display:none;position:relative">
    <button id="printer-dropdown-btn" onclick="togglePrinterDropdown()" style="background:var(--raised);border:1px solid var(--border);border-radius:6px;padding:4px 10px;color:var(--txt);cursor:pointer;font-size:13px;display:flex;align-items:center;gap:6px">
      <span id="h-pname">Anycubic Kobra X</span><span style="opacity:.5">▾</span>
    </button>
    <div id="printer-dropdown-menu" style="display:none;position:absolute;top:calc(100% + 4px);right:0;background:var(--card);border:1px solid var(--border);border-radius:8px;min-width:200px;z-index:200;box-shadow:0 4px 16px #0006;overflow:hidden">
    </div>
  </div>
  <div id="h-pname-single" class="hname">Anycubic Kobra X</div>
  <span id="h-version" style="font-size:11px;opacity:.5;margin-left:6px"></span>
  <div class="hbadge" id="h-badge"><span class="dot"></span><span id="h-state">Standby</span></div>
  <button class="theme-btn" onclick="toggleTheme()">☀ / ☾</button>
  <button class="theme-btn" onclick="toggleLang()" id="lang-btn">EN</button>
  <button class="theme-btn" onclick="openSettings()" id="settings-btn" title="Einstellungen">⚙</button>
  <button class="conn-btn disconnected" id="conn-btn" onclick="toggleConnection()">⚡ Verbinden</button>
</header>

<!-- ═══ SETTINGS MODAL ═══ -->
<div class="modal-overlay" id="settings-modal" onclick="if(event.target===this)closeSettings()">
  <div class="modal-box">
    <div class="modal-header">
      <span class="modal-title" id="modal-title-settings">Einstellungen</span>
      <button class="modal-close" onclick="closeSettings()">✕</button>
    </div>

    <div>
      <div class="modal-field" style="margin-bottom:12px">
        <label id="lbl-printer-name" style="font-weight:600">Drucker-Name</label>
        <input type="text" id="s-printer-name" placeholder="z.B. Kobra X Links">
      </div>
      <div class="modal-section" id="modal-sec-connection">Verbindung</div>
      <div class="modal-field">
        <label id="lbl-printer-ip">Drucker-IP</label>
        <input type="text" id="s-printer-ip" placeholder="192.168.x.x">
        <small id="lbl-ip-hint" style="color:#f80;display:none"></small>
      </div>
      <div class="modal-field">
        <label id="lbl-mqtt-port">MQTT-Port</label>
        <input type="number" id="s-mqtt-port" placeholder="9883">
      </div>
      <div class="modal-field">
        <label id="lbl-username">MQTT-Benutzername</label>
        <input type="text" id="s-username" placeholder="userXXXXXXXX" autocomplete="new-password">
      </div>
      <div class="modal-field">
        <label id="lbl-password">MQTT-Passwort</label>
        <input type="password" id="s-password" autocomplete="new-password">
      </div>
      <div class="modal-field">
        <label id="lbl-device-id">Device-ID</label>
        <input type="text" id="s-device-id" placeholder="32 Hex-Zeichen">
      </div>
      <div class="modal-field">
        <label id="lbl-mode-id">Mode-ID</label>
        <input type="text" id="s-mode-id" placeholder="20030">
      </div>
    </div>

    <div>
      <div class="modal-section" id="modal-sec-print">Druckeinstellungen</div>
      <div class="modal-field">
        <label id="lbl-default-slot">Standard-Slot (Einfarbdruck)</label>
        <select id="s-default-slot">
          <option value="auto" id="opt-slot-auto">Auto (alle belegten Slots)</option>
          <option value="0" id="opt-slot-0">Slot 1</option>
          <option value="1" id="opt-slot-1">Slot 2</option>
          <option value="2" id="opt-slot-2">Slot 3</option>
          <option value="3" id="opt-slot-3">Slot 4</option>
        </select>
      </div>
      <div class="modal-field" style="flex-direction:row;align-items:center;gap:10px">
        <input type="checkbox" id="s-auto-leveling" style="width:auto;margin:0">
        <label id="lbl-auto-leveling" style="margin:0;cursor:pointer" for="s-auto-leveling">Auto-Leveling vor Druck</label>
      </div>
    </div>

    <div>
      <div class="modal-section" id="modal-sec-poll">Poll-Intervall</div>
      <div class="poll-btns">
        <button class="poll-btn" onclick="setPoll(1000)" id="poll-1">1s</button>
        <button class="poll-btn active" onclick="setPoll(2000)" id="poll-2">2s</button>
        <button class="poll-btn" onclick="setPoll(5000)" id="poll-5">5s</button>
      </div>
    </div>

    <div>
      <div class="modal-section" id="modal-sec-version">Version</div>
      <div class="update-row">
        <span id="s-version-label" style="font-size:13px;color:var(--txt)">–</span>
        <button class="btn btn-sm" style="background:var(--raised);color:var(--txt)" onclick="checkUpdate()" id="btn-update-check">🔄 <span id="lbl-update-check">Auf Updates prüfen</span></button>
      </div>
      <div class="update-status" id="update-status" style="margin-top:6px"></div>
      <button class="btn btn-sm btn-accent" id="btn-update-apply" style="display:none;margin-top:8px" onclick="applyUpdate()">
        <span id="lbl-update-apply">Jetzt installieren</span>
      </button>
      <div id="update-changelog" style="display:none;margin-top:10px;background:var(--raised);border-radius:6px;padding:10px;font-size:11px;font-family:var(--mono);color:var(--txt2);white-space:pre-wrap;max-height:180px;overflow-y:auto;line-height:1.6"></div>
    </div>

    <button class="modal-save" onclick="saveSettings()" id="btn-save-settings">Speichern &amp; Neustart</button>
  </div>
</div>

<!-- ═══ AMS SLOT EDIT DIALOG ═══ -->
<div class="modal-overlay" id="slot-edit-modal" onclick="if(event.target===this)closeSlotEdit()">
  <div class="modal-box" style="max-width:340px">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
      <span class="modal-title" id="slot-edit-title"></span>
      <button onclick="closeSlotEdit()" style="background:none;border:none;color:var(--txt2);font-size:20px;cursor:pointer;line-height:1">✕</button>
    </div>
    <div style="display:flex;align-items:center;gap:16px;margin-bottom:20px">
      <div id="slot-edit-preview" style="width:56px;height:56px;border-radius:50%;border:3px solid rgba(255,255,255,.2);flex-shrink:0"></div>
      <div style="flex:1">
        <div style="font-size:11px;color:var(--txt2);margin-bottom:4px" id="lbl-slot-color"></div>
        <input type="color" id="slot-edit-color"
          oninput="document.getElementById('slot-edit-preview').style.background=this.value"
          style="width:100%;height:36px;border:1px solid var(--border);border-radius:6px;background:var(--raised);cursor:pointer;padding:2px">
      </div>
    </div>
    <div style="margin-bottom:20px">
      <div style="font-size:11px;color:var(--txt2);margin-bottom:6px" id="lbl-slot-material"></div>
      <div style="display:flex;flex-wrap:wrap;gap:6px" id="slot-mat-btns">
      </div>
      <input type="text" id="slot-edit-mat"
        oninput="highlightMatBtn(this.value)"
        style="margin-top:8px;width:100%;padding:6px 10px;background:var(--raised);border:1px solid var(--border);border-radius:6px;color:var(--txt);font-size:13px;box-sizing:border-box">
    </div>
    <button class="modal-save" id="btn-slot-edit-save" onclick="saveSlotEdit()"></button>
  </div>
</div>

<div class="layout">
  <nav class="sidebar">
    <button class="nav-btn active" onclick="showPanel('dashboard')" id="nb-dashboard">
      <span class="nav-icon">⊞</span><span class="nav-text">Dashboard</span></button>
    <button class="nav-btn" onclick="showPanel('printers');loadPrinterTab()" id="nb-printers">
      <span class="nav-icon">🖨</span><span class="nav-text">Drucker</span></button>
    <button class="nav-btn" onclick="showPanel('store');loadStore()" id="nb-store">
      <span class="nav-icon">🗂</span><span class="nav-text">Browser</span></button>
    <button class="nav-btn" onclick="showPanel('console');clearLogBadge()" id="nb-console">
      <span class="nav-icon">≡</span><span class="nav-text">Konsole</span><span id="log-badge" style="display:none;margin-left:4px;background:var(--err);color:#fff;border-radius:10px;font-size:10px;padding:1px 5px;font-weight:700"></span></button>
  </nav>

  <main>
    <!-- ═══ DASHBOARD ═══ -->
    <div class="panel active" id="panel-dashboard">
      <div class="grid">
        <!-- Kamera -->
        <div class="card" style="grid-column:1/-1">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px">
            <div class="card-title" style="margin-bottom:0"><span>📷</span> <span id="d-card-cam">Kamera</span></div>
            <div style="display:flex;align-items:center;gap:10px">
              <span id="d-lbl-light" style="font-size:12px;color:var(--txt2)">💡 Licht</span>
              <label class="toggle">
                <input type="checkbox" id="d-light-toggle" onchange="setLight()">
                <span class="toggle-track"></span>
                <span class="toggle-thumb"></span>
              </label>
            </div>
          </div>
          <div class="cam-wrap" id="cam-wrap">
            <div class="cam-placeholder" id="cam-placeholder"><span id="cam-placeholder-txt">📷 Kamera nicht gestartet</span></div>
            <div class="cam-spinner" id="cam-spinner"></div>
            <img id="cam-img" style="display:none;width:100%;height:auto" alt="Kamera">
            <div class="cam-overlay" id="cam-overlay" style="display:none">
              <div style="font-size:12px;color:#fff" id="cam-fname"></div>
            </div>
            <button class="cam-toggle" onclick="toggleCam()" id="cam-toggle-btn">▶ Kamera</button>
          </div>
        </div>

        <!-- Fortschritt -->
        <div class="card" style="grid-column:1/-1">
          <div class="card-title"><span>◉</span> <span id="d-card-progress">Fortschritt</span></div>
          <img id="d-thumbnail" src="" alt="" style="display:none;width:100%;max-height:160px;object-fit:contain;border-radius:8px;background:#111;margin-bottom:10px">
          <div class="pct-big"><span id="d-pct">0</span><small>%</small></div>
          <div style="display:flex;align-items:center;gap:10px;margin:8px 0">
            <div class="progress-bar" style="flex:1;margin:0"><div class="progress-fill" id="d-pbar" style="width:0%"></div></div>
            <div class="time-block" style="padding:6px 10px;min-width:72px;text-align:center;flex-shrink:0">
              <div class="time-label" id="d-lbl-layers"></div>
              <div class="time-val" style="font-size:16px" id="d-layers">–</div>
            </div>
          </div>
          <div class="time-grid">
            <div class="time-block">
              <div class="time-label" id="d-lbl-elapsed"></div>
              <div class="time-val" id="d-elapsed">–</div>
            </div>
            <div class="time-block" id="d-slicer-row" style="display:none">
              <div class="time-label" id="d-slicer-label"></div>
              <div class="time-val" id="d-slicer-time">–</div>
            </div>
            <div class="time-block" style="color:var(--acc)">
              <div class="time-label" id="d-lbl-remain"></div>
              <div class="time-val" id="d-remain" style="color:var(--acc)">–</div>
            </div>
          </div>
          <div class="fname" id="d-fname" title="" style="margin-top:6px">–</div>
          <div class="ctrl-btns" id="d-ctrl-btns" style="margin-top:12px">
            <button class="btn btn-pause btn-sm" id="d-btn-pause" onclick="printAction('pause')">⏸ Pause</button>
            <button class="btn btn-resume btn-sm" id="d-btn-resume" onclick="printAction('resume')">▶ Weiter</button>
            <button class="btn btn-cancel btn-sm" id="d-btn-cancel" onclick="confirmCancel()">✕ Stopp</button>
          </div>
        </div>

        <!-- Temperatursteuerung + Verlauf -->
        <div class="card" style="grid-column:1/-1">
          <div class="card-title"><span>⊙</span> <span id="d-card-temps">Temperaturen</span></div>
          <div class="temp-card-inner">
            <div class="temp-block">
              <div class="temp-label">Nozzle</div>
              <div class="temp-row">
                <div class="temp-val" id="d-nt">–</div>
                <div class="temp-unit">°C</div>
              </div>
              <div class="temp-target">→ <span id="d-nt-t">0</span>°C</div>
              <div class="progress-bar" style="margin:8px 0 0">
                <div class="progress-fill" id="d-ntbar" style="width:0%;background:linear-gradient(90deg,var(--accent2),#ffb020)"></div>
              </div>
              <div class="temp-edit" style="margin-top:10px">
                <input type="number" class="temp-input" id="p-nozzle-inp" placeholder="Ziel" min="0" max="300" style="flex:1">
                <button class="btn btn-sm btn-accent" onclick="setNozzle()"><span class="lbl-set">Set</span></button>
                <button class="btn btn-sm" style="background:var(--raised);color:var(--txt)" onclick="document.getElementById('p-nozzle-inp').value=0;setNozzle()"><span class="lbl-off">Aus</span></button>
              </div>
            </div>
            <div class="temp-block">
              <div class="temp-label" id="d-lbl-bed">Bett</div>
              <div class="temp-row">
                <div class="temp-val" id="d-bt">–</div>
                <div class="temp-unit">°C</div>
              </div>
              <div class="temp-target">→ <span id="d-bt-t">0</span>°C</div>
              <div class="progress-bar" style="margin:8px 0 0">
                <div class="progress-fill" id="d-btbar" style="width:0%;background:linear-gradient(90deg,#ff6b35,var(--warn))"></div>
              </div>
              <div class="temp-edit" style="margin-top:10px">
                <input type="number" class="temp-input" id="p-bed-inp" placeholder="Ziel" min="0" max="120" style="flex:1">
                <button class="btn btn-sm btn-accent" onclick="setBed()"><span class="lbl-set">Set</span></button>
                <button class="btn btn-sm" style="background:var(--raised);color:var(--txt)" onclick="document.getElementById('p-bed-inp').value=0;setBed()"><span class="lbl-off">Aus</span></button>
              </div>
            </div>
          </div>
          <div style="margin-top:14px">
            <div style="font-size:10px;color:var(--txt2);margin-bottom:4px" id="d-chart-label">Verlauf (letzte 60 Messungen)</div>
            <canvas id="d-chart" width="800" height="120" style="width:100%;height:120px;background:var(--raised);border-radius:8px"></canvas>
          </div>
        </div>

        <!-- Achsensteuerung -->
        <div class="card">
          <div class="card-title"><span>✛</span> <span id="ptitle-motion-xy">XY-Achsen</span></div>
          <div class="joypad">
            <div></div>
            <button class="joy" onclick="move(1,1,getStep())" title="Y+">▲</button>
            <div></div>
            <button class="joy" onclick="move(0,-1,getStep())" title="X−">◀</button>
            <button class="joy home" onclick="homeAll()" title="Home All">⌂</button>
            <button class="joy" onclick="move(0,1,getStep())" title="X+">▶</button>
            <div></div>
            <button class="joy" onclick="move(1,-1,getStep())" title="Y−">▼</button>
            <div></div>
          </div>
          <div class="step-btns">
            <button class="step-btn" onclick="setStep(this,0.1)">0.1</button>
            <button class="step-btn active" onclick="setStep(this,1)">1</button>
            <button class="step-btn" onclick="setStep(this,5)">5</button>
            <button class="step-btn" onclick="setStep(this,10)">10 mm</button>
          </div>
          <div class="home-btns">
            <button class="btn btn-sm" style="background:var(--raised);color:var(--txt)" onclick="homeZ()"><span class="lbl-home-z">Home Z</span></button>
            <button class="btn btn-sm" style="background:var(--raised);color:var(--txt)" onclick="homeXY()"><span class="lbl-home-xy">Home XY</span></button>
            <button class="btn btn-sm btn-accent" onclick="homeAll()"><span class="lbl-home-all">Home All</span></button>
            <button class="btn btn-sm" style="background:var(--raised);color:var(--txt)" onclick="disableMotors()"><span class="lbl-disable-motors">Motors Off</span></button>
          </div>
        </div>
        <div class="card">
          <div class="card-title"><span>↕</span> <span id="ptitle-motion-z">Z-Achse</span></div>
          <div class="joypad" style="grid-template-columns:52px;grid-template-rows:repeat(2,52px)">
            <button class="joy" onclick="move(2,1,getStep())" title="Z+">▲</button>
            <button class="joy" onclick="move(2,-1,getStep())" title="Z−">▼</button>
          </div>
          <div style="text-align:center;margin-top:8px;font-size:12px;color:var(--txt2)"><span class="lbl-step">Schrittweite:</span> <span id="step-display">1</span> mm</div>
        </div>

        <!-- Print Speed -->
        <div class="card">
          <div class="card-title"><span>🏎</span> <span id="d-card-speed">Druckgeschwindigkeit</span></div>
          <div style="display:flex;gap:8px;margin-top:4px">
            <button class="spd-btn" id="d-spd-1" onclick="setSpeed(1)">
              <span class="spd-icon">🐢</span>
              <span id="d-spd-lbl-1">Leise</span>
            </button>
            <button class="spd-btn spd-active" id="d-spd-2" onclick="setSpeed(2)">
              <span class="spd-icon">⚡</span>
              <span id="d-spd-lbl-2">Normal</span>
            </button>
            <button class="spd-btn" id="d-spd-3" onclick="setSpeed(3)">
              <span class="spd-icon">🚀</span>
              <span id="d-spd-lbl-3">Sport</span>
            </button>
          </div>
          <div class="spd-bar" style="margin-top:12px">
            <div class="spd-bar-fill" id="d-spd-bar" style="width:50%"></div>
          </div>
        </div>

        <!-- Lüfter -->
        <div class="card">
          <div class="card-title"><span>🌀</span> <span id="d-card-lightfan">Lüfter</span></div>
          <div class="slider-row">
            <input type="range" class="slider" min="0" max="100" value="0" id="d-fan" oninput="document.getElementById('d-fan-val').textContent=this.value" onchange="setFan()">
            <span class="slider-val" id="d-fan-val">0</span>
          </div>
          <div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap">
            <button class="btn btn-sm" style="background:var(--raised);color:var(--txt)" onclick="quickFan(0)">Aus</button>
            <button class="btn btn-sm" style="background:var(--raised);color:var(--txt)" onclick="quickFan(25)">25%</button>
            <button class="btn btn-sm" style="background:var(--raised);color:var(--txt)" onclick="quickFan(50)">50%</button>
            <button class="btn btn-sm" style="background:var(--raised);color:var(--txt)" onclick="quickFan(75)">75%</button>
            <button class="btn btn-sm btn-accent" onclick="quickFan(100)">100%</button>
          </div>
        </div>

        <!-- AMS -->
        <div class="card" style="grid-column:1/-1" id="d-ams-card">
          <div class="card-title"><span>◫</span> <span id="d-card-ams">AMS / Filamentbox</span></div>
          <div class="ams-slots" id="ams-slots">
            <div style="grid-column:1/-1;text-align:center;color:var(--txt2);padding:20px" id="ams-no-data">Keine AMS-Daten empfangen</div>
          </div>
          <div id="ams-controls" style="margin-top:16px;display:flex;flex-direction:column;gap:10px">
            <div style="font-size:12px;color:var(--txt2);margin-bottom:2px" id="ams-slot-lbl">Slot auswählen</div>
            <div style="display:flex;align-items:center;gap:10px">
              <input type="range" id="ams-slot-sel" min="0" max="3" step="1" value="0"
                class="slider" style="flex:1"
                oninput="document.getElementById('ams-slot-label').textContent='Slot '+(parseInt(this.value)+1)">
              <span id="ams-slot-label" style="min-width:48px;font-size:13px;font-weight:600">Slot 1</span>
            </div>
            <div style="display:flex;gap:10px">
              <button class="btn" style="flex:1" onclick="amsFeed(1)">⬇ <span class="lbl-feed">Einziehen</span></button>
              <button id="btn-unload" class="btn" style="flex:1" onclick="amsFeed(2)">⬆ <span class="lbl-unload">Ausziehen</span></button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ═══ CONSOLE ═══ -->
    <!-- ═══ DRUCKER ═══ -->
    <div class="panel" id="panel-printers">
      <div class="card">
        <div class="card-title" style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
          <span id="printers-panel-title">🖨 Drucker</span>
          <div style="display:flex;gap:8px">
            <button onclick="openAddPrinterDialog()" style="font-size:12px;padding:4px 12px;background:var(--accent);border:none;border-radius:6px;color:#fff;cursor:pointer;font-weight:600">+ <span id="add-printer-btn-label">Drucker hinzufügen</span></button>
            <button onclick="loadPrinterTab()" style="font-size:12px;padding:4px 12px;background:var(--raised);border:1px solid var(--border);border-radius:6px;color:var(--txt2);cursor:pointer">↻</button>
          </div>
        </div>
        <div id="printers-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:14px"></div>
      </div>
    </div>

    <!-- ═══ GCODE STORE ═══ -->
    <div class="panel" id="panel-store">
      <div class="card">
        <div class="card-title" style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
          <span id="store-panel-title">🗂 Datei-Browser</span>
          <button id="store-refresh-btn" onclick="loadStore()" style="font-size:12px;padding:4px 12px;background:var(--raised);border:1px solid var(--border);border-radius:6px;color:var(--txt2);cursor:pointer">↻ Aktualisieren</button>
        </div>
        <div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap">
          <input id="store-search" type="text" placeholder="🔍 Suche…" oninput="renderStore()"
            style="flex:1;min-width:140px;padding:6px 10px;background:var(--raised);border:1px solid var(--border);border-radius:6px;color:var(--txt);font-size:13px">
          <select id="store-filter" onchange="renderStore()"
            style="padding:6px 8px;background:var(--raised);border:1px solid var(--border);border-radius:6px;color:var(--txt);font-size:13px">
            <option value="all" id="sf-all">Alle</option>
            <option value="completed" id="sf-ok">✓ Erfolgreich</option>
            <option value="failed" id="sf-err">✗ Fehler</option>
            <option value="never" id="sf-new">Neu</option>
          </select>
          <select id="store-sort" onchange="renderStore()"
            style="padding:6px 8px;background:var(--raised);border:1px solid var(--border);border-radius:6px;color:var(--txt);font-size:13px">
            <option value="date_desc" id="ss-date">↓ Datum</option>
            <option value="name_asc" id="ss-name">A–Z Name</option>
            <option value="duration_asc" id="ss-dur">⏱ Druckzeit</option>
          </select>
        </div>
        <div id="store-empty" style="display:none;color:var(--txt2);text-align:center;padding:40px 0;font-size:14px">
        </div>
        <div id="store-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:14px"></div>
      </div>
    </div>

    <div class="panel" id="panel-console">
      <div class="card">
        <div class="card-title" style="display:flex;justify-content:space-between;align-items:center">
          <span><span>≡</span> <span id="ptitle-console">Ereignis-Log</span></span>
          <a id="btn-log-dl" href="/api/log/download" download="kx-bridge.log"
             style="font-size:12px;padding:4px 10px;background:var(--raised);border-radius:6px;color:var(--txt2);text-decoration:none">⬇ Download</a>
        </div>
        <div style="display:flex;gap:6px;margin-bottom:6px;flex-wrap:wrap;align-items:center">
          <input id="log-filter" type="text" placeholder="Filter…"
            oninput="renderLog()"
            style="flex:1;min-width:120px;padding:5px 10px;background:var(--raised);border:1px solid var(--border);border-radius:6px;color:var(--txt);font-size:12px;font-family:var(--mono)">
          <button id="btn-autoscroll" onclick="toggleAutoScroll()"
            style="font-size:12px;padding:5px 10px;border-radius:6px;border:1px solid var(--border);background:var(--accent);color:#fff;cursor:pointer;white-space:nowrap">⬇ Auto</button>
          <button onclick="consoleLogs=[];renderLog()"
            style="font-size:12px;padding:5px 10px;border-radius:6px;border:1px solid var(--border);background:var(--raised);color:var(--txt2);cursor:pointer">✕ Clear</button>
        </div>
        <div style="display:flex;gap:5px;margin-bottom:8px;flex-wrap:wrap">
          <span style="font-size:11px;color:var(--txt2);align-self:center;margin-right:2px">Dir:</span>
          <button class="log-dir-btn active" id="logdir-all"  onclick="setLogDir('all')"  style="font-size:11px;padding:3px 9px;border-radius:5px;border:1px solid var(--border);cursor:pointer"></button>
          <button class="log-dir-btn"        id="logdir-rx"   onclick="setLogDir('rx')"   style="font-size:11px;padding:3px 9px;border-radius:5px;border:1px solid var(--border);cursor:pointer">RX</button>
          <button class="log-dir-btn"        id="logdir-tx"   onclick="setLogDir('tx')"   style="font-size:11px;padding:3px 9px;border-radius:5px;border:1px solid var(--border);cursor:pointer">TX</button>
          <span style="font-size:11px;color:var(--txt2);align-self:center;margin-left:6px;margin-right:2px">Topic:</span>
          <button class="log-topic-btn" data-topic="multiColorBox" onclick="setLogTopic('multiColorBox')" style="font-size:11px;padding:3px 9px;border-radius:5px;border:1px solid var(--border);cursor:pointer">AMS</button>
          <button class="log-topic-btn" data-topic="print"         onclick="setLogTopic('print')"         style="font-size:11px;padding:3px 9px;border-radius:5px;border:1px solid var(--border);cursor:pointer">print</button>
          <button class="log-topic-btn" data-topic="info"          onclick="setLogTopic('info')"          style="font-size:11px;padding:3px 9px;border-radius:5px;border:1px solid var(--border);cursor:pointer">info</button>
          <button class="log-topic-btn" data-topic="status"        onclick="setLogTopic('status')"        style="font-size:11px;padding:3px 9px;border-radius:5px;border:1px solid var(--border);cursor:pointer">status</button>
        </div>
        <div class="console" id="console-log" style="height:calc(100vh - 260px);min-height:160px" onscroll="onLogScroll()"></div>
      </div>
    </div>
  </main>
</div>

<nav class="bottom-nav">
  <button class="bnav-btn active" onclick="showPanel('dashboard')" id="bnb-dashboard"><span class="bnav-icon">⊞</span>Dashboard</button>
  <button class="bnav-btn" onclick="showPanel('printers');loadPrinterTab()" id="bnb-printers"><span class="bnav-icon">🖨</span>Drucker</button>
  <button class="bnav-btn" onclick="showPanel('store');loadStore()" id="bnb-store"><span class="bnav-icon">🗂</span>Browser</button>
  <button class="bnav-btn" onclick="showPanel('console');clearLogBadge()" id="bnb-console"><span class="bnav-icon">≡</span>Log<span id="log-badge-bot" style="display:none;margin-left:3px;background:var(--err);color:#fff;border-radius:10px;font-size:10px;padding:1px 4px;font-weight:700"></span></button>
</nav>

<script>
// ── State ──
var S={nozzle_temp:0,nozzle_target:0,bed_temp:0,bed_target:0,
  print_state:'standby',filename:'',progress:0,print_duration:0,remain_time:0,
  curr_layer:0,total_layers:0,printer_name:'Kobra X',firmware_version:'–',
  camera_url:'',fan_speed:0,print_speed_mode:2,light_on:false,light_brightness:80,ams_slots:[]};
var tempHistory={n:[],b:[]};
var camOn=false;
var currentStep=1;
var currentPanel='dashboard';

// ── Theme ──
function toggleTheme(){
  var h=document.documentElement;
  h.setAttribute('data-theme',h.getAttribute('data-theme')==='dark'?'light':'dark');
  localStorage.setItem('theme',h.getAttribute('data-theme'));
}
(function(){var t=localStorage.getItem('theme');if(t)document.documentElement.setAttribute('data-theme',t)})();

// ── i18n ──
var LANG_DE={
  header_status_standby:'Bereit',header_status_printing:'Druckt',header_status_complete:'Fertig',header_status_error:'Fehler',
  kobra_free:'Bereit',kobra_busy:'Beschäftigt',kobra_printing:'Druckt',kobra_preheating:'Aufheizen',kobra_auto_leveling:'Nivellierung',kobra_checking:'Prüfung',kobra_updated:'Aktualisierung',kobra_init:'Initialisierung',kobra_pausing:'Pausiert...',kobra_paused:'Pausiert',kobra_resuming:'Fortsetzen...',kobra_resumed:'Fortgesetzt',kobra_stopping:'Stoppt...',kobra_stoped:'Gestoppt',kobra_finished:'Abgeschlossen',kobra_failed:'Fehler',kobra_canceled:'Abgebrochen',kobra_offline:'Offline',
  nav_dashboard:'Dashboard',nav_print:'Druck',nav_temps:'Temperaturen',nav_motion:'Achsen',nav_ams:'AMS',nav_extras:'Licht / Lüfter',nav_console:'Konsole',
  card_progress:'Fortschritt',card_temps:'Temperaturen',card_light_fan:'Lüfter',card_speed:'Druckgeschwindigkeit',card_cam:'Kamera',lbl_elapsed:'Verstrichen:',lbl_remaining:'Restzeit:',lbl_slicer_time:'Slicer-Schätzung:',lbl_layers:'Layer',
  speed_silent:'🐢 Leise',speed_normal:'⚡ Normal',speed_sport:'🚀 Sport',
  lbl_light:'💡 Licht',lbl_feed:'Einziehen',lbl_unload:'Ausziehen',
  cam_placeholder:'📷 Kamera nicht gestartet',btn_cam_start:'▶ Kamera',btn_cam_stop:'◼ Kamera',
  btn_pause:'⏸ Pause',btn_resume:'▶ Weiter',btn_cancel:'✕ Stopp',
  label_nozzle:'Nozzle',label_bed:'Bett',label_fan:'🌀 Lüfter',label_light:'💡 Licht',label_on_off:'Ein / Aus',label_speed:'Geschwindigkeit',
  panel_print_title:'Drucksteuerung',panel_print_btn_pause:'⏸ Pause',panel_print_btn_resume:'▶ Fortsetzen',panel_print_btn_cancel:'✕ Abbrechen',panel_print_temps_live:'Temperaturen (Live)',
  label_set:'Setzen',label_off:'Aus',
  panel_temps_nozzle:'Nozzle',panel_temps_bed:'Heizbett',panel_temps_chart:'Verlauf (letzte 60 Messungen)',label_target_c:'Ziel:',
  panel_motion_xy:'XY-Achsen',panel_motion_z:'Z-Achse',label_step:'Schrittweite:',btn_home_z:'Home Z',btn_home_xy:'Home XY',btn_home_all:'Home All',btn_disable_motors:'Motoren aus',
  panel_ams_title:'AMS / Filamentbox',ams_no_data:'Keine AMS-Daten empfangen',label_slot:'Slot',ams_empty:'Leer',
  panel_extras_light:'Licht',panel_extras_fan:'Lüfter',panel_extras_camera:'Kamera',btn_cam_start2:'▶ Start',btn_cam_stop2:'◼ Stop',
  panel_console_title:'Ereignis-Log',
  log_light_on:'Licht an',log_light_off:'Licht aus',log_fan:'Lüfter →',log_nozzle:'Nozzle →',log_bed:'Bett →',log_axis:'Achse',log_home:'Home',log_home_all:'Home All',log_cam_start:'Kamera gestartet:',log_cam_stop:'Kamera gestoppt',log_poll_error:'Poll-Fehler:',log_error:'Fehler:',
  confirm_cancel:'Druck wirklich abbrechen?',
  settings_title:'Einstellungen',settings_connection:'Verbindung',settings_print:'Druckeinstellungen',settings_poll:'Poll-Intervall',settings_version:'Version',
  settings_save:'Speichern & Neustart',settings_printer_name:'Drucker-Name',settings_printer_ip:'Drucker-IP',settings_mqtt_port:'MQTT-Port',
  settings_username:'MQTT-Benutzername',settings_password:'MQTT-Passwort',settings_device_id:'Device-ID',settings_mode_id:'Mode-ID',hint_ip_no_port:'Nur IP-Adresse, kein Port (z.B. 192.168.1.102)',
  settings_default_slot:'Standard-Slot (Einfarbdruck)',settings_slot_auto:'Auto (alle belegten Slots)',settings_auto_leveling:'Auto-Leveling vor Druck',
  update_check:'Auf Updates prüfen',update_checking:'Prüfe...',update_available:'verfügbar',update_none:'Bereits aktuell',
  update_apply:'Jetzt installieren',update_applying:'Lade herunter...',update_restarting:'Starte neu...',update_error:'Fehler',
  btn_connect:'⚡ Verbinden',btn_disconnect:'✕ Trennen',
  lbl_conn_error:'Verbindungsfehler:',
  slot_edit_title:'Slot bearbeiten',slot_edit_color:'Farbe',slot_edit_material:'Material',
  slot_edit_save:'💾 Speichern',slot_edit_custom:'z.B. PLA, PETG, ABS…',
  slot_edit_ok:'AMS Slot',
  log_dir_all:'Alle',
  file_ready_btn:'▶ Druck starten',
  file_slots_btn:'🎨 Slots wählen',
  file_cancel_btn:'✕ Abbrechen',
  nav_printers:'Drucker',
  add_printer:'Drucker hinzufügen',apd_lbl_ip:'Drucker-IP',apd_lbl_name:'Name (optional)',
  apd_fetching:'Hole Daten vom Drucker…',apd_success:'Drucker hinzugefügt, Bridge startet neu…',apd_err_ip:'Bitte IP-Adresse eingeben',
  printers_remove:'Drucker entfernen',printers_remove_confirm:'Drucker "{name}" entfernen? Die Bridge startet neu.',
  printers_active:'● aktiv',
  printers_switch:'Wechseln →',
  printers_current:'Aktueller Drucker',
  printers_loading:'Lade…',
  printers_none:'Keine Drucker konfiguriert.',
  printers_empty_hint:'Noch kein Drucker eingerichtet.',
  nav_browser:'Browser',
  panel_browser_title:'Datei-Browser',
  store_empty:'Noch keine Dateien hochgeladen.',
  store_refresh:'↻ Aktualisieren',
  store_print:'▶ Drucken',
  store_delete_confirm:'Datei löschen?',
  store_print_confirm:'Datei drucken?',
  store_no_results:'Keine Dateien gefunden.',
  store_never:'noch nicht gedruckt',
  sf_all:'Alle',sf_ok:'✓ Erfolgreich',sf_err:'✗ Fehler',sf_new:'Neu',
  ss_date:'↓ Datum',ss_name:'A–Z Name',ss_dur:'⏱ Druckzeit'
};
var LANG_EN={
  header_status_standby:'Ready',header_status_printing:'Printing',header_status_complete:'Complete',header_status_error:'Error',
  kobra_free:'Ready',kobra_busy:'Busy',kobra_printing:'Printing',kobra_preheating:'Preheating',kobra_auto_leveling:'Auto Leveling',kobra_checking:'Checking',kobra_updated:'Updating',kobra_init:'Initializing',kobra_pausing:'Pausing...',kobra_paused:'Paused',kobra_resuming:'Resuming...',kobra_resumed:'Resumed',kobra_stopping:'Stopping...',kobra_stoped:'Stopped',kobra_finished:'Finished',kobra_failed:'Error',kobra_canceled:'Cancelled',kobra_offline:'Offline',
  nav_dashboard:'Dashboard',nav_print:'Print',nav_temps:'Temperatures',nav_motion:'Motion',nav_ams:'AMS',nav_extras:'Light / Fan',nav_console:'Console',
  card_progress:'Progress',card_temps:'Temperatures',card_light_fan:'Fan',card_speed:'Print Speed',card_cam:'Camera',lbl_elapsed:'Elapsed:',lbl_remaining:'Remaining:',lbl_slicer_time:'Slicer estimate:',lbl_layers:'Layer',
  speed_silent:'🐢 Silent',speed_normal:'⚡ Normal',speed_sport:'🚀 Sport',
  lbl_light:'💡 Light',lbl_feed:'Load',lbl_unload:'Unload',
  cam_placeholder:'📷 Camera not started',btn_cam_start:'▶ Camera',btn_cam_stop:'◼ Camera',
  btn_pause:'⏸ Pause',btn_resume:'▶ Resume',btn_cancel:'✕ Stop',
  label_nozzle:'Nozzle',label_bed:'Bed',label_fan:'🌀 Fan',label_light:'💡 Light',label_on_off:'On / Off',label_speed:'Speed',
  panel_print_title:'Print Control',panel_print_btn_pause:'⏸ Pause',panel_print_btn_resume:'▶ Resume',panel_print_btn_cancel:'✕ Cancel',panel_print_temps_live:'Temperatures (Live)',
  label_set:'Set',label_off:'Off',
  panel_temps_nozzle:'Nozzle',panel_temps_bed:'Heated Bed',panel_temps_chart:'History (last 60 readings)',label_target_c:'Target:',
  panel_motion_xy:'XY Axes',panel_motion_z:'Z Axis',label_step:'Step size:',btn_home_z:'Home Z',btn_home_xy:'Home XY',btn_home_all:'Home All',btn_disable_motors:'Motors Off',
  panel_ams_title:'AMS / Filament Box',ams_no_data:'No AMS data received',label_slot:'Slot',ams_empty:'Empty',
  panel_extras_light:'Light',panel_extras_fan:'Fan',panel_extras_camera:'Camera',btn_cam_start2:'▶ Start',btn_cam_stop2:'◼ Stop',
  panel_console_title:'Event Log',
  log_light_on:'Light on',log_light_off:'Light off',log_fan:'Fan →',log_nozzle:'Nozzle →',log_bed:'Bed →',log_axis:'Axis',log_home:'Home',log_home_all:'Home All',log_cam_start:'Camera started:',log_cam_stop:'Camera stopped',log_poll_error:'Poll error:',log_error:'Error:',
  confirm_cancel:'Really cancel the print?',
  settings_title:'Settings',settings_connection:'Connection',settings_print:'Print Settings',settings_poll:'Poll Interval',settings_version:'Version',
  settings_save:'Save & Restart',settings_printer_name:'Printer Name',settings_printer_ip:'Printer IP',settings_mqtt_port:'MQTT Port',
  settings_username:'MQTT Username',settings_password:'MQTT Password',settings_device_id:'Device ID',settings_mode_id:'Mode ID',hint_ip_no_port:'IP address only, no port (e.g. 192.168.1.102)',
  settings_default_slot:'Default Slot (single color)',settings_slot_auto:'Auto (all loaded slots)',settings_auto_leveling:'Auto-Leveling before print',
  update_check:'Check for Updates',update_checking:'Checking...',update_available:'available',update_none:'Already up to date',
  update_apply:'Install Now',update_applying:'Downloading...',update_restarting:'Restarting...',update_error:'Error',
  btn_connect:'⚡ Connect',btn_disconnect:'✕ Disconnect',
  lbl_conn_error:'Connection error:',
  slot_edit_title:'Edit Slot',slot_edit_color:'Color',slot_edit_material:'Material',
  slot_edit_save:'💾 Save',slot_edit_custom:'e.g. PLA, PETG, ABS…',
  slot_edit_ok:'AMS Slot',
  log_dir_all:'All',
  file_ready_btn:'▶ Start Print',
  file_slots_btn:'🎨 Select Slots',
  file_cancel_btn:'✕ Cancel',
  nav_printers:'Printers',
  add_printer:'Add printer',apd_lbl_ip:'Printer IP',apd_lbl_name:'Name (optional)',
  apd_fetching:'Fetching data from printer…',apd_success:'Printer added, bridge restarting…',apd_err_ip:'Please enter an IP address',
  printers_remove:'Remove printer',printers_remove_confirm:'Remove printer "{name}"? The bridge will restart.',
  printers_active:'● active',
  printers_switch:'Switch →',
  printers_current:'Current printer',
  printers_loading:'Loading…',
  printers_none:'No printers configured.',
  printers_empty_hint:'No printer set up yet.',
  nav_browser:'Browser',
  panel_browser_title:'File Browser',
  store_empty:'No files uploaded yet.',
  store_refresh:'↻ Refresh',
  store_print:'▶ Print',
  store_delete_confirm:'Delete file?',
  store_print_confirm:'Print file?',
  store_no_results:'No files found.',
  store_never:'never printed',
  sf_all:'All',sf_ok:'✓ Completed',sf_err:'✗ Failed',sf_new:'New',
  ss_date:'↓ Date',ss_name:'A–Z Name',ss_dur:'⏱ Print time'
};
// Multi-Printer: BASE_URL aus Pathname (/printer2 → andere Bridge-Instanz)
var _printers=[];
var _activePrinter=null;
(function(){
  var path=window.location.pathname.replace(/\/+$/,'');
  var m=path.match(/^\/printer(\d+)$/);
  var idx=m?parseInt(m[1]):1;
  window._printerIndex=idx;
})();
function _apiUrl(path){
  if(_activePrinter&&_activePrinter.bridge_url){
    return _activePrinter.bridge_url.replace(/\/+$/,'')+path;
  }
  return path;
}
function initPrinters(){
  fetch('/kx/printers').then(function(r){return r.json()}).then(function(d){  // immer lokale Instanz für Drucker-Liste
    _printers=d.result||[];
    var idx=window._printerIndex||1;
    _activePrinter=_printers.find(function(p){return String(p.id)===String(idx)})||_printers[0]||null;
    renderPrinterDropdown();
  }).catch(function(){});
}
function renderPrinterDropdown(){
  var wrap=document.getElementById('printer-dropdown-wrap');
  var single=document.getElementById('h-pname-single');
  var name=_printers.length===0?'–':(_activePrinter?(_activePrinter.name||'Kobra X'):'Kobra X');
  var pname=document.getElementById('h-pname');
  if(pname)pname.textContent=name;
  if(single)single.textContent=name;
  if(_printers.length>1){
    if(wrap)wrap.style.display='';
    if(single)single.style.display='none';
    var menu=document.getElementById('printer-dropdown-menu');
    if(menu){
      menu.innerHTML=_printers.map(function(p){
        var active=_activePrinter&&String(p.id)===String(_activePrinter.id);
        var num=p.id;
        return '<a href="/printer'+num+'" style="display:block;padding:10px 14px;color:'+(active?'var(--accent)':'var(--txt)')+';text-decoration:none;font-size:13px;border-bottom:1px solid var(--border)" '+(active?'style="font-weight:600"':'')+'>'+
          (active?'▶ ':'')+p.name+'</a>';
      }).join('');
    }
  } else {
    if(wrap)wrap.style.display='none';
    if(single)single.style.display='';
  }
}
function togglePrinterDropdown(){
  var menu=document.getElementById('printer-dropdown-menu');
  if(menu)menu.style.display=menu.style.display==='none'?'block':'none';
}
document.addEventListener('click',function(e){
  var wrap=document.getElementById('printer-dropdown-wrap');
  if(wrap&&!wrap.contains(e.target)){
    var menu=document.getElementById('printer-dropdown-menu');
    if(menu)menu.style.display='none';
  }
});

var currentLang='de';
var T=LANG_DE;
function toggleLang(){
  currentLang=currentLang==='de'?'en':'de';
  T=currentLang==='de'?LANG_DE:LANG_EN;
  localStorage.setItem('lang',currentLang);
  document.getElementById('lang-btn').textContent=currentLang==='de'?'EN':'DE';
  document.documentElement.setAttribute('lang',currentLang);
  applyLang();
}
function applyLang(){
  // Nav
  var nb=document.getElementById('nb-dashboard');if(nb)nb.querySelector('.nav-text').textContent=T.nav_dashboard;
  nb=document.getElementById('nb-console');if(nb)nb.querySelector('.nav-text').textContent=T.nav_console;
  nb=document.getElementById('nb-printers');if(nb)nb.querySelector('.nav-text').textContent=T.nav_printers;
  nb=document.getElementById('nb-store');if(nb)nb.querySelector('.nav-text').textContent=T.nav_browser;
  // Bottom nav
  var bnb=document.getElementById('bnb-dashboard');if(bnb)bnb.lastChild.textContent=T.nav_dashboard;
  bnb=document.getElementById('bnb-console');if(bnb)bnb.lastChild.textContent=T.nav_console;
  bnb=document.getElementById('bnb-printers');if(bnb)bnb.lastChild.textContent=T.nav_printers;
  bnb=document.getElementById('bnb-store');if(bnb)bnb.lastChild.textContent=T.nav_browser;
  // Browser panel
  setText('printers-panel-title','🖨 '+T.nav_printers);
  setText('add-printer-btn-label',T.add_printer);
  setText('apd-title',T.add_printer);
  setText('apd-lbl-ip',T.apd_lbl_ip);
  setText('apd-lbl-name',T.apd_lbl_name);
  setText('store-panel-title','🗂 '+T.panel_browser_title);
  var srb=document.getElementById('store-refresh-btn');if(srb)srb.textContent=T.store_refresh;
  setText('store-empty',T.store_empty);
  setText('sf-all',T.sf_all);setText('sf-ok',T.sf_ok);setText('sf-err',T.sf_err);setText('sf-new',T.sf_new);
  setText('ss-date',T.ss_date);setText('ss-name',T.ss_name);setText('ss-dur',T.ss_dur);
  // Dashboard card titles
  setText('d-card-progress',T.card_progress);
  setText('d-card-temps',T.card_temps);
  setText('d-card-lightfan',T.card_light_fan);
  setText('d-card-speed',T.card_speed);
  setText('d-card-cam',T.card_cam);
  setText('d-card-ams',T.panel_ams_title);
  setText('d-lbl-elapsed',T.lbl_elapsed);
  setText('d-lbl-remain',T.lbl_remaining);
  setText('d-slicer-label',T.lbl_slicer_time);
  setText('d-lbl-layers',T.lbl_layers);
  setText('d-lbl-light',T.lbl_light);
  setText('d-lbl-bed',T.label_bed);
  // Dashboard buttons
  setText('d-btn-pause',T.btn_pause);
  setText('d-btn-resume',T.btn_resume);
  setText('d-btn-cancel',T.btn_cancel);
  setText('cam-toggle-btn',camOn?T.btn_cam_stop:T.btn_cam_start);
  setText('cam-placeholder-txt',T.cam_placeholder);
  // Temp labels
  document.querySelectorAll('.lbl-set').forEach(e=>e.textContent=T.label_set);
  document.querySelectorAll('.lbl-off').forEach(e=>e.textContent=T.label_off);
  setText('d-chart-label',T.panel_temps_chart);
  // Axis labels
  setText('ptitle-motion-xy',T.panel_motion_xy);
  setText('ptitle-motion-z',T.panel_motion_z);
  document.querySelectorAll('.lbl-home-z').forEach(e=>e.textContent=T.btn_home_z);
  document.querySelectorAll('.lbl-home-xy').forEach(e=>e.textContent=T.btn_home_xy);
  document.querySelectorAll('.lbl-home-all').forEach(e=>e.textContent=T.btn_home_all);
  document.querySelectorAll('.lbl-disable-motors').forEach(e=>e.textContent=T.btn_disable_motors);
  document.querySelectorAll('.lbl-step').forEach(e=>e.textContent=T.label_step);
  document.querySelectorAll('.temp-input').forEach(e=>e.setAttribute('placeholder',T.label_target_c.replace(':','')));
  // Console
  setText('ptitle-console',T.panel_console_title);
  // Settings modal
  setText('modal-title-settings',T.settings_title);
  setText('modal-sec-connection',T.settings_connection);
  setText('modal-sec-print',T.settings_print);
  setText('modal-sec-poll',T.settings_poll);
  setText('modal-sec-version',T.settings_version);
  setText('btn-save-settings',T.settings_save);
  setText('lbl-printer-name',T.settings_printer_name);
  setText('lbl-printer-ip',T.settings_printer_ip);
  setText('lbl-mqtt-port',T.settings_mqtt_port);
  setText('lbl-username',T.settings_username);
  setText('lbl-password',T.settings_password);
  setText('lbl-device-id',T.settings_device_id);
  setText('lbl-mode-id',T.settings_mode_id);
  setText('lbl-default-slot',T.settings_default_slot);
  setText('opt-slot-auto',T.settings_slot_auto);
  setText('lbl-auto-leveling',T.settings_auto_leveling);

  setText('lbl-update-check',T.update_check);
  setText('lbl-update-apply',T.update_apply);
  // Speed buttons
  setText('d-spd-lbl-1',T.speed_silent.replace(/^\S+\s/,''));
  setText('d-spd-lbl-2',T.speed_normal.replace(/^\S+\s/,''));
  setText('d-spd-lbl-3',T.speed_sport.replace(/^\S+\s/,''));
  // AMS feed/unload
  document.querySelectorAll('.lbl-feed').forEach(e=>e.textContent=T.lbl_feed);
  document.querySelectorAll('.lbl-unload').forEach(e=>e.textContent=T.lbl_unload);
  // conn-btn text (nur wenn nicht im Übergangszustand)
  updateConnBtn();
  // Slot-Edit-Dialog
  setText('lbl-slot-color',T.slot_edit_color);
  setText('lbl-slot-material',T.slot_edit_material);
  setText('btn-slot-edit-save',T.slot_edit_save);
  var mi=document.getElementById('slot-edit-mat');if(mi)mi.setAttribute('placeholder',T.slot_edit_custom);
  setText('logdir-all',T.log_dir_all);
  setText('file-ready-btn',T.file_ready_btn);
  setText('file-slots-btn',T.file_slots_btn);
  setText('file-cancel-btn',T.file_cancel_btn);
  setText('file-cancel-btn',T.file_cancel_btn);
}
function setText(id,txt){var el=document.getElementById(id);if(el)el.textContent=txt;}
(function(){
  var l=localStorage.getItem('lang')||'de';
  currentLang=l;T=l==='de'?LANG_DE:LANG_EN;
  document.getElementById('lang-btn').textContent=l==='de'?'EN':'DE';
  document.documentElement.setAttribute('lang',l);
  // defer until DOM ready
  window.addEventListener('DOMContentLoaded',function(){
    applyLang();
    // Kein Drucker konfiguriert? → direkt in den Drucker-Tab (zeigt "+ Drucker hinzufügen")
    fetch('/kx/printers').then(function(r){return r.json()}).then(function(d){
      if(!d.result||!d.result.length){showPanel('printers');loadPrinterTab();}
    }).catch(function(){});
  });
})();

// ── Panel nav ──
function showPanel(id){
  document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
  document.getElementById('panel-'+id).classList.add('active');
  document.querySelectorAll('.nav-btn,.bnav-btn').forEach(b=>b.classList.remove('active'));
  var nb=document.getElementById('nb-'+id);if(nb)nb.classList.add('active');
  var bnb=document.getElementById('bnb-'+id);if(bnb)bnb.classList.add('active');
  currentPanel=id;
}

// ── Console log ──
var consoleLogs=[];
var logAutoScroll=true;
var logBadgeCount=0;
var logDirFilter='all';   // 'all'|'rx'|'tx'
var logTopicFilter='';    // '' = no topic filter

function clog(msg,cls){
  cls=cls||'msg-info';
  var ts=new Date().toLocaleTimeString('de',{hour:'2-digit',minute:'2-digit',second:'2-digit'});
  _appendLog({ts:ts,lvl:'',name:'ui',msg:msg},cls);
}
function _lvlCls(lvl){
  if(lvl==='ERROR'||lvl==='CRITICAL')return'msg-err';
  if(lvl==='WARNING')return'msg-warn';
  if(lvl==='DEBUG')return'msg-info';
  return'msg-ok';
}
function _appendLog(entry,forceCls){
  var cls=forceCls||_lvlCls(entry.lvl);
  var label=entry.name?'['+entry.name+'] ':'';
  consoleLogs.push({ts:entry.ts,msg:label+entry.msg,cls:cls});
  if(consoleLogs.length>500)consoleLogs.shift();
  // Badge wenn Tab nicht aktiv und Fehler/Warnungen
  if(currentPanel!=='console'&&(cls==='msg-err'||cls==='msg-warn')){
    logBadgeCount++;
    var bc=logBadgeCount>99?'99+':logBadgeCount;
    ['log-badge','log-badge-bot'].forEach(function(id){var b=document.getElementById(id);if(b){b.style.display='inline';b.textContent=bc;}});
  }
  renderLog();
}
function setLogDir(dir){
  logDirFilter=dir;
  document.querySelectorAll('.log-dir-btn').forEach(function(b){
    b.style.background=b.id==='logdir-'+dir?'var(--accent)':'var(--raised)';
    b.style.color=b.id==='logdir-'+dir?'#fff':'var(--txt2)';
  });
  renderLog();
}
function setLogTopic(topic){
  var inp=document.getElementById('log-filter');
  var active=inp.value===topic;
  inp.value=active?'':topic;
  document.querySelectorAll('.log-topic-btn').forEach(function(b){
    var on=!active&&b.getAttribute('data-topic')===topic;
    b.style.background=on?'var(--accent)':'var(--raised)';
    b.style.color=on?'#fff':'var(--txt2)';
  });
  renderLog();
}
function renderLog(){
  var el=document.getElementById('console-log');
  if(!el)return;
  var filter=(document.getElementById('log-filter')||{}).value||'';
  var fl=filter.toLowerCase();
  var rows=consoleLogs.filter(function(l){
    var m=l.msg;
    if(logDirFilter==='rx'&&!/ RX[ (]/.test(m))return false;
    if(logDirFilter==='tx'&&!/ TX[ (]/.test(m))return false;
    if(fl&&!m.toLowerCase().includes(fl))return false;
    return true;
  });
  var savedScroll=logAutoScroll?null:el.scrollTop;
  el.innerHTML=rows.map(l=>`<div><span class="ts">${l.ts}</span><span class="${l.cls}">${escHtml(l.msg)}</span></div>`).join('');
  if(logAutoScroll)el.scrollTop=el.scrollHeight;
  else if(savedScroll!==null)el.scrollTop=savedScroll;
}
function onLogScroll(){
  var el=document.getElementById('console-log');
  if(!el)return;
  var atBottom=el.scrollHeight-el.scrollTop-el.clientHeight<30;
  if(!atBottom&&logAutoScroll){setAutoScroll(false);}
}
function toggleAutoScroll(){
  setAutoScroll(!logAutoScroll);
  if(logAutoScroll){var el=document.getElementById('console-log');if(el)el.scrollTop=el.scrollHeight;}
}
function setAutoScroll(on){
  logAutoScroll=on;
  var btn=document.getElementById('btn-autoscroll');
  if(btn){btn.style.background=on?'var(--accent)':'var(--raised)';btn.style.color=on?'#fff':'var(--txt2)';}
}
function clearLogBadge(){
  logBadgeCount=0;
  ['log-badge','log-badge-bot'].forEach(function(id){var b=document.getElementById(id);if(b)b.style.display='none';});
}
function escHtml(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
// SSE server-log stream
(function(){
  function connect(){
    var es=new EventSource('/api/log/stream');
    es.onmessage=function(e){try{_appendLog(JSON.parse(e.data));}catch(_){}};
    es.onerror=function(){es.close();setTimeout(connect,3000);};
  }
  window.addEventListener('DOMContentLoaded',connect);
})();

// ── Helpers ──
function fmtTime(s){if(!s||s<0)return'–';var m=Math.floor(s/60),h=Math.floor(m/60);m%=60;return h>0?h+'h '+m+'m':m+'m'}
function post(url,body){return fetch(_apiUrl(url),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})}
function clamp(v,lo,hi){return Math.min(hi,Math.max(lo,v))}

// ── Apply state to DOM ──
function applyState(){
  var s=S;
  // connection error banner – nur wenn überhaupt ein Drucker konfiguriert ist
  var banner=document.getElementById('conn-error-banner');
  if(banner){if(s.connection_error&&_printers.length>0){banner.textContent='⚠ '+(T.lbl_conn_error||'Connection error:')+' '+s.connection_error;banner.style.display='block';}else{banner.style.display='none';}}
  var frb=document.getElementById('file-ready-banner');
  if(frb){
    if(s.file_ready&&s.print_state==='standby'){
      document.getElementById('file-ready-name').textContent=s.file_ready;
      frb.style.display='flex';
    }else{frb.style.display='none';}
  }
  // header
  var b=document.getElementById('h-badge');
  b.className='hbadge '+s.print_state;
  document.getElementById('h-state').textContent=T['kobra_'+s.kobra_state]||s.kobra_state||T.header_status_standby;
  var _pn=_printers.length===0?'–':((_activePrinter&&_activePrinter.name)||s.printer_name);
  var _el=document.getElementById('h-pname');if(_el)_el.textContent=_pn;
  var _el2=document.getElementById('h-pname-single');if(_el2)_el2.textContent=_pn;
  var hv=document.getElementById('h-version');if(hv&&s.version)hv.textContent='v'+s.version;


  // temps
  var nt=document.getElementById('d-nt');if(nt)nt.textContent=s.nozzle_temp.toFixed(1);
  var ntt=document.getElementById('d-nt-t');if(ntt)ntt.textContent=s.nozzle_target.toFixed(0);
  var bt=document.getElementById('d-bt');if(bt)bt.textContent=s.bed_temp.toFixed(1);
  var btt=document.getElementById('d-bt-t');if(btt)btt.textContent=s.bed_target.toFixed(0);

  // temp bars (dashboard)
  var nb=document.getElementById('d-ntbar');if(nb)nb.style.width=clamp(s.nozzle_temp/300*100,0,100)+'%';
  var bb=document.getElementById('d-btbar');if(bb)bb.style.width=clamp(s.bed_temp/120*100,0,100)+'%';

  // progress
  var pct=Math.round(s.progress*100);
  var dpct=document.getElementById('d-pct');if(dpct)dpct.textContent=pct;
  var dpbar=document.getElementById('d-pbar');if(dpbar)dpbar.style.width=pct+'%';

  var layers=s.curr_layer&&s.total_layers?'L '+s.curr_layer+' / '+s.total_layers:'–';
  var dlayers=document.getElementById('d-layers');if(dlayers)dlayers.textContent=layers;

  var delapsed=document.getElementById('d-elapsed');if(delapsed)delapsed.textContent=fmtTime(s.print_duration);
  var dremain=document.getElementById('d-remain');if(dremain)dremain.textContent=s.remain_time>0?fmtTime(s.remain_time):'–';
  var dslrow=document.getElementById('d-slicer-row');
  var dsltime=document.getElementById('d-slicer-time');
  if(dslrow&&dsltime){
    if(s.slicer_time>0){dslrow.style.display='';dsltime.textContent=fmtTime(s.slicer_time);}
    else{dslrow.style.display='none';}
  }

  var fn=s.filename||'–';
  var dfname=document.getElementById('d-fname');if(dfname){dfname.textContent=fn;dfname.title=fn};
  var pfname=document.getElementById('p-fname');if(pfname){pfname.textContent=fn;pfname.title=fn};
  var cfo=document.getElementById('cam-fname');if(cfo)cfo.textContent=fn!=='–'?fn:'';

  // thumbnail
  var thumb=document.getElementById('d-thumbnail');
  if(thumb){
    if(s.thumbnail){
      thumb.src='data:image/png;base64,'+s.thumbnail;
      thumb.style.display='block';
    } else {
      thumb.style.display='none';
      thumb.src='';
    }
  }

  // light/fan sync
  document.getElementById('d-light-toggle').checked=s.light_on;
  var dfan=document.getElementById('d-fan');if(dfan)dfan.value=s.fan_speed;
  var dfanval=document.getElementById('d-fan-val');if(dfanval)dfanval.textContent=s.fan_speed;

  // speed mode buttons
  var spdWidths={1:25,2:55,3:90};
  [1,2,3].forEach(function(m){
    var b=document.getElementById('d-spd-'+m);
    if(b) b.classList.toggle('spd-active', s.print_speed_mode===m);
  });
  var spdBar=document.getElementById('d-spd-bar');
  if(spdBar) spdBar.style.width=(spdWidths[s.print_speed_mode]||55)+'%';

  // AMS
  if(s.ams_slots&&s.ams_slots.length){
    window._amsSlots=s.ams_slots;
    var html='';
    s.ams_slots.forEach(function(slot,i){
      var empty=slot.status!==5;
      var rgb=empty?[80,80,80]:(Array.isArray(slot.color)?slot.color:[128,128,128]);
      var col='rgb('+rgb[0]+','+rgb[1]+','+rgb[2]+')';
      var active=slot.status===1||slot.active;
      var pct=empty?T.ams_empty:(slot.consumables_percent!=null?slot.consumables_percent+'%':'–');
      var idx=slot.index!=null?slot.index:i;
      html+='<div class="ams-slot'+(active?' active':'')+(empty?' empty':'')+ '" style="--slot-color:'+col+';opacity:'+(empty?0.4:1)+';cursor:pointer" onclick="openSlotEdit('+i+')">'
        +'<div class="slot-circle" style="background:'+col+'"></div>'
        +'<div class="slot-material">'+(empty?'–':(slot.type||slot.material_type||'–'))+'</div>'
        +'<div class="slot-label">Slot '+(idx+1)+'</div>'
        +'<div class="slot-label" style="font-size:10px;color:var(--txt2)">'+pct+'</div>'
        +'<div style="font-size:9px;color:var(--txt2);margin-top:2px">✏</div>'
        +'</div>';
    });
    document.getElementById('ams-slots').innerHTML=html;
  }

  // camera overlay
  var co=document.getElementById('cam-overlay');
  if(co)co.style.display=(s.print_state==='printing'&&camOn)?'block':'none';

  // auto-start camera during print
  if(s.print_state==='printing'&&!camOn&&s.camera_url){
    camStart();
  }

  updateConnBtn();
}

function updateConnBtn(){
  var btn=document.getElementById('conn-btn');
  if(!btn)return;
  var offline=S.kobra_state==='offline';
  if(offline){
    btn.className='conn-btn disconnected';
    btn.textContent=T.btn_connect||'⚡ Verbinden';
  } else {
    btn.className='conn-btn connected';
    btn.textContent=T.btn_disconnect||'✕ Trennen';
  }
}

function toggleConnection(){
  var btn=document.getElementById('conn-btn');
  var offline=S.kobra_state==='offline';
  btn.disabled=true;
  btn.textContent='…';
  var url=offline?'/api/connect':'/api/disconnect';
  post(url,{}).then(function(r){return r.json()}).then(function(r){
    btn.disabled=false;
    if(r.error)addLog('Error: '+r.error);
  }).catch(function(){btn.disabled=false;});
}

// ── Temp history + chart ──
function updateHistory(){
  tempHistory.n.push(S.nozzle_temp);
  tempHistory.b.push(S.bed_temp);
  if(tempHistory.n.length>60)tempHistory.n.shift();
  if(tempHistory.b.length>60)tempHistory.b.shift();
  drawChart('d-chart',tempHistory,[{data:tempHistory.n,color:'#00c8ff',max:300},{data:tempHistory.b,color:'#ff6b35',max:120}]);
}
function drawChart(id,_,series){
  var canvas=document.getElementById(id);if(!canvas)return;
  var ctx=canvas.getContext('2d');
  var W=canvas.offsetWidth*window.devicePixelRatio||canvas.width;
  var H=canvas.offsetHeight*window.devicePixelRatio||canvas.height;
  canvas.width=W;canvas.height=H;
  ctx.clearRect(0,0,W,H);
  series.forEach(function(s){
    var data=s.data;if(!data.length)return;
    var max=s.max;
    ctx.beginPath();ctx.strokeStyle=s.color;ctx.lineWidth=2;ctx.lineJoin='round';
    data.forEach(function(v,i){
      var x=i/(Math.max(data.length-1,1))*(W-4)+2;
      var y=H-4-(v/max)*(H-8);
      if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y);
    });
    ctx.stroke();
  });
}

// ── Settings Modal ──
var _updateTag='';
var _updateUrl='';
function openSettings(){
  // Titel mit aktivem Drucker-Namen aktualisieren
  var pname=_activePrinter&&_activePrinter.name?_activePrinter.name:null;
  var title=document.getElementById('modal-title-settings');
  if(title)title.textContent=T.settings_title+(pname?' – '+pname:'');
  fetch(_apiUrl('/api/settings')).then(function(r){return r.json()}).then(function(d){
    document.getElementById('s-printer-name').value=d.printer_name||'';
    document.getElementById('s-printer-ip').value=d.printer_ip||'';
    document.getElementById('s-mqtt-port').value=d.mqtt_port||9883;
    document.getElementById('s-username').value=d.username||'';
    document.getElementById('s-password').value=d.password||'';
    document.getElementById('s-device-id').value=d.device_id||'';
    document.getElementById('s-mode-id').value=d.mode_id||'';
    document.getElementById('s-default-slot').value=d.default_ams_slot||'auto';
    document.getElementById('s-auto-leveling').checked=(d.auto_leveling===undefined?true:!!d.auto_leveling);
  });
  var v=localStorage.getItem('pollInterval')||'2000';
  document.querySelectorAll('.poll-btn').forEach(function(b){b.classList.remove('active')});
  var pb=document.getElementById('poll-'+Math.round(parseInt(v)/1000));
  if(pb)pb.classList.add('active');
  document.getElementById('s-version-label').textContent='v'+('__VERSION__'||'?');
  document.getElementById('update-status').textContent='';
  document.getElementById('btn-update-apply').style.display='none';
  var cl=document.getElementById('update-changelog');if(cl)cl.style.display='none';
  _updateTag='';_updateUrl='';
  document.getElementById('settings-modal').classList.add('open');
}
function closeSettings(){
  document.getElementById('settings-modal').classList.remove('open');
}

// ── AMS Slot Edit ──
var _slotEditIndex=-1;
var _MAT_PRESETS=['PLA','PETG','ABS','ASA','TPU','PA','PC','HIPS'];
function openSlotEdit(i){
  var slot=(window._amsSlots||[])[i]||{};
  var index=slot.index!=null?slot.index:i;
  _slotEditIndex=index;
  document.getElementById('slot-edit-title').textContent=T.slot_edit_title+' '+(index+1);
  var rgb=Array.isArray(slot.color)?slot.color:[128,128,128];
  var hex='#'+rgb.map(function(v){return('0'+Math.min(255,v).toString(16)).slice(-2)}).join('');
  var ci=document.getElementById('slot-edit-color');
  ci.value=hex;
  document.getElementById('slot-edit-preview').style.background=hex;
  var mat=(slot.type||'PLA').toUpperCase();
  document.getElementById('slot-edit-mat').value=mat;
  var btns=document.getElementById('slot-mat-btns');
  btns.innerHTML=_MAT_PRESETS.map(function(m){
    return '<button class="mat-preset-btn" data-mat="'+m+'" onclick="selectMatPreset(\''+m+'\')" '
      +'style="padding:4px 10px;border-radius:6px;border:1px solid var(--border);cursor:pointer;font-size:12px;'
      +(m===mat?'background:var(--accent);color:#fff':'background:var(--raised);color:var(--txt2)')+'">'+m+'</button>';
  }).join('');
  document.getElementById('slot-edit-modal').classList.add('open');
}
function closeSlotEdit(){
  document.getElementById('slot-edit-modal').classList.remove('open');
}
function startReadyFile(){
  var btn=document.getElementById('file-ready-btn');
  if(btn){btn.disabled=true;btn.textContent='…';}
  post('/printer/print/start',{filename:S.file_ready})
    .then(function(r){return r.json();})
    .then(function(r){
      document.getElementById('file-ready-banner').style.display='none';
      if(btn){btn.disabled=false;setText('file-ready-btn',T.file_ready_btn);}
    })
    .catch(function(e){
      clog((T.log_error||'Error:')+' '+e,'msg-err');
      if(btn){btn.disabled=false;setText('file-ready-btn',T.file_ready_btn);}
    });
}
function cancelReadyFile(){
  post('/api/file_ready/clear',{})
    .then(function(){document.getElementById('file-ready-banner').style.display='none';});
}
function selectMatPreset(m){
  document.getElementById('slot-edit-mat').value=m;
  highlightMatBtn(m);
}
function highlightMatBtn(val){
  document.querySelectorAll('.mat-preset-btn').forEach(function(b){
    var on=b.getAttribute('data-mat')===val.toUpperCase();
    b.style.background=on?'var(--accent)':'var(--raised)';
    b.style.color=on?'#fff':'var(--txt2)';
  });
}
function hexToRgb(hex){
  var r=parseInt(hex.slice(1,3),16),g=parseInt(hex.slice(3,5),16),b=parseInt(hex.slice(5,7),16);
  return[r,g,b];
}
function saveSlotEdit(){
  var hex=document.getElementById('slot-edit-color').value;
  var mat=document.getElementById('slot-edit-mat').value.trim().toUpperCase()||'PLA';
  var color=hexToRgb(hex);
  post('/api/ams/set_slot',{index:_slotEditIndex,type:mat,color:color})
    .then(function(r){return r.json();})
    .then(function(r){
      closeSlotEdit();
      clog((T.slot_edit_ok||'AMS Slot')+' '+(_slotEditIndex+1)+': '+mat+' '+hex,'msg-ok');
    })
    .catch(function(e){clog('Fehler: '+e,'msg-err');});
}
document.addEventListener('DOMContentLoaded',function(){
  document.getElementById('s-printer-ip').addEventListener('input',function(){
    var hint=document.getElementById('lbl-ip-hint');
    if(this.value.includes(':')){hint.textContent=T.hint_ip_no_port;hint.style.display='block';}
    else{hint.style.display='none';}
  });
});
function setPoll(ms){
  document.querySelectorAll('.poll-btn').forEach(function(b){b.classList.remove('active')});
  var id='poll-'+Math.round(ms/1000);
  var pb=document.getElementById(id);if(pb)pb.classList.add('active');
  localStorage.setItem('pollInterval',ms);
  clearInterval(pollTimer);
  pollTimer=setInterval(poll,ms);
}
function saveSettings(){
  var btn=document.getElementById('btn-save-settings');
  btn.disabled=true;btn.textContent='…';
  post('/api/settings',{
    printer_name:     document.getElementById('s-printer-name').value,
    printer_ip:       document.getElementById('s-printer-ip').value,
    mqtt_port:        parseInt(document.getElementById('s-mqtt-port').value)||9883,
    username:         document.getElementById('s-username').value,
    password:         document.getElementById('s-password').value,
    device_id:        document.getElementById('s-device-id').value,
    mode_id:          document.getElementById('s-mode-id').value,
    default_ams_slot: document.getElementById('s-default-slot').value,
    auto_leveling:    document.getElementById('s-auto-leveling').checked?1:0,
  }).then(function(){
    btn.textContent=T.update_restarting;
    setTimeout(function(){
      btn.disabled=false;
      setText('btn-save-settings',T.settings_save);
      closeSettings();
      poll();
    },4000);
  }).catch(function(e){
    btn.disabled=false;setText('btn-save-settings',T.settings_save);
    clog('Settings-Fehler: '+e,'msg-err');
  });
}
function checkUpdate(){
  var sb=document.getElementById('update-status');
  sb.textContent=T.update_checking;
  document.getElementById('btn-update-apply').style.display='none';
  _updateTag='';_updateUrl='';
  fetch(_apiUrl('/api/update/check')).then(function(r){return r.json()}).then(function(d){
    if(d.error){sb.textContent=T.update_error+': '+d.error;return;}
    var cl=document.getElementById('update-changelog');
    if(d.changelog&&d.changelog.trim()){cl.textContent=d.changelog;cl.style.display='block';}
    else{cl.style.display='none';}
    if(d.update_available){
      sb.textContent='v'+d.latest+' '+T.update_available;
      sb.style.color='var(--ok)';
      _updateTag=d.tag;_updateUrl=d.download_url;
      document.getElementById('btn-update-apply').style.display='inline-block';
    } else {
      sb.textContent=T.update_none;
      sb.style.color='var(--txt2)';
    }
  }).catch(function(e){sb.textContent=T.update_error+': '+e;});
}
function applyUpdate(){
  if(!_updateUrl)return;
  var sb=document.getElementById('update-status');
  var btn=document.getElementById('btn-update-apply');
  btn.disabled=true;sb.textContent=T.update_applying;
  post('/api/update/apply',{download_url:_updateUrl,tag:_updateTag}).then(function(){
    sb.textContent=T.update_restarting;
    closeSettings();
    setTimeout(function(){poll();},5000);
  }).catch(function(e){
    btn.disabled=false;sb.textContent=T.update_error+': '+e;
  });
}

// ── Poll ──
async function poll(){
  try{
    var r=await fetch(_apiUrl('/api/state'));
    if(!r.ok)return;
    var d=await r.json();
    Object.assign(S,d);
    applyState();
    updateHistory();
  }catch(e){clog(T.log_poll_error+' '+e,'msg-err')}
}
var pollTimer;
(function(){
  var ms=parseInt(localStorage.getItem('pollInterval')||'2000');
  initPrinters();
  poll();pollTimer=setInterval(poll,ms);
})();

// ── Print actions ──
function printAction(a){
  post('/printer/print/'+a,{}).then(function(){clog('Druck: '+a,'msg-ok');poll()})
    .catch(function(e){clog('Fehler: '+e,'msg-err')});
}
function confirmCancel(){if(confirm('Druck wirklich abbrechen?'))printAction('cancel')}

// ── Axis motion ──
// axis codes: 0=X, 1=Y, 2=Z
// move_type 1=relative, distance positive/negative
function getStep(){return currentStep}
function setStep(btn,v){
  currentStep=v;
  document.querySelectorAll('.step-btn').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById('step-display').textContent=v;
}
function move(axis,dir,dist){
  // axis: 0=X,1=Y,2=Z → printer axis codes: 1=X,2=Y,3=Z
  var axisMap={0:1,1:2,2:3};
  post('/api/axis',{axis:axisMap[axis],move_type:1,distance:dir*dist})
    .then(function(){clog('Achse '+(axis===0?'X':axis===1?'Y':'Z')+' '+(dir>0?'+':'')+dir*dist+'mm','msg-ok')})
    .catch(function(e){clog('Achse-Fehler: '+e,'msg-err')});
}
function homeAll(){
  post('/api/axis',{axis:5,move_type:2,distance:0})
    .then(function(){clog('Home All','msg-ok')})
    .catch(function(e){clog('Home-Fehler: '+e,'msg-err')});
}
function homeXY(){
  post('/api/axis',{axis:4,move_type:2,distance:0})
    .then(function(){clog('Home XY','msg-ok')})
    .catch(function(e){clog('Home-Fehler: '+e,'msg-err')});
}
function homeZ(){
  post('/api/axis',{axis:3,move_type:2,distance:0})
    .then(function(){clog('Home Z','msg-ok')})
    .catch(function(e){clog('Home-Fehler: '+e,'msg-err')});
}
function disableMotors(){
  post('/api/axis',{action:'turnOff'})
    .then(function(){clog('Motors Off','msg-ok')})
    .catch(function(e){clog('Motors-Fehler: '+e,'msg-err')});
}

// ── Temperature ──
function setNozzle(){
  var v=parseFloat(document.getElementById('p-nozzle-inp').value||0);
  post('/api/temperature',{nozzle:v,bed:S.bed_target})
    .then(function(){clog('Nozzle → '+v+'°C','msg-ok')})
    .catch(function(e){clog('Temp-Fehler: '+e,'msg-err')});
}
function setBed(){
  var v=parseFloat(document.getElementById('p-bed-inp').value||0);
  post('/api/temperature',{nozzle:S.nozzle_target,bed:v})
    .then(function(){clog(T.label_bed+' → '+v+'°C','msg-ok')})
    .catch(function(e){clog('Temp-Fehler: '+e,'msg-err')});
}

// ── Light ──
function setLight(){
  var on=document.getElementById('d-light-toggle').checked;
  post('/api/light',{on:on,brightness:80})
    .then(function(){clog('Licht '+(on?'an, '+br+'%':'aus'),'msg-ok')})
    .catch(function(e){clog('Licht-Fehler: '+e,'msg-err')});
}

// ── Print Speed ──
function setSpeed(mode){
  S.print_speed_mode=mode;
  [1,2,3].forEach(function(m){
    var b=document.getElementById('d-spd-'+m);
    if(b) b.classList.toggle('spd-active',m===mode);
  });
  post('/api/speed',{mode:mode})
    .catch(function(e){clog('Speed-Fehler: '+e,'msg-err')});
}

// ── Fan ──
function setFan(){
  var v=parseInt(document.getElementById('d-fan').value);
  document.getElementById('d-fan-val').textContent=v;
  post('/api/fan',{speed:v})
    .then(function(){clog('Lüfter → '+v+'%','msg-ok')})
    .catch(function(e){clog('Lüfter-Fehler: '+e,'msg-err')});
}
function quickFan(v){
  document.getElementById('d-fan').value=v;
  document.getElementById('d-fan-val').textContent=v;
  post('/api/fan',{speed:v})
    .then(function(){clog('Lüfter → '+v+'%','msg-ok')})
    .catch(function(e){clog('Lüfter-Fehler: '+e,'msg-err')});
}

// ── AMS ──
function amsFeed(type){
  var slot=parseInt(document.getElementById('ams-slot-sel').value);
  post('/api/ams/feed',{slot_index:slot,type:type})
    .then(function(){clog((type===1?T.lbl_feed:T.lbl_unload)+' Slot '+(slot+1),'msg-ok')})
    .catch(function(e){clog('AMS-Fehler: '+e,'msg-err')});
}

// ── Camera ──
function camStart(){
  var img=document.getElementById('cam-img');
  var ph=document.getElementById('cam-placeholder');
  var sp=document.getElementById('cam-spinner');
  ph.style.display='none';
  img.style.display='none';
  sp.style.display='block';
  post('/api/camera/start',{}).then(function(){
    img.onerror=function(){
      sp.style.display='none';
      img.style.display='none';
      ph.style.display='flex';
      camOn=false;
      document.getElementById('cam-toggle-btn').textContent=T.btn_cam_start||'▶ Kamera';
      clog((T.log_error||'Fehler:')+' Stream nicht verfügbar','msg-err');
    };
    img.src='/api/camera/stream?t='+Date.now();
    camOn=true;
    document.getElementById('cam-toggle-btn').textContent=T.btn_cam_stop||'◼ Kamera';
    clog((T.log_cam_start||'Kamera gestartet'),'msg-ok');
    // MJPEG liefert kein onload – Spinner nach kurzem Timeout ausblenden
    setTimeout(function(){
      sp.style.display='none';
      img.style.display='block';
    },1200);
  }).catch(function(e){
    sp.style.display='none';
    ph.style.display='flex';
    clog((T.log_error||'Fehler:')+' '+e,'msg-err');
  });
}
function camStop(){
  post('/api/camera/stop',{}).then(function(){
    var img=document.getElementById('cam-img');
    img.src='';
    img.style.display='none';
    document.getElementById('cam-spinner').style.display='none';
    document.getElementById('cam-placeholder').style.display='flex';
    camOn=false;
    document.getElementById('cam-toggle-btn').textContent=T.btn_cam_start||'▶ Kamera';
    clog(T.log_cam_stop||'Kamera gestoppt','msg-ok');
  }).catch(function(e){clog((T.log_error||'Fehler:')+' '+e,'msg-err')});
}
function toggleCam(){if(camOn)camStop();else camStart()}

// ── GCode Store ──
var storeFiles=[];

function loadStore(){
  fetch(_apiUrl('/kx/files')).then(function(r){return r.json()}).then(function(d){
    storeFiles=d.result||[];
    renderStore();
  }).catch(function(e){clog('Store-Fehler: '+e,'msg-err')});
}

function renderStore(){
  var grid=document.getElementById('store-grid');
  var empty=document.getElementById('store-empty');

  // Suche
  var q=(document.getElementById('store-search')||{value:''}).value.toLowerCase().trim();
  // Filter
  var filter=(document.getElementById('store-filter')||{value:'all'}).value;
  // Sortierung
  var sort=(document.getElementById('store-sort')||{value:'date_desc'}).value;

  var files=storeFiles.filter(function(f){
    if(q&&f.filename.toLowerCase().indexOf(q)===-1) return false;
    if(filter==='completed'&&f.last_print_status!=='completed') return false;
    if(filter==='failed'&&(f.last_print_status!=='cancelled'&&f.last_print_status!=='failed')) return false;
    if(filter==='never'&&f.last_print_status) return false;
    return true;
  });

  files.sort(function(a,b){
    if(sort==='name_asc') return a.filename.localeCompare(b.filename);
    if(sort==='duration_asc'){
      var da=a.last_print_duration||a.est_print_time_sec||0;
      var db=b.last_print_duration||b.est_print_time_sec||0;
      return da-db;
    }
    // date_desc (default)
    return (b.uploaded_at||'').localeCompare(a.uploaded_at||'');
  });

  if(!storeFiles.length){
    empty.textContent=T.store_empty;
    grid.innerHTML='';
    empty.style.display='block';
    return;
  }
  if(!files.length){
    empty.textContent=T.store_no_results;
    grid.innerHTML='';
    empty.style.display='block';
    return;
  }
  empty.style.display='none';
  grid.innerHTML=files.map(function(f){
    var thumb=f.thumbnail_b64
      ? '<img src="data:image/png;base64,'+f.thumbnail_b64+'" style="width:100%;height:130px;object-fit:cover;border-radius:6px;display:block;margin-bottom:8px">'
      : '<div style="width:100%;height:130px;background:var(--raised);border-radius:6px;display:flex;align-items:center;justify-content:center;margin-bottom:8px;font-size:32px">🖨</div>';
    var name=f.filename.length>28?f.filename.slice(0,25)+'…':f.filename;
    var date=f.uploaded_at?f.uploaded_at.replace('T',' ').slice(0,16):'';
    var est=f.est_print_time_sec?formatDur(f.est_print_time_sec):'–';
    var statusBadge='';
    var lastInfo='';
    if(f.last_print_status==='completed'){
      statusBadge='<span style="background:#2a7a3b;color:#fff;border-radius:4px;padding:1px 6px;font-size:10px;margin-left:4px">✓</span>';
      if(f.last_print_duration) lastInfo='<div style="font-size:11px;color:var(--ok);margin-bottom:2px">✓ '+formatDur(f.last_print_duration)+'</div>';
    } else if(f.last_print_status==='cancelled'||f.last_print_status==='failed'){
      statusBadge='<span style="background:#a04020;color:#fff;border-radius:4px;padding:1px 6px;font-size:10px;margin-left:4px">✗</span>';
      lastInfo='<div style="font-size:11px;color:var(--err);margin-bottom:2px">✗ '+f.last_print_status+'</div>';
    } else if(!f.last_print_status){
      lastInfo='<div style="font-size:11px;color:var(--txt2);margin-bottom:2px;opacity:.6">'+T.store_never+'</div>';
    }
    return '<div style="background:var(--raised);border:1px solid var(--border);border-radius:8px;padding:10px;display:flex;flex-direction:column">'+
      thumb+
      '<div title="'+f.filename+'" style="font-size:12px;font-weight:600;margin-bottom:4px;color:var(--txt)">'+name+statusBadge+'</div>'+
      lastInfo+
      '<div style="font-size:11px;color:var(--txt2);margin-bottom:2px">⏱ Schätzung: '+est+'</div>'+
      '<div style="font-size:11px;color:var(--txt2);margin-bottom:8px">📅 '+date+'</div>'+
      '<div style="display:flex;gap:6px;margin-top:auto">'+
        '<button onclick="storePrint(\''+f.id+'\',\''+f.filename.replace(/'/g,"\\'")+'\')" '+
          'style="flex:1;font-size:12px;padding:5px;background:var(--accent);color:#fff;border:none;border-radius:6px;cursor:pointer">'+T.store_print+'</button>'+
        '<button onclick="storeDelete(\''+f.id+'\')" '+
          'style="font-size:12px;padding:5px 8px;background:var(--raised);border:1px solid var(--border);border-radius:6px;color:var(--txt2);cursor:pointer">🗑</button>'+
      '</div>'+
    '</div>';
  }).join('');
}

function formatDur(sec){
  var h=Math.floor(sec/3600),m=Math.floor((sec%3600)/60);
  return h?h+'h '+m+'m':m+'m';
}

var _storeFileId=null;
var _storeFilename=null;
var _filamentDialogMode='store'; // 'store' oder 'banner'

var _gcodeFilaments=[];

function storePrint(fileId, filename){
  _storeFileId=fileId;
  _storeFilename=filename;
  _filamentDialogMode='store';
  // GCode-Filamente aus Store-Datei holen (für Vorschau im Dialog)
  var fileObj=storeFiles.find(function(f){return f.id===fileId;});
  try{ _gcodeFilaments=fileObj&&fileObj.gcode_filaments?JSON.parse(fileObj.gcode_filaments):[]; }
  catch(e){ _gcodeFilaments=[]; }
  fetch(_apiUrl('/kx/filament/slots')).then(function(r){return r.json()}).then(function(d){
    openFilamentDialog(d.result||[]);
  }).catch(function(){openFilamentDialog([]);});
}

function startReadyFileWithSlots(){
  _filamentDialogMode='banner';
  _storeFilename=S.file_ready||'';
  fetch(_apiUrl('/kx/filament/slots')).then(function(r){return r.json()}).then(function(d){
    openFilamentDialog(d.result||[]);
  }).catch(function(){openFilamentDialog([]);});
}

var _amsSlots=[];

function openFilamentDialog(slots){
  _amsSlots=slots.filter(function(s){return s.status==='loaded';});
  var dlg=document.getElementById('filament-dialog');
  var title=document.getElementById('fd-title');
  var body=document.getElementById('fd-slots');
  if(title)title.textContent='▶ '+_storeFilename;

  // GCode-Kanäle: bevorzugt aus _gcodeFilaments, sonst aus belegten AMS-Slots ableiten
  var channels=_gcodeFilaments.length?_gcodeFilaments:_amsSlots.map(function(s,i){
    return {slot_index:i,color_hex:s.color_hex,material:s.material};
  });

  if(!_amsSlots.length){
    body.innerHTML='<p style="color:var(--txt2);font-size:13px;text-align:center;padding:16px 0">Keine belegten AMS-Slots.<br>Druck trotzdem starten?</p>';
  } else {
    body.innerHTML=channels.map(function(gc,i){
      // Passende Slots: gleicher Materialtyp
      var compatible=_amsSlots.filter(function(s){return s.material.toUpperCase()===gc.material.toUpperCase();});
      if(!compatible.length) compatible=_amsSlots; // Fallback: alle
      // Standard-Auswahl: Slot mit gleichem Index oder erster kompatibler
      var defaultSlot=compatible.find(function(s){return s.slot_index===gc.slot_index;})||compatible[0];
      var opts=compatible.map(function(s){
        var sel=(s.slot_index===defaultSlot.slot_index)?'selected':'';
        return '<option value="'+s.slot_index+'" data-color="'+s.color_hex+'" data-material="'+s.material+'" '+sel+'>'+
          'Slot '+(s.slot_index+1)+' · '+s.material+'</option>';
      }).join('');
      return '<div style="display:flex;align-items:center;gap:10px;padding:8px;border-radius:6px;background:var(--raised);border:1px solid var(--border)">'+
        '<span style="display:inline-block;width:16px;height:16px;border-radius:50%;background:'+gc.color_hex+';border:1px solid var(--border);flex-shrink:0"></span>'+
        '<span style="font-size:13px;font-weight:600;min-width:70px">Kanal '+(i+1)+'</span>'+
        '<span style="font-size:11px;color:var(--txt2);min-width:32px">'+gc.material+'</span>'+
        '<span style="font-size:18px;color:var(--txt2)">→</span>'+
        '<select data-paint="'+i+'" data-paint-color="'+gc.color_hex+'" style="flex:1;padding:4px 6px;border-radius:6px;border:1px solid var(--border);background:var(--raised);color:var(--txt);font-size:13px">'+
        opts+'</select>'+
      '</div>';
    }).join('');
  }
  if(dlg)dlg.classList.add('open');
}

function closeFilamentDialog(){
  var dlg=document.getElementById('filament-dialog');
  if(dlg)dlg.classList.remove('open');
}

function confirmFilamentPrint(){
  var selects=document.querySelectorAll('#fd-slots select');
  var assignments=[];
  selects.forEach(function(sel){
    var paintIdx=parseInt(sel.dataset.paint);
    var paintColor=sel.dataset.paintColor;
    var opt=sel.options[sel.selectedIndex];
    var amsIdx=parseInt(opt.value);
    var amsSlot=_amsSlots.find(function(s){return s.slot_index===amsIdx;})||{};
    // Farbe als [R,G,B,255]
    function hexToRgba(h){
      var c=h.replace('#','');
      if(c.length===3)c=c[0]+c[0]+c[1]+c[1]+c[2]+c[2];
      return [parseInt(c.slice(0,2),16),parseInt(c.slice(2,4),16),parseInt(c.slice(4,6),16),255];
    }
    assignments.push({
      paint_index:  paintIdx,
      slot_index:   amsIdx,
      material:     opt.dataset.material||'PLA',
      paint_color:  hexToRgba(paintColor||'#ffffff'),
      ams_color:    hexToRgba(amsSlot.color_hex||'#ffffff'),
    });
  });
  closeFilamentDialog();
  if(_filamentDialogMode==='banner'){
    // Banner-Modus: normaler print/start mit Slot-Override
    var btn=document.getElementById('file-ready-btn');
    if(btn){btn.disabled=true;btn.textContent='…';}
    post('/printer/print/start',{filename:S.file_ready,filament_assignments:assignments})
      .then(function(r){return r.json();})
      .then(function(){
        document.getElementById('file-ready-banner').style.display='none';
        if(btn){btn.disabled=false;setText('file-ready-btn',T.file_ready_btn);}
      })
      .catch(function(e){
        clog((T.log_error||'Error:')+' '+e,'msg-err');
        if(btn){btn.disabled=false;setText('file-ready-btn',T.file_ready_btn);}
      });
  } else {
    // Store-Modus: POST /kx/print
    fetch(_apiUrl('/kx/print'),{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({file_id:_storeFileId,filament_assignments:assignments})
    }).then(function(r){return r.json()}).then(function(d){
      if(d.result==='ok'){clog('Druckstart: '+_storeFilename,'msg-ok');showPanel('dashboard');}
      else{clog('Druckfehler: '+(d.error||'?'),'msg-err');}
    }).catch(function(e){clog('Druckfehler: '+e,'msg-err');});
  }
}

function storeDelete(fileId){
  if(!confirm(T.store_delete_confirm)) return;
  fetch(_apiUrl('/kx/files/'+fileId),{method:'DELETE'}).then(function(r){
    if(r.ok){loadStore();}
    else{clog('Löschen fehlgeschlagen','msg-err');}
  });
}

// ── Drucker hinzufügen ──
function openAddPrinterDialog(){
  document.getElementById('apd-ip').value='';
  document.getElementById('apd-name').value='';
  var st=document.getElementById('apd-status');st.textContent='';st.style.color='var(--txt2)';
  document.getElementById('apd-confirm').disabled=false;
  document.getElementById('add-printer-dialog').classList.add('open');
}
function closeAddPrinterDialog(){
  document.getElementById('add-printer-dialog').classList.remove('open');
}
function confirmAddPrinter(){
  var ip=document.getElementById('apd-ip').value.trim();
  var name=document.getElementById('apd-name').value.trim();
  var st=document.getElementById('apd-status'),btn=document.getElementById('apd-confirm');
  if(!ip){st.textContent=T.apd_err_ip;st.style.color='var(--err)';return;}
  st.textContent=T.apd_fetching;st.style.color='var(--txt2)';btn.disabled=true;
  fetch('/kx/printers/add',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({printer_ip:ip,name:name})})
    .then(function(r){return r.json().then(function(j){return {ok:r.ok,j:j};});})
    .then(function(res){
      if(!res.ok){st.textContent=(res.j&&res.j.error)||'Fehler';st.style.color='var(--err)';btn.disabled=false;return;}
      st.textContent=T.apd_success;st.style.color='var(--ok)';
      setTimeout(function(){location.reload();},2500);
    })
    .catch(function(e){st.textContent=''+e;st.style.color='var(--err)';btn.disabled=false;});
}
function removePrinter(id,name){
  if(!confirm(T.printers_remove_confirm.replace('{name}',name)))return;
  fetch('/kx/printers/'+encodeURIComponent(id),{method:'DELETE'})
    .then(function(r){return r.json().then(function(j){return {ok:r.ok,j:j};});})
    .then(function(res){
      if(!res.ok){alert((res.j&&res.j.error)||'Fehler');return;}
      setTimeout(function(){location.href='/printer1';},2000);
    })
    .catch(function(e){alert(''+e);});
}

// ── Drucker-Tab ──
function loadPrinterTab(){
  var grid=document.getElementById('printers-grid');
  if(grid)grid.innerHTML='<div style="color:var(--txt2);font-size:13px;padding:20px">'+T.printers_loading+'</div>';
  // Drucker-Liste von lokaler Instanz holen
  fetch('/kx/printers').then(function(r){return r.json()}).then(function(d){
    var printers=d.result||[];
    if(!printers.length){
      if(grid)grid.innerHTML='<div style="grid-column:1/-1;text-align:center;padding:40px 20px;color:var(--txt2)">'+
        '<div style="font-size:32px;margin-bottom:8px">🖨</div>'+
        '<div style="font-size:14px;margin-bottom:14px">'+T.printers_empty_hint+'</div>'+
        '<button onclick="openAddPrinterDialog()" style="font-size:13px;padding:8px 18px;background:var(--accent);border:none;border-radius:8px;color:#fff;cursor:pointer;font-weight:600">+ '+T.add_printer+'</button>'+
      '</div>';
      return;
    }
    // Status jedes Druckers parallel abrufen
    var fetches=printers.map(function(p){
      var url=(p.bridge_url||'').replace(/\/+$/,'');
      return fetch(url+'/api/state',{signal:AbortSignal.timeout(3000)})
        .then(function(r){return r.json()})
        .then(function(s){return {printer:p,state:s,online:true};})
        .catch(function(){return {printer:p,state:{},online:false};});
    });
    Promise.all(fetches).then(function(results){
      var activeId=_activePrinter?String(_activePrinter.id):null;
      if(grid)grid.innerHTML=results.map(function(res){
        var p=res.printer,s=res.state,online=res.online;
        var isActive=String(p.id)===activeId;
        var url=(p.bridge_url||'').replace(/\/+$/,'');
        var printerNum=p.id;
        var ks=online?(s.kobra_state||'free'):'offline';
        var stateKey='kobra_'+ks;
        var stateLabel=T[stateKey]||ks;
        var stateColor=ks==='free'?'var(--ok)':ks==='printing'?'var(--accent)':ks==='offline'?'var(--txt2)':'var(--warn)';
        var progress=online&&s.progress?Math.round(s.progress*100):null;
        var filename=online&&s.filename?s.filename:'';
        var nt=online&&s.nozzle_temp?s.nozzle_temp.toFixed(1):'–';
        var bt=online&&s.bed_temp?s.bed_temp.toFixed(1):'–';
        var border=isActive?'2px solid var(--accent)':'1px solid var(--border)';
        var nameEsc=String(p.name).replace(/\\/g,'\\\\').replace(/'/g,"\\'");
        return '<div style="background:var(--raised);border:'+border+';border-radius:10px;padding:14px;display:flex;flex-direction:column;gap:8px">'+
          '<div style="display:flex;align-items:center;justify-content:space-between;gap:8px">'+
            '<span style="font-weight:700;font-size:14px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">🖨 '+p.name+'</span>'+
            '<span style="display:flex;align-items:center;gap:8px;flex-shrink:0">'+
              (isActive?'<span style="font-size:11px;color:var(--accent);font-weight:600">'+T.printers_active+'</span>':'')+
              '<button onclick="removePrinter(\''+printerNum+'\',\''+nameEsc+'\')" title="'+T.printers_remove+'" style="background:none;border:none;color:var(--txt2);font-size:16px;cursor:pointer;line-height:1;padding:0">✕</button>'+
            '</span>'+
          '</div>'+
          '<div style="display:flex;align-items:center;gap:6px">'+
            '<span style="width:8px;height:8px;border-radius:50%;background:'+stateColor+';display:inline-block"></span>'+
            '<span style="font-size:13px;color:var(--txt2)">'+stateLabel+'</span>'+
          '</div>'+
          (p.printer_ip?'<div style="font-size:12px;color:var(--txt2)">🌐 '+p.printer_ip+'</div>':'')+
          (filename?'<div style="font-size:12px;color:var(--txt2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis" title="'+filename+'">📄 '+filename+'</div>':'')+
          (progress!==null?'<div style="background:var(--border);border-radius:4px;height:6px;overflow:hidden"><div style="background:var(--accent);height:100%;width:'+progress+'%"></div></div>':'')+
          '<div style="font-size:12px;color:var(--txt2);display:flex;gap:12px">'+
            '<span>🌡 '+nt+'°C</span><span>🛏 '+bt+'°C</span>'+
          '</div>'+
          (!isActive?'<a href="/printer'+printerNum+'" style="display:block;text-align:center;padding:7px;background:var(--accent);color:#fff;border-radius:7px;font-size:13px;font-weight:600;text-decoration:none;margin-top:4px">'+T.printers_switch+'</a>':'<div style="text-align:center;padding:7px;font-size:12px;color:var(--txt2)">'+T.printers_current+'</div>')+
        '</div>';
      }).join('');
    });
  }).catch(function(e){
    if(grid)grid.innerHTML='<div style="color:var(--err);font-size:13px;padding:20px">Fehler: '+e+'</div>';
  });
}
</script>
<!-- Filament-Slot-Dialog -->
<div class="modal-overlay" id="filament-dialog" onclick="if(event.target===this)closeFilamentDialog()">
  <div class="modal-box" style="max-width:380px;width:100%">
    <div class="modal-header" style="margin-bottom:14px">
      <span class="modal-title" id="fd-title" style="font-size:14px;word-break:break-all"></span>
      <button onclick="closeFilamentDialog()" style="background:none;border:none;font-size:18px;cursor:pointer;color:var(--txt2)">✕</button>
    </div>
    <p style="font-size:12px;color:var(--txt2);margin-bottom:10px">GCode-Kanal → AMS-Slot zuweisen:</p>
    <div id="fd-slots" style="display:flex;flex-direction:column;gap:8px;margin-bottom:16px"></div>
    <div style="display:flex;gap:8px;justify-content:flex-end">
      <button onclick="closeFilamentDialog()" style="padding:8px 16px;background:var(--raised);border:1px solid var(--border);border-radius:8px;color:var(--txt);cursor:pointer">Abbrechen</button>
      <button onclick="confirmFilamentPrint()" style="padding:8px 18px;background:var(--accent);color:#fff;border:none;border-radius:8px;cursor:pointer;font-weight:600">▶ Drucken</button>
    </div>
  </div>
</div>
<!-- Drucker-hinzufügen-Dialog -->
<div class="modal-overlay" id="add-printer-dialog" onclick="if(event.target===this)closeAddPrinterDialog()">
  <div class="modal-box" style="max-width:380px;width:100%">
    <div class="modal-header" style="margin-bottom:14px">
      <span class="modal-title" id="apd-title">Drucker hinzufügen</span>
      <button onclick="closeAddPrinterDialog()" style="background:none;border:none;font-size:18px;cursor:pointer;color:var(--txt2)">✕</button>
    </div>
    <label id="apd-lbl-ip" style="display:block;font-size:12px;color:var(--txt2);margin-bottom:4px">Drucker-IP</label>
    <input type="text" id="apd-ip" placeholder="192.168.1.100" style="width:100%;box-sizing:border-box;padding:8px;background:var(--raised);border:1px solid var(--border);border-radius:6px;color:var(--txt);margin-bottom:10px">
    <label id="apd-lbl-name" style="display:block;font-size:12px;color:var(--txt2);margin-bottom:4px">Name (optional)</label>
    <input type="text" id="apd-name" placeholder="z.B. Kobra X Wohnzimmer" style="width:100%;box-sizing:border-box;padding:8px;background:var(--raised);border:1px solid var(--border);border-radius:6px;color:var(--txt);margin-bottom:6px">
    <div id="apd-status" style="font-size:12px;margin:8px 0;min-height:16px;color:var(--txt2)"></div>
    <div style="display:flex;gap:8px;justify-content:flex-end">
      <button onclick="closeAddPrinterDialog()" style="padding:8px 16px;background:var(--raised);border:1px solid var(--border);border-radius:8px;color:var(--txt);cursor:pointer">Abbrechen</button>
      <button id="apd-confirm" onclick="confirmAddPrinter()" style="padding:8px 18px;background:var(--accent);color:#fff;border:none;border-radius:8px;cursor:pointer;font-weight:600">Hinzufügen</button>
    </div>
  </div>
</div>

<footer style="text-align:center;padding:12px;font-size:11px;color:var(--txt2);border-top:1px solid var(--border);margin-top:auto">
  &copy; ViewIT 2026
</footer>
</body>
</html>"""
        version = self._read_version()
        html = html.replace("'__VERSION__'", f"'{version}'")
        return web.Response(text=html, content_type="text/html",
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
        index  = int(body.get("index", 0))
        mat    = str(body.get("type", "PLA")).upper()
        color  = body.get("color", [255, 255, 255])
        if not (isinstance(color, list) and len(color) == 3):
            return web.json_response({"error": "color must be [r,g,b]"}, status=400)
        loop = asyncio.get_event_loop()
        def _send():
            resp = self.client.publish(
                "multiColorBox", "setInfo",
                {"multi_color_box": [{"id": -1, "slots": [{"index": index, "type": mat, "color": color}]}]},
                timeout=5
            )
            log.info(f"setInfo slot={index} type={mat} color={color} → {resp}")
            return resp
        resp = await loop.run_in_executor(None, _send)
        if resp and resp.get("code") == 200:
            # Update cached slot immediately
            for s in self._ams_slots:
                if s.get("index") == index:
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
        # Ausziehen (type=2): wenn kein Slot explizit gewählt, den zuletzt geladenen nehmen
        if feed_type == 2 and self._ams_loaded_slot >= 0:
            slot_index = self._ams_loaded_slot
        loop = asyncio.get_event_loop()
        def _send():
            resp = self.client.publish(
                "multiColorBox", "feedFilament",
                {"multi_color_box": [{"id": -1, "feed_status": {"slot_index": slot_index, "type": feed_type}}]},
                timeout=5
            )
            log.info(f"feedFilament type={feed_type} slot={slot_index} loaded_slot={self._ams_loaded_slot} → {resp}")
        await loop.run_in_executor(None, _send)
        return web.json_response({"result": "ok"})

    async def handle_api_axis(self, request):
        try:
            body = await request.json()
        except Exception:
            body = {}
        action = body.get("action", "move")
        loop = asyncio.get_event_loop()
        if action == "turnOff":
            await loop.run_in_executor(None, lambda: self.client.publish(
                "axis", "turnOff", None, timeout=0
            ))
        else:
            axis      = int(body.get("axis", 4))
            move_type = int(body.get("move_type", 2))
            distance  = float(body.get("distance", 0))
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
            # Idle: standard tempature/set with both values
            n = int(float(nozzle)) if nozzle is not None else int(self._state["nozzle_target"])
            b = int(float(bed))    if bed    is not None else int(self._state["bed_target"])
            await loop.run_in_executor(None, lambda: self.client.publish(
                "tempature", "set",
                {"target_nozzle_temp": n, "target_hotbed_temp": b},
                timeout=0
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
        return web.json_response({"result": "ok"})

    async def handle_api_camera_snapshot(self, request):
        """Einzelner JPEG-Frame aus dem Kamera-Stream – für Obico und andere Snapshot-Clients."""
        url = self._state.get("camera_url", "")
        if not url:
            return web.Response(status=503, text="Keine Kamera-URL bekannt")
        is_rtsp = url.lower().startswith("rtsp://")
        input_args = ["-fflags", "nobuffer", "-flags", "low_delay"]
        if is_rtsp:
            input_args += ["-probesize", "32", "-analyzeduration", "0", "-rtsp_transport", "tcp"]
        else:
            input_args += ["-probesize", "1000000", "-analyzeduration", "1000000"]
        try:
            proc = await asyncio.create_subprocess_exec(
                _find_ffmpeg(), "-loglevel", "quiet",
                *input_args, "-i", url,
                "-frames:v", "1", "-f", "mjpeg", "-q:v", "3",
                "pipe:1",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            jpeg, _ = await asyncio.wait_for(proc.communicate(), timeout=20)
        except asyncio.TimeoutError:
            return web.Response(status=504, text="Snapshot-Timeout")
        except Exception as e:
            return web.Response(status=503, text=str(e))
        if not jpeg:
            return web.Response(status=503, text="Kein Frame empfangen")
        return web.Response(body=jpeg, content_type="image/jpeg",
                            headers={"Cache-Control": "no-cache"})

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
            log.warning("Kamera: ffmpeg nicht gefunden – Kamerastream nicht verfügbar")
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

        return resp

    async def handle_serve_file(self, request):
        """Liefert hochgeladene G-Code-Dateien vom Temp-Verzeichnis (für Drucker-Download)."""
        filename = os.path.basename(request.match_info.get("filename", ""))
        serve_path = os.path.join(self._serve_dir_path, filename)
        if not os.path.isfile(serve_path):
            return web.Response(status=404, text="not found")
        size = os.path.getsize(serve_path)
        log.info(f"Drucker lädt Datei ab: {filename} ({size} bytes)")
        return web.FileResponse(serve_path, headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        })

    async def handle_api_state(self, request):
        s = self._state
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
            "filename":         s["filename"],
            "slicer_time":      s["slicer_time"],
            "camera_url":       s["camera_url"],
            "fan_speed":        s["fan_speed"],
            "print_speed_mode": s["print_speed_mode"],
            "light_on":         s["light_on"],
            "light_brightness": s["light_brightness"],
            "ams_slots":        self._ams_slots,
            "ams_loaded_slot":  self._ams_loaded_slot,
            "thumbnail":        self._thumbnail_b64,
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

        return web.json_response(
            {"error": {"code": 404, "message": f"Namespace '{namespace}' not found"}},
            status=404
        )

    async def handle_database_list(self, request):
        """OrcaSlicer prüft welche Namespaces vorhanden sind um MMU-Typ zu erkennen."""
        return web.json_response({"result": {"namespaces": ["lane_data"]}})

    def _get_ams_slots_fresh(self):
        """Frische Slot-Daten per getInfo holen, Fallback auf gecachte."""
        resp = self.client.publish("multiColorBox", "getInfo", None, timeout=5)
        if resp and resp.get("data"):
            boxes = resp["data"].get("multi_color_box") or []
            if boxes:
                slots = boxes[0].get("slots") or []
                if slots:
                    self._ams_slots = slots
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
        for section in ("connection", "print", "bridge"):
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
        if not cfg.has_option("bridge", "poll_interval"):
            cfg.set("bridge", "poll_interval", "3")
        printer_name = str(data.get("printer_name", "")).strip()
        if printer_name:
            cfg.set("bridge", "printer_name", printer_name)
        elif cfg.has_option("bridge", "printer_name"):
            cfg.remove_option("bridge", "printer_name")

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
        log.info(f"Drucker '{name or creds['model']}' als {sec} hinzugefügt (Port {new_port})")
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
                   "BRIDGE_PRINTER_NAME"):
            os.environ.pop(_k, None)

        in_docker = os.path.exists("/.dockerenv") or os.environ.get("KX_IN_DOCKER")
        if in_docker:
            # Docker/systemd: Prozess beenden reicht – der Supervisor startet neu (frische environ)
            log.info("Container-Umgebung erkannt – beende Prozess für Supervisor-Restart")
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
        for base in (pathlib.Path(_BASE), pathlib.Path(_BASE).parent):
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
        lines = [f"[{e['ts']}] {e['lvl']:<5} {e['name']}: {e['msg']}" for e in _log_buffer]
        text = "\n".join(lines)
        return web.Response(
            body=text.encode("utf-8"),
            content_type="text/plain",
            headers={"Content-Disposition": 'attachment; filename="kx-bridge.log"'},
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

    async def handle_api_update_apply(self, request):
        data = await request.json()
        download_url = data.get("download_url", "")
        new_tag      = data.get("tag", "")
        if not download_url:
            return web.json_response({"error": "download_url fehlt"}, status=400)
        script_path = pathlib.Path(sys.executable if getattr(sys, "frozen", False) else __file__).resolve()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(download_url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status != 200:
                        return web.json_response({"error": f"Download HTTP {resp.status}"}, status=502)
                    content = await resp.read()
            # Atomisch ersetzen
            tmp = script_path.with_suffix(".py.new")
            tmp.write_bytes(content)
            os.replace(tmp, script_path)
            if new_tag:
                self._write_version(new_tag.lstrip("v"))
            log.info(f"Update auf {new_tag} installiert, starte neu …")
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
            else:
                log.debug(f"Unbekannte RPC-Methode: {method}")
                result = {}
        except Exception as e:
            log.error(f"RPC-Fehler für {method}: {e}")
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
                    boxes = (box.get("data") or {}).get("multi_color_box") or []
                    slots = boxes[0].get("slots") or [] if boxes else []
                    if slots:
                        self._ams_slots = slots
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
    r.add_post("/server/files/upload",       bridge.handle_file_upload)
    r.add_post("/printer/print/start",       bridge.handle_print_start)
    r.add_post("/printer/print/pause",       bridge.handle_print_pause)
    r.add_post("/printer/print/resume",      bridge.handle_print_resume)
    r.add_post("/printer/print/cancel",      bridge.handle_print_cancel)

    # OctoPrint compatibility (OrcaSlicer probes this + uploads here)
    r.add_get("/api/version",                bridge.handle_octoprint_version)
    r.add_post("/api/files/local",           bridge.handle_file_upload)
    r.add_post("/api/files/{path:.*}",       bridge.handle_file_upload)

    # Moonraker database (OrcaSlicer AMS-Sync)
    r.add_get("/server/database/item",       bridge.handle_moonraker_database)
    r.add_get("/server/database/list",       bridge.handle_database_list)

    # New API endpoints
    r.add_post("/api/light",               bridge.handle_api_light)
    r.add_post("/api/fan",                 bridge.handle_api_fan)
    r.add_post("/api/connect",             bridge.handle_api_connect)
    r.add_post("/api/disconnect",          bridge.handle_api_disconnect)
    r.add_post("/api/speed",               bridge.handle_api_speed)
    r.add_post("/api/ams/feed",            bridge.handle_api_ams_feed)
    r.add_post("/api/ams/set_slot",        bridge.handle_api_ams_set_slot)
    r.add_post("/api/axis",                bridge.handle_api_axis)
    r.add_post("/api/temperature",         bridge.handle_api_temperature)
    r.add_get("/api/camera",               bridge.handle_api_camera)
    r.add_get("/api/camera/stream",        bridge.handle_camera_stream)
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
    r.add_get("/kx/filament/slots",        bridge.handle_kx_filament_slots)
    r.add_get("/kx/history",               bridge.handle_kx_history)
    r.add_route("OPTIONS", "/kx/{path:.*}", bridge.handle_kx_options)

    # Root + Printer-Routen (Single-Page, JS liest Pathname)
    r.add_get("/",                           bridge.handle_index)
    r.add_get("/printer{num:\d+}",          bridge.handle_index)
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
        log.info(f"[Drucker {pid}] Bridge läuft auf http://{args.host}:{per_args.port}")

    import socket as _socket
    try:
        with _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM) as _s:
            _s.connect(("8.8.8.8", 80))
            _local_ip = _s.getsockname()[0]
    except Exception:
        _local_ip = args.host
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

    parser.add_argument("--host",            default="0.0.0.0",
                        help="Bind-Adresse für den Bridge-Server")
    parser.add_argument("--port",        type=int, default=7125,
                        help="HTTP/WS-Port (Moonraker-Standard: 7125)")
    parser.add_argument("--data-dir",    default=_default_data_dir(),
                        help="Persistenz-Verzeichnis für GCode-Store und DB")
    args = parser.parse_args()
    if args.printer_ip and ":" in args.printer_ip:
        args.printer_ip = args.printer_ip.split(":")[0]

    # Windows braucht ProactorEventLoop für asyncio.create_subprocess_exec
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(run_bridge(args))


if __name__ == "__main__":
    main()
