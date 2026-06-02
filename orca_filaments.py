"""OrcaSlicer Filament-Profil Parser.

Geteilt zwischen dem Generator (tools/gen_orca_filament_list.py) und dem
Custom-Profile-Import-Endpoint (bridge/kobrax_moonraker_bridge.py).

Liest Orca-Filament-JSON-Dateien (System- oder User-Profile) und gibt
sie als normalisierte Liste mit (id, name, vendor, type, color) zurück.
"""
from __future__ import annotations

import json
import re


def first_str(value, default: str = "") -> str:
    """Orca-Profile speichern manche Felder als ['wert']. Liefert erstes
    Element als String."""
    if isinstance(value, list):
        return str(value[0]) if value else default
    if isinstance(value, str):
        return value
    return default


def clean_name(raw: str) -> str:
    """Strippt printer-/varianten-spezifische Suffixe:
      'PolyTerra PLA @base'                       → 'PolyTerra PLA'
      'Anycubic PLA @Anycubic Kobra X 0.4 nozzle' → 'Anycubic PLA'
      'Anker Generic PLA 0.4 nozzle'              → 'Anker Generic PLA'
    """
    name = re.sub(r"\s*@.*$", "", raw).strip()
    name = re.sub(r"\s+\d+(\.\d+)?\s*nozzle\s*$", "", name, flags=re.IGNORECASE).strip()
    return name or raw


def parse_profile(data: dict, by_name: dict | None = None,
                  path_vendor: str | None = None,
                  source_path: str = "",
                  system_index: list | None = None) -> dict | None:
    """Parsed ein einzelnes Orca-Filament-Profil zum Bridge-Schema.

    `by_name` ist optional ein {name: [profile, …]}-Index für Inherits-Resolve
    aus dem rohen Source-Tree (Generator). Bei Single-File-Import (User-Datei
    aus OrcaSlicer-User-Dir) reichen wir stattdessen `system_index` rein —
    die fertige System-Profile-Liste aus orca_filaments.json. Damit können
    wir filament_id/vendor/type/color über die `inherits`-Kette aus dem
    System-Parent ableiten, auch wenn das User-Profil diese Felder nicht
    selbst setzt (typisch: User-Override-Profile haben nur Tweaks).

    Liefert {id, name, vendor, type, color} oder None wenn das Profil
    keine filament_id hat (z.B. abstrakte @base-Templates).
    """
    if not isinstance(data, dict):
        return None
    # User-Profile aus dem OrcaSlicer-User-Dir setzen oft KEIN "type"-Feld —
    # das kommt vom System-Parent. Wir akzeptieren das wenn entweder "type"
    # explizit "filament" ist ODER ein "inherits" auf ein anderes Profil zeigt.
    if data.get("type") not in (None, "filament") and not data.get("inherits"):
        return None
    if data.get("type") == "filament" and data.get("inherits") is None and not data.get("filament_id"):
        # type=filament aber kein parent + keine ID → wertloses Stub
        return None
    inst = data.get("instantiation", "true")
    if isinstance(inst, str) and inst.lower() == "false":
        return None

    # Build system-name-Index für den fallback-Lookup wenn system_index gesetzt.
    sys_by_name: dict[str, dict] = {}
    if system_index:
        for p in system_index:
            if isinstance(p, dict) and p.get("name"):
                sys_by_name[p["name"]] = p

    def _resolve(key: str, depth: int = 5):
        cur_list = [data]
        for _ in range(depth):
            for cur in cur_list:
                v = cur.get(key)
                if v not in ("", [], None, [""]) and v is not None:
                    return v
            # Erst raw-Inherits via by_name (Generator-Pfad)
            if by_name:
                next_list: list[dict] = []
                for cur in cur_list:
                    parent_name = cur.get("inherits")
                    if parent_name and parent_name in by_name:
                        next_list.extend(by_name[parent_name])
                if next_list:
                    cur_list = next_list
                    continue
            break
        return None

    def _resolve_via_system_index(key: str):
        """Inherits-Kette über system_index (clean_name-Match)."""
        parent_raw = data.get("inherits")
        if not parent_raw or not sys_by_name:
            return None
        parent_clean = clean_name(parent_raw)
        sys_p = sys_by_name.get(parent_clean)
        if not sys_p:
            return None
        # System-JSON benutzt schon das normalisierte Schema
        mapping = {
            "filament_id":              "id",
            "filament_vendor":          "vendor",
            "filament_type":            "type",
            "default_filament_colour":  "color",
        }
        return sys_p.get(mapping.get(key, key))

    def _resolve_full(key: str):
        v = _resolve(key)
        if v not in ("", [], None, [""]) and v is not None:
            return v
        return _resolve_via_system_index(key)

    fid = _resolve_full("filament_id")
    if not fid or not isinstance(fid, str):
        return None

    name_raw = data.get("name", fid)
    name = clean_name(name_raw)
    vendor = first_str(_resolve_full("filament_vendor")) or (path_vendor or "Generic")
    ftype  = first_str(_resolve_full("filament_type"), "")
    color  = first_str(_resolve_full("default_filament_colour"), "")

    return {
        "id":     fid,
        "name":   name,
        "vendor": vendor,
        "type":   ftype,
        "color":  color,
    }


def parse_profile_bytes(blob: bytes, source_name: str = "",
                        system_index: list | None = None) -> dict | None:
    """Liest ein einzelnes Profil aus JSON-Bytes. Für File-Upload-Pfad.
    `system_index` ist optional die fertige Liste aus orca_filaments.json —
    wird für die Inherits-Resolve von User-Profilen genutzt die das volle
    Schema vom System-Parent erben."""
    try:
        data = json.loads(blob.decode("utf-8", errors="replace"))
    except Exception:
        return None
    return parse_profile(data, source_path=source_name, system_index=system_index)
