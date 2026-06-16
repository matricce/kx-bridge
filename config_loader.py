"""
config_loader.py – lädt Verbindungsparameter aus config/config.ini (primär)
oder .env (Fallback / Migration).
Umgebungsvariablen haben immer Vorrang.
"""
import os
import sys
import pathlib
import configparser

_BASE = pathlib.Path(sys.executable).parent if getattr(sys, "frozen", False) else pathlib.Path(__file__).parent

CONFIG_SECTION_CONNECTION = "connection"
CONFIG_SECTION_PRINT      = "print"
CONFIG_SECTION_BRIDGE     = "bridge"


def _find_config_file() -> pathlib.Path | None:
    for base in (_BASE, _BASE.parent):
        p = base / "config" / "config.ini"
        if p.is_file():
            return p
    return None


def _find_env_file() -> pathlib.Path | None:
    for base in (_BASE, _BASE.parent):
        p = base / ".env"
        if p.is_file():
            return p
    return None


def _load_env_file(path: pathlib.Path):
    """Lädt .env-Datei als Fallback – setzt nur Keys die noch nicht in os.environ sind."""
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip()
            if key and key not in os.environ:
                os.environ[key] = val


def _load_config_file(path: pathlib.Path):
    """Lädt config.ini und setzt Keys in os.environ (nur wenn nicht bereits gesetzt)."""
    cfg = configparser.ConfigParser()
    cfg.read(path, encoding="utf-8")

    mapping = {
        "PRINTER_IP":       (CONFIG_SECTION_CONNECTION, "printer_ip"),
        "MQTT_PORT":        (CONFIG_SECTION_CONNECTION, "mqtt_port"),
        "MQTT_USERNAME":    (CONFIG_SECTION_CONNECTION, "username"),
        "MQTT_PASSWORD":    (CONFIG_SECTION_CONNECTION, "password"),
        "MODE_ID":          (CONFIG_SECTION_CONNECTION, "mode_id"),
        "DEVICE_ID":        (CONFIG_SECTION_CONNECTION, "device_id"),
        "DEFAULT_AMS_SLOT":     (CONFIG_SECTION_PRINT,   "default_ams_slot"),
        "AUTO_LEVELING":        (CONFIG_SECTION_PRINT,   "auto_leveling"),
        "CAMERA_ON_PRINT":      (CONFIG_SECTION_PRINT,   "camera_on_print"),
        "WEB_UPLOAD_WARNING":   (CONFIG_SECTION_PRINT,   "web_upload_warning"),
        "PRINT_START_DIALOG":   (CONFIG_SECTION_PRINT,   "print_start_dialog"),
        "BRIDGE_PRINTER_NAME":  (CONFIG_SECTION_BRIDGE,  "printer_name"),
    }
    for env_key, (section, option) in mapping.items():
        if env_key not in os.environ:
            try:
                val = cfg.get(section, option)
                if val:
                    os.environ[env_key] = val
            except (configparser.NoSectionError, configparser.NoOptionError):
                pass


    # Backward compatibility: old key FILE_READY_DIALOG → PRINT_START_DIALOG
    if "PRINT_START_DIALOG" not in os.environ:
        try:
            legacy = cfg.get(CONFIG_SECTION_PRINT, "file_ready_dialog")
            if legacy:
                os.environ["PRINT_START_DIALOG"] = legacy
        except (configparser.NoSectionError, configparser.NoOptionError):
            pass
    if "PRINT_START_DIALOG" not in os.environ and "FILE_READY_DIALOG" in os.environ:
        os.environ["PRINT_START_DIALOG"] = os.environ["FILE_READY_DIALOG"]


