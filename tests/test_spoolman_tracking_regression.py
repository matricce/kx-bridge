"""Regression test for Spoolman tracking runaway consumption bug.

Bug mechanism:
1. When printing a file that is not in GCodeStore (e.g. file already on the printer
   or started from the printer's screen), `gf` is None.
2. Because `gf` was None, `self._current_job_id` was never set.
3. Because `self._current_job_id` remained empty, `kobra_state == "printing" and not self._current_job_id`
   evaluated to True on EVERY poll tick (every 2-3 seconds).
4. This wiped out `_spoolman_slot_usage`, `_spoolman_slot_reported`, and reset `_spoolman_last_usage`
   and `_spoolman_last_sync` to 0.0 on every tick.
5. In `_spoolman_unreported`, because `_spoolman_slot_usage` was wiped, it fell back to dividing
   `total_used` across all mapped spools.
6. Every 60 seconds, it reported the entire print total (cumulative) to Spoolman again instead of
   the delta, compounding hundreds of meters and driving all spools from 1000g to 0g in minutes.
"""
from unittest.mock import MagicMock
import pytest


def test_untracked_print_does_not_wipe_tracking_on_every_tick(monkeypatch):
    from kobrax_moonraker_bridge import KobraXBridge

    # Mock client and args
    mock_client = MagicMock()
    mock_client.callbacks = {}
    mock_args = MagicMock()
    mock_args.data_dir = "/tmp"
    mock_args.printer_name = "TestPrinter"
    mock_args.spoolman_server = "http://127.0.0.1:7912"
    mock_args.spoolman_sync_rate = 60
    mock_args.ui_theme = "default"
    mock_args.device_id = "test-device"

    mock_store = MagicMock()
    mock_store._gcode_dir = "/tmp"
    mock_store.get_file_by_name.return_value = None  # File not in store!

    bridge = KobraXBridge(mock_client, args=mock_args, store=mock_store, printer_id="1")
    bridge._spoolman_slot_spools = {0: 101, 1: 102}  # Two spools mapped
    bridge._ams_loaded_slot = 0  # Slot 0 is loaded

    # 1. First print/report tick: print starts
    payload1 = {
        "state": "printing",
        "data": {
            "filename": "internal_file.gcode",
            "supplies_usage": 100,
        }
    }
    bridge._on_print(payload1)

    assert bridge._is_printing_active is True
    assert bridge._current_job_id != ""

    # Simulate slot 0 usage recorded
    bridge._spoolman_slot_usage[0] = 50.0

    # 2. Second print/report tick (2 seconds later): same printing state
    payload2 = {
        "state": "printing",
        "data": {
            "filename": "internal_file.gcode",
            "supplies_usage": 120,
        }
    }
    bridge._on_print(payload2)

    # CRITICAL: It must NOT have wiped _spoolman_slot_usage!
    assert bridge._spoolman_slot_usage.get(0) == 50.0
    assert bridge._is_printing_active is True


def test_spoolman_unreported_never_splits_across_all_spools_when_ams_has_multiple_spools():
    from kobrax_moonraker_bridge import KobraXBridge

    mock_client = MagicMock()
    mock_client.callbacks = {}
    mock_args = MagicMock()
    mock_args.data_dir = "/tmp"
    mock_args.spoolman_server = "http://127.0.0.1:7912"
    mock_args.spoolman_sync_rate = 60
    mock_args.ui_theme = "default"
    mock_args.device_id = "test-device"
    mock_store = MagicMock()
    mock_store._gcode_dir = "/tmp"

    bridge = KobraXBridge(mock_client, args=mock_args, store=mock_store, printer_id="1")
    bridge._spoolman_slot_spools = {0: 1, 1: 2, 2: 3, 3: 4}  # 4 spools in AMS
    bridge._state["supplies_usage"] = 500
    bridge._spoolman_slot_usage = {}  # Empty!
    bridge._spoolman_slot_reported = {}

    # Case A: Loaded slot is known (slot 1)
    bridge._ams_loaded_slot = 1
    unreported = bridge._spoolman_unreported()
    # It must attribute exclusively to the loaded slot, NEVER dividing by 4!
    assert unreported == {1: 500.0}

    # Case B: Loaded slot is unknown (-1)
    bridge._ams_loaded_slot = -1
    unreported_unknown = bridge._spoolman_unreported()
    # It must NOT split across all 4 spools! It should return empty dict and refuse to corrupt all spools.
    assert unreported_unknown == {}


def test_spoolman_restarting_midprint_does_not_create_huge_delta():
    from kobrax_moonraker_bridge import KobraXBridge

    mock_client = MagicMock()
    mock_client.callbacks = {}
    mock_args = MagicMock()
    mock_args.data_dir = "/tmp"
    mock_args.spoolman_server = "http://127.0.0.1:7912"
    mock_args.spoolman_sync_rate = 60
    mock_args.ui_theme = "default"
    mock_args.device_id = "test-device"
    mock_store = MagicMock()
    mock_store._gcode_dir = "/tmp"

    bridge = KobraXBridge(mock_client, args=mock_args, store=mock_store, printer_id="1")
    bridge._spoolman_slot_spools = {0: 10}
    bridge._ams_loaded_slot = 0

    # Bridge starts while print is ALREADY at 5000mm
    bridge._state["supplies_usage"] = 5000
    payload = {
        "state": "printing",
        "data": {
            "filename": "running.gcode",
            "supplies_usage": 5000,
        }
    }
    bridge._on_print(payload)

    # First attribute tick: printer reports 5010mm (+10mm delta)
    bridge._state["supplies_usage"] = 5010
    bridge._spoolman_attribute_tick({})

    # Delta should be ONLY 10mm, NOT 5010mm!
    assert bridge._spoolman_slot_usage.get(0) == pytest.approx(10.0)
