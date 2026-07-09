"""Stale slot-profile guard: suppress a saved per-slot filament profile when the
AMS now reports a *different material family* than the profile was assigned for.

Real-world bug (KX1): slot 1 held a PETG spool and got the profile
"KINGROON PETG Basic". The user swapped in yellow PLA. The AMS updated the
colour (live) but the saved profile stuck on PETG, so the panel + the slicer
hint kept showing/using PETG. Restarting did not help — the override lives in
config.ini.

Fix = non-destructive suppression (Option A): resolve the effective profile as
"the saved override only if its material *family* matches the current AMS
material; otherwise none (fall back to the generic default)". The override is
never deleted, so putting the original material back reactivates it.

Comparison must be by *family*, never strict string equality — PLA / PLA+ /
PLA SILK / PLA MATTE are the same family and must NOT invalidate each other
(regression guard for the earlier over-strict material compare).
"""
import argparse
import json
import tempfile
from unittest.mock import MagicMock

# conftest.py (same dir) already put bridge/ on sys.path and mocked env_loader.
from kobrax_moonraker_bridge import KobraXBridge

# Minimal in-memory stand-in for orca_filaments.json (id, name, vendor, type).
LIBRARY = [
    {"vendor": "KINGROON", "name": "KINGROON PETG Basic",      "type": "PETG", "id": "PB01"},
    {"vendor": "KINGROON", "name": "KINGROON PLA Basic",       "type": "PLA",  "id": "PL01"},
    {"vendor": "XTZL3D",   "name": "XTZL3D Speedy Silk PLA+",  "type": "PLA",  "id": "PS01"},
]

PETG_PROFILE = {"vendor": "KINGROON", "name": "KINGROON PETG Basic", "id": "PB01"}
SILK_PROFILE = {"vendor": "XTZL3D",   "name": "XTZL3D Speedy Silk PLA+", "id": "PS01"}
UNKNOWN_PROFILE = {"vendor": "Foo", "name": "Foo Bar Filament", "id": "X99"}


def _bridge():
    c = MagicMock()
    c.callbacks = {}
    c.connected = False
    args = argparse.Namespace(
        printer_ip="", mqtt_port=9883, username="", password="",
        mode_id="20030", device_id="", host="127.0.0.1", port=7125,
        data_dir=tempfile.mkdtemp(prefix="kxguard-"),
    )
    b = KobraXBridge(c, args=args)
    b._orca_filaments_cache = LIBRARY  # _load_orca_filaments() returns this as-is
    return b


# ── _material_family ──────────────────────────────────────────────────────────

def test_material_family_collapses_pla_variants():
    fam = KobraXBridge._material_family
    assert fam("PLA") == "PLA"
    assert fam("PLA+") == "PLA"
    assert fam("PLA SILK") == "PLA"
    assert fam("PLA MATTE") == "PLA"
    assert fam("Silk PLA") == "PLA"  # alias-normalised before family reduction


def test_material_family_collapses_petg_variants():
    fam = KobraXBridge._material_family
    assert fam("PETG") == "PETG"
    assert fam("PETG+") == "PETG"


def test_material_family_distinguishes_pla_from_petg():
    fam = KobraXBridge._material_family
    assert fam("PLA") != fam("PETG")
    assert fam("PLA SILK") != fam("PETG")


def test_material_family_empty_for_empty_input():
    assert KobraXBridge._material_family("") == ""
    assert KobraXBridge._material_family(None) == ""


# ── _effective_slot_profile ───────────────────────────────────────────────────

def test_suppressed_when_family_changes_petg_profile_pla_loaded():
    """The exact KX1 bug: PETG profile, AMS now reports PLA → suppress."""
    b = _bridge()
    b._filament_profiles = {0: dict(PETG_PROFILE)}
    assert b._effective_slot_profile(0, "PLA") == {}


def test_kept_when_family_matches_petg_profile_petg_loaded():
    b = _bridge()
    b._filament_profiles = {0: dict(PETG_PROFILE)}
    assert b._effective_slot_profile(0, "PETG") == PETG_PROFILE


def test_kept_for_pla_variant_no_false_positive():
    """PLA+ profile with a PLA SILK spool loaded is the same family → keep."""
    b = _bridge()
    b._filament_profiles = {1: dict(SILK_PROFILE)}
    assert b._effective_slot_profile(1, "PLA SILK") == SILK_PROFILE


def test_kept_when_profile_material_unknown_failsafe():
    """If the profile is not in the library we cannot know its family → never
    suppress on uncertainty (fail-safe keeps the user's choice)."""
    b = _bridge()
    b._filament_profiles = {2: dict(UNKNOWN_PROFILE)}
    assert b._effective_slot_profile(2, "PLA") == UNKNOWN_PROFILE


def test_empty_when_no_override():
    b = _bridge()
    b._filament_profiles = {}
    assert b._effective_slot_profile(3, "PLA") == {}


# ── Integration: display endpoint (the visible panel) ─────────────────────────

async def test_display_endpoint_suppresses_stale_petg_when_pla_loaded():
    """/kx/filament/slots must not show the stale PETG identity once PLA loads."""
    b = _bridge()
    b._ams_slots = [{"global_index": 0, "status": 5, "color": [255, 236, 61], "type": "PLA"}]
    b._filament_profiles = {0: dict(PETG_PROFILE)}
    row = json.loads((await b.handle_kx_filament_slots(MagicMock())).body)["result"][0]
    assert row["material"] == "PLA"        # AMS truth, always
    assert row["filament_name"] == ""      # stale PETG identity gone
    assert row["filament_vendor"] == ""


async def test_display_endpoint_keeps_profile_when_family_matches():
    b = _bridge()
    b._ams_slots = [{"global_index": 0, "status": 5, "color": [10, 20, 30], "type": "PETG"}]
    b._filament_profiles = {0: dict(PETG_PROFILE)}
    row = json.loads((await b.handle_kx_filament_slots(MagicMock())).body)["result"][0]
    assert row["filament_name"] == "KINGROON PETG Basic"
    assert row["filament_vendor"] == "KINGROON"


# ── Integration: print path (lane_data sent to OrcaSlicer) ────────────────────

async def test_lane_data_does_not_leak_stale_petg_identity():
    b = _bridge()
    b._ams_slots = [{"status": 5, "color": [255, 236, 61], "type": "PLA"}]
    b._filament_profiles = {0: dict(PETG_PROFILE)}
    tray = b._build_lane_data()["ams"][0]["tray"][0]
    assert tray["tray_type"] == "PLA"
    assert "PETG" not in tray["name"].upper()
    assert tray["vendor_name"] != "KINGROON"


async def test_lane_data_keeps_profile_when_family_matches():
    b = _bridge()
    b._ams_slots = [{"status": 5, "color": [10, 20, 30], "type": "PETG"}]
    b._filament_profiles = {0: dict(PETG_PROFILE)}
    tray = b._build_lane_data()["ams"][0]["tray"][0]
    assert tray["name"] == "KINGROON PETG Basic"
    assert tray["vendor_name"] == "KINGROON"
