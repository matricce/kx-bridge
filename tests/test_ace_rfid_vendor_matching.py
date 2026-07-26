"""Auto-matching for custom ACE-RFID filament tags (Issue #101).

Anycubic's ACE RFID system concatenates vendor + material + a truncated
serial into one `type` string for custom (third-party) tags, e.g.
"GEEETECH PLA Bas" (vendor "Geeetech", material "PLA", serial "Bas" for
"Basic"). Previously the bridge treated this whole string as an unknown
material and fell back to a neutral "Generic <type>" profile, even though
the user had already imported a matching OrcaSlicer profile via the ZIP
import feature (Issue #41) - requiring a manual per-slot reassignment every
time that spool was loaded.

_parse_combined_rfid_type() + _match_profile_by_vendor_family() resolve this
automatically against the merged system+user filament library.
"""
import argparse
import tempfile
from unittest.mock import MagicMock

from kobrax_moonraker_bridge import KobraXBridge

USER_PROFILES = [
    {"id": "OGFL99", "name": "Generic PLA", "vendor": "Generic", "type": "PLA", "color": ""},
    {"id": "GTPLA01", "name": "Geeetech PLA Basic", "vendor": "Geeetech", "type": "PLA", "color": "", "is_user": True},
]


def _bridge(profiles=USER_PROFILES):
    c = MagicMock(); c.callbacks = {}; c.connected = False
    args = argparse.Namespace(
        printer_ip="", mqtt_port=9883, username="", password="",
        mode_id="20030", device_id="", host="127.0.0.1", port=7125,
        data_dir=tempfile.mkdtemp(prefix="kxrfid-"),
    )
    b = KobraXBridge(c, args=args)
    b._orca_filaments_cache = profiles
    return b


def test_combined_rfid_type_parses_known_vendor_and_family():
    b = _bridge()
    vendor, family = b._parse_combined_rfid_type("GEEETECH PLA Bas")
    assert vendor == "Geeetech"
    assert family == "PLA"


def test_plain_type_string_is_unaffected():
    """Regression guard: a normal type="PLA" report (no vendor prefix) must
    not be mistaken for a combined RFID string."""
    b = _bridge()
    vendor, family = b._parse_combined_rfid_type("PLA")
    assert vendor == ""
    assert family == ""


def test_unknown_vendor_prefix_returns_no_match():
    b = _bridge()
    vendor, family = b._parse_combined_rfid_type("TOTALLYUNKNOWNBRAND PLA Bas")
    assert vendor == ""
    assert family == ""


def test_match_profile_by_vendor_family_finds_imported_profile():
    b = _bridge()
    profile = b._match_profile_by_vendor_family("Geeetech", "PLA")
    assert profile.get("name") == "Geeetech PLA Basic"


def test_match_profile_by_vendor_family_no_match_returns_empty():
    b = _bridge()
    profile = b._match_profile_by_vendor_family("Geeetech", "PETG")
    assert profile == {}


def test_match_profile_by_vendor_family_ambiguous_picks_first_without_crashing():
    profiles = USER_PROFILES + [
        {"id": "GTPLA02", "name": "Geeetech PLA Silk", "vendor": "Geeetech", "type": "PLA SILK", "color": "", "is_user": True},
    ]
    b = _bridge(profiles)
    profile = b._match_profile_by_vendor_family("Geeetech", "PLA")
    assert profile.get("name") in ("Geeetech PLA Basic", "Geeetech PLA Silk")


def test_build_lane_data_auto_resolves_combined_rfid_slot():
    """End-to-end: a slot reporting the combined RFID string should surface
    the imported Geeetech profile in lane_data instead of the Generic
    fallback."""
    b = _bridge()
    b._filament_profiles = {}  # no manual per-slot override - isolate the auto-match path
    b._filament_mode = "ace_hub"
    b._ams_slots = [
        {"global_index": 0, "box_id": 0, "status": 5, "type": "GEEETECH PLA Bas", "color": [238, 190, 152]},
    ]
    lane = b._build_lane_data()
    tray = lane["ams"][0]["tray"][0]
    assert tray["vendor_name"] == "Geeetech"
    assert tray["name"] == "Geeetech PLA Basic"


def test_build_lane_data_plain_type_still_uses_generic_fallback():
    """Regression guard: everyday type="PLA" slots must keep using the
    existing Generic-library fallback, unaffected by the new matching path."""
    b = _bridge()
    b._filament_profiles = {}  # no manual per-slot override - isolate the fallback path
    b._filament_mode = "ace_hub"
    b._ams_slots = [
        {"global_index": 0, "box_id": 0, "status": 5, "type": "PLA", "color": [255, 255, 255]},
    ]
    lane = b._build_lane_data()
    tray = lane["ams"][0]["tray"][0]
    assert tray["name"] == "Generic PLA"
    assert tray["vendor_name"] == "Generic"