def migrate_env_to_config(env_path: pathlib.Path, config_path: pathlib.Path):
    """Einmalige Migration: .env → config.ini anlegen."""
    env_vals: dict[str, str] = {}
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            env_vals[k.strip()] = v.strip()

    config_path.parent.mkdir(parents=True, exist_ok=True)
    cfg = configparser.ConfigParser()
    cfg[CONFIG_SECTION_CONNECTION] = {
        "printer_ip": env_vals.get("PRINTER_IP", ""),
        "mqtt_port":  env_vals.get("MQTT_PORT",  "9883"),
        "username":   env_vals.get("MQTT_USERNAME", ""),
        "password":   env_vals.get("MQTT_PASSWORD", ""),
        "mode_id":    env_vals.get("MODE_ID",    ""),
        "device_id":  env_vals.get("DEVICE_ID",  ""),
    }
    cfg[CONFIG_SECTION_PRINT] = {
        "default_ams_slot": env_vals.get("DEFAULT_AMS_SLOT", "auto"),
        "auto_leveling":    env_vals.get("AUTO_LEVELING",    "1"),
        "camera_on_print":  env_vals.get("CAMERA_ON_PRINT",  "0"),
        "web_upload_warning": env_vals.get("WEB_UPLOAD_WARNING", "1"),
    }
    cfg[CONFIG_SECTION_BRIDGE] = {
        "poll_interval": "3",
    }
    with open(config_path, "w", encoding="utf-8") as f:
        f.write("# KX-Bridge Konfigurationsdatei\n")
        f.write("# Automatisch migriert aus .env\n\n")
        cfg.write(f)


def find_config_path() -> pathlib.Path:
    """Gibt den Pfad zur config.ini zurück (auch wenn sie noch nicht existiert)."""
    for base in (_BASE, _BASE.parent):
        config_dir = base / "config"
        if config_dir.is_dir():
            return config_dir / "config.ini"
    return _BASE / "config" / "config.ini"


# ─── Laden ───────────────────────────────────────────────────────────────────

_config_path = _find_config_file()
_env_path    = _find_env_file()

if _config_path:
    _load_config_file(_config_path)
elif _env_path:
    # Kein config.ini vorhanden → aus .env migrieren
    _target = find_config_path()
    migrate_env_to_config(_env_path, _target)
    _load_config_file(_target)
    _config_path = _target


def list_printers() -> list[dict]:
    """Liest alle [printer_N]-Sektionen aus config.ini.

    Jede Sektion kann folgende Keys haben:
      name, printer_ip, mqtt_port, username, password, mode_id, device_id,
      bridge_url, default_ams_slot, auto_leveling

    Gibt eine leere Liste zurück wenn keine [printer_N]-Sektionen vorhanden sind
    (Single-Printer-Betrieb via [connection]).
    """
    path = _find_config_file()
    if not path:
        return []
    cfg = configparser.ConfigParser()
    cfg.read(path, encoding="utf-8")
    printers: list[dict] = []
    idx = 1
    while True:
        section = f"printer_{idx}"
        if not cfg.has_section(section):
            break
        p = dict(cfg[section])
        p.setdefault("id", str(idx))
        if "mqtt_port" in p:
            try:
                p["mqtt_port"] = int(p["mqtt_port"])
            except ValueError:
                p["mqtt_port"] = 9883
        printers.append(p)
        idx += 1
    return printers


def list_filament_profiles() -> dict[int, dict]:
    """Liest die [filament_profiles]-Sektion aus config.ini.

    Format pro AMS-Slot — primärer Selector ist (vendor, name), die `id` wird
    aus der orca_filaments.json beim Speichern nachgeschlagen und mitgeführt
    (als Hint für OrcaSlicer; das Orca-Datenmodell hat ~136 Profile mit
    derselben filament_id wie 'OGFL99', d.h. die ID ist nicht eindeutig):

      [filament_profiles]
      slot_0_vendor = Polymaker
      slot_0_name   = PolyTerra PLA
      slot_0_id     = OGFL01

    Gibt einen Dict {slot_index: {"id": ..., "vendor": ..., "name": ...}}
    zurück. Leere/fehlende Slots werden NICHT aufgenommen — das Default-Mapping
    (per filament_type) in der Bridge bleibt dann aktiv.

    Backwards-Kompat: alte Configs mit nur (vendor, id) bleiben lesbar; `name`
    fehlt dann und der Aufrufer kann optional aus der orca_filaments.json
    rekonstruieren.
    """
    path = _find_config_file()
    if not path:
        return {}
    cfg = configparser.ConfigParser()
    cfg.read(path, encoding="utf-8")
    if not cfg.has_section("filament_profiles"):
        return {}
    result: dict[int, dict] = {}
    for key, value in cfg.items("filament_profiles"):
        # Erwartet: slot_<idx>_id oder slot_<idx>_vendor oder slot_<idx>_name
        if not key.startswith("slot_"):
            continue
        parts = key.split("_", 2)
        if len(parts) < 3:
            continue
        try:
            slot_idx = int(parts[1])
        except ValueError:
            continue
        field = parts[2]
        if field not in ("id", "vendor", "name"):
            continue
        if not value.strip():
            continue
        result.setdefault(slot_idx, {})[field] = value.strip()
    return result


