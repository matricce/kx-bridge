"""Multi-ACE aggregation in ace_direct mode (Issue #95, Kobra S1).

A Kobra S1 with two daisy-chained ACE Pro units reports
multi_color_box = [{id:0, slots:[4]}, {id:1, slots:[4]}] with NO toolhead
entry (id:-1). The old ace_direct branch kept only ace_boxes[0], silently
dropping the second unit — the dashboard and the OrcaSlicer sync only ever
saw 4 of the 8 slots. Payloads below are trimmed from the real log attached
to the issue.
"""
from kobrax_moonraker_bridge import KobraXBridge


def _slot(index, type_="PLA", color=(1, 2, 3), status=5):
    return {
        "index": index, "sku": "", "type": type_, "color": list(color),
        "edit_status": 0, "status": status,
        "color_group": [list(color) + [255]], "icon_type": 0,
        "consumables_percent": 50,
    }


def _ace_box(box_id, loaded_slot=-1, n_slots=4):
    return {
        "id": box_id, "status": 1, "model_id": 0, "auto_feed": 1,
        "loaded_slot": loaded_slot,
        "feed_status": {"code": 200, "type": -1, "current_status": -1, "slot_index": -1},
        "temp": 30, "humidity": 0,
        "drying_status": {"status": 0, "target_temp": 0, "duration": 0, "remain_time": 0},
        "slots": [_slot(i) for i in range(n_slots)],
    }


def _toolhead_box(n_slots=4):
    box = _ace_box(-1, n_slots=n_slots)
    return box


# ── mode detection ───────────────────────────────────────────────────────────

def test_two_ace_units_no_toolhead_is_ace_direct():
    boxes = [_ace_box(0), _ace_box(1)]
    assert KobraXBridge._detect_filament_mode(boxes) == "ace_direct"


# ── ace_direct aggregation ───────────────────────────────────────────────────

def test_single_ace_unit_yields_4_slots():
    """Kobra X regression: one unit, global indices 0-3 exactly as before."""
    slots, loaded = KobraXBridge._aggregate_slots([_ace_box(0)], "ace_direct")
    assert len(slots) == 4
    assert [s["global_index"] for s in slots] == [0, 1, 2, 3]
    assert all(s["box_id"] == 0 for s in slots)
    assert loaded == -1


def test_two_ace_units_yield_8_slots():
    """Issue #95: the second unit's slots must appear as global 4-7."""
    slots, loaded = KobraXBridge._aggregate_slots([_ace_box(0), _ace_box(1)], "ace_direct")
    assert len(slots) == 8
    assert [s["global_index"] for s in slots] == [0, 1, 2, 3, 4, 5, 6, 7]
    assert [s["box_id"] for s in slots] == [0, 0, 0, 0, 1, 1, 1, 1]


def test_two_ace_units_report_order_does_not_matter():
    """Boxes sorted by id — global numbering stays stable if the firmware
    reports unit 1 before unit 0."""
    slots, _ = KobraXBridge._aggregate_slots([_ace_box(1), _ace_box(0)], "ace_direct")
    assert [s["global_index"] for s in slots] == [0, 1, 2, 3, 4, 5, 6, 7]
    assert [s["box_id"] for s in slots] == [0, 0, 0, 0, 1, 1, 1, 1]


def test_loaded_slot_on_second_unit_maps_to_global():
    slots, loaded = KobraXBridge._aggregate_slots(
        [_ace_box(0), _ace_box(1, loaded_slot=2)], "ace_direct")
    assert loaded == 6  # 1*4 + 2


def test_loaded_slot_on_first_unit_unchanged():
    slots, loaded = KobraXBridge._aggregate_slots(
        [_ace_box(0, loaded_slot=3), _ace_box(1)], "ace_direct")
    assert loaded == 3


# ── ace_hub regression (unchanged behavior) ──────────────────────────────────

def test_ace_hub_numbering_unchanged():
    boxes = [_toolhead_box(), _ace_box(0), _ace_box(1)]
    assert KobraXBridge._detect_filament_mode(boxes) == "ace_hub"
    slots, _ = KobraXBridge._aggregate_slots(boxes, "ace_hub")
    # 3 toolhead + 4 + 4 ACE
    assert len(slots) == 11
    assert [s["global_index"] for s in slots] == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    assert [s["box_id"] for s in slots][:3] == [-1, -1, -1]


# ── _box_local_to_global / _global_to_box_slot round-trip ────────────────────

def _bridge_with_mode(mode, slots):
    b = object.__new__(KobraXBridge)
    b._filament_mode = mode
    b._ams_slots = slots
    return b


def test_box_local_to_global_ace_direct_second_unit():
    b = _bridge_with_mode("ace_direct", [])
    assert b._box_local_to_global(0, 2, []) == 2
    assert b._box_local_to_global(1, 2, []) == 6


def test_global_to_box_slot_round_trip_two_units():
    slots, _ = KobraXBridge._aggregate_slots([_ace_box(0), _ace_box(1)], "ace_direct")
    b = _bridge_with_mode("ace_direct", slots)
    for g in range(8):
        box_id, local = b._global_to_box_slot(g)
        assert (box_id, local) == (g // 4, g % 4)
        assert b._box_local_to_global(box_id, local, []) == g
