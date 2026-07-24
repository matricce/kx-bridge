"""Empty-tray placeholder bug in the OrcaSlicer "upload and print" path.

Real KX1 bug (confirmed 2026-07-22): printing Filament 4 with the slot below it
EMPTY fails; with all slots full it works. `_start_print` -> `_build_auto_ams_box_mapping`
inserts a positional placeholder at each gap whose `ams_index` points at the
gap's own (physically EMPTY) tray. The printer rejects a mapping entry that
references an empty tray, even for a tool the GCode never calls.

Invariant the fix must hold: EVERY entry's ams_index references a LOADED tray.
Positional alignment (entry N = TN, from a16062f) must be preserved.
"""
import argparse
import tempfile
from unittest.mock import MagicMock

from kobrax_moonraker_bridge import KobraXBridge

# Real KX1 AMS state: slot 2 (idx 2) EMPTY, below the used Filament 4 (idx 3).
AMS_SLOTS = [
    {"global_index": 0, "box_id": -1, "status": 5, "type": "PLA",      "color": [101, 88, 177]},
    {"global_index": 1, "box_id": -1, "status": 5, "type": "PLA SILK", "color": [239, 96, 163]},
    {"global_index": 2, "box_id": -1, "status": 4, "type": "PLA",      "color": [223, 221, 220]},  # EMPTY
    {"global_index": 3, "box_id": -1, "status": 5, "type": "PLA",      "color": [117, 120, 123]},
]


def _bridge(slots=AMS_SLOTS):
    c = MagicMock(); c.callbacks = {}; c.connected = False
    args = argparse.Namespace(
        printer_ip="", mqtt_port=9883, username="", password="",
        mode_id="20030", device_id="", host="127.0.0.1", port=7125,
        data_dir=tempfile.mkdtemp(prefix="kxauto-"),
    )
    b = KobraXBridge(c, args=args)
    b._filament_mode = "toolhead"
    b._ams_slots = [dict(s) for s in slots]
    return b


def _loaded_ams_indices(b):
    return {b._slot_to_print_ams_index(int(s["global_index"]))
            for s in b._ams_slots if s["status"] == 5}


def test_no_entry_points_at_an_empty_tray_when_only_used_slot_loaded():
    """_start_print filters loaded to the used slot only: loaded=[(3, slot3)].
    Positions 0..2 are placeholders and must NOT reference empty tray idx 2."""
    b = _bridge()
    loaded = [(3, b._ams_slots[3])]

    mapping = b._build_auto_ams_box_mapping(loaded_slots=loaded)

    assert [e["paint_index"] for e in mapping] == [0, 1, 2, 3]  # positional alignment kept
    loaded_ams = _loaded_ams_indices(b)
    bad = [e for e in mapping if e["ams_index"] not in loaded_ams]
    assert not bad, f"entries reference an empty/non-loaded tray: {bad}"


def test_no_entry_points_at_an_empty_tray_with_gap_in_loaded_set():
    """All occupied slots mapped (0,1,3 loaded, 2 empty). The placeholder at
    position 2 must not reference the empty tray idx 2."""
    b = _bridge()
    loaded = [(0, b._ams_slots[0]), (1, b._ams_slots[1]), (3, b._ams_slots[3])]

    mapping = b._build_auto_ams_box_mapping(loaded_slots=loaded)

    assert [e["paint_index"] for e in mapping] == [0, 1, 2, 3]
    loaded_ams = _loaded_ams_indices(b)
    bad = [e for e in mapping if e["ams_index"] not in loaded_ams]
    assert not bad, f"entries reference an empty/non-loaded tray: {bad}"
    # Real loaded slots keep their own ams_index.
    assert mapping[0]["ams_index"] == 0
    assert mapping[1]["ams_index"] == 1
    assert mapping[3]["ams_index"] == 3


def test_all_full_is_unchanged():
    """All slots loaded -> no placeholders, identity mapping (the working case)."""
    slots = [dict(s, status=5) for s in AMS_SLOTS]
    b = _bridge(slots)
    loaded = [(i, b._ams_slots[i]) for i in range(4)]

    mapping = b._build_auto_ams_box_mapping(loaded_slots=loaded)

    assert [e["ams_index"] for e in mapping] == [0, 1, 2, 3]