def save_filament_profiles(profiles: dict[int, dict]) -> bool:
    """Schreibt die übergebenen Slot-Profile in die [filament_profiles]-
    Sektion der config.ini. Existierende Einträge werden komplett ersetzt.

    profiles: {slot_index: {"id": "OGFL01", "vendor": "Polymaker", "name": "PolyTerra PLA"}}
    Mindestens vendor+name müssen gesetzt sein; id ist optional (Hint).
    """
    path = _find_config_file()
    if not path:
        return False
    cfg = configparser.ConfigParser()
    cfg.read(path, encoding="utf-8")
    # visible_vendors (Issue #41) ist kein Slot-Mapping — beim Ersetzen der
    # Sektion erhalten, sonst geht der Vendor-Filter beim Slot-Save verloren.
    preserved_vendors = None
    if cfg.has_option("filament_profiles", "visible_vendors"):
        preserved_vendors = cfg.get("filament_profiles", "visible_vendors")
    if cfg.has_section("filament_profiles"):
        cfg.remove_section("filament_profiles")
    if profiles or preserved_vendors:
        cfg["filament_profiles"] = {}
        if preserved_vendors:
            cfg["filament_profiles"]["visible_vendors"] = preserved_vendors
        for slot_idx in sorted(profiles.keys()):
            entry = profiles[slot_idx] or {}
            if entry.get("vendor"):
                cfg["filament_profiles"][f"slot_{slot_idx}_vendor"] = entry["vendor"]
            if entry.get("name"):
                cfg["filament_profiles"][f"slot_{slot_idx}_name"] = entry["name"]
            if entry.get("id"):
                cfg["filament_profiles"][f"slot_{slot_idx}_id"] = entry["id"]
    with open(path, "w", encoding="utf-8") as f:
        cfg.write(f)
    return True


def list_visible_vendors() -> list[str]:
    """Liest [filament_profiles] visible_vendors (komma-separiert) aus config.ini.

    Vendor-Sichtbarkeitsfilter für das Slot-Profil-Dropdown (Issue #41 Option A).
    Leere Liste = keine Einschränkung (rückwärtskompatibel: alle Vendoren).
    """
    path = _find_config_file()
    if not path:
        return []
    cfg = configparser.ConfigParser()
    cfg.read(path, encoding="utf-8")
    if not cfg.has_option("filament_profiles", "visible_vendors"):
        return []
    raw = cfg.get("filament_profiles", "visible_vendors")
    return [v.strip() for v in raw.split(",") if v.strip()]


def save_visible_vendors(vendors: list[str]) -> bool:
    """Schreibt visible_vendors in [filament_profiles], ohne die Slot-Mappings
    (slot_N_*) zu verlieren. Leere Liste entfernt den Key wieder."""
    path = _find_config_file()
    if not path:
        return False
    cfg = configparser.ConfigParser()
    cfg.read(path, encoding="utf-8")
    if not cfg.has_section("filament_profiles"):
        cfg.add_section("filament_profiles")
    clean = [v.strip() for v in (vendors or []) if v and v.strip()]
    if clean:
        cfg["filament_profiles"]["visible_vendors"] = ", ".join(clean)
    elif cfg.has_option("filament_profiles", "visible_vendors"):
        cfg.remove_option("filament_profiles", "visible_vendors")
    with open(path, "w", encoding="utf-8") as f:
        cfg.write(f)
    return True


def get(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


# Häufig verwendete Shortcuts
PRINTER_IP       = get("PRINTER_IP",       "")
MQTT_PORT        = int(get("MQTT_PORT",    "9883"))
USERNAME         = get("MQTT_USERNAME",    "")
PASSWORD         = get("MQTT_PASSWORD",    "")
MODE_ID          = get("MODE_ID",          "")
DEVICE_ID        = get("DEVICE_ID",        "")
DEFAULT_AMS_SLOT = get("DEFAULT_AMS_SLOT", "auto")
AUTO_LEVELING    = int(get("AUTO_LEVELING","1"))
CAMERA_ON_PRINT  = int(get("CAMERA_ON_PRINT","0"))
WEB_UPLOAD_WARNING = int(get("WEB_UPLOAD_WARNING", "1"))
PRINT_START_DIALOG = int(get("PRINT_START_DIALOG", get("FILE_READY_DIALOG", "1")))
