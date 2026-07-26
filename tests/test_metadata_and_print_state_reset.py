"""server/files/metadata state-leak + terminal-state reset gaps (Issue #102).

Reported by @fmontagna via moonraker-obico:
1. Querying metadata for a file OTHER than the currently/last tracked job
   leaked that job's live layer count / estimated time into the response,
   because _build_file_metadata() read from self._state first and only fell
   back to the file's own GCodeStore row when the state value was falsy.
2. curr_layer/total_layers (and, for a successful "finished" print, every
   other per-job field) were never reset at print end - they stayed at the
   last job's values until the next print happened to overwrite them.
3. The printer reports its own "progress" during pre-print phases
   (preheating/auto_leveling/checking/...), which used to pass straight
   through to display_status.progress/virtual_sdcard.progress and then jump
   non-monotonically once real printing started and progress reset.
"""
import argparse
import tempfile
from unittest.mock import MagicMock

from kobrax_moonraker_bridge import KobraXBridge


def _bridge():
    c = MagicMock(); c.callbacks = {}; c.connected = False
    args = argparse.Namespace(
        printer_ip="", mqtt_port=9883, username="", password="",
        mode_id="20030", device_id="", host="127.0.0.1", port=7125,
        data_dir=tempfile.mkdtemp(prefix="kxmeta-"),
    )
    return KobraXBridge(c, args=args)


def _insert_store_row(b, filename, layer_count=None, est_time=None, size_bytes=0):
    with b._store._lock:
        b._store._conn.execute(
            "INSERT OR REPLACE INTO gcode_files (id, filename, path, size_bytes, uploaded_at, layer_count, est_print_time_sec) "
            "VALUES (?,?,?,?,?,?,?)",
            (filename, filename, "/tmp/" + filename, size_bytes, "2026-01-01T00:00:00Z", layer_count, est_time),
        )
        b._store._conn.commit()


# --- Fix 1: metadata state-leak -------------------------------------------

def test_metadata_for_untracked_file_does_not_leak_running_job_state():
    b = _bridge()
    # A job is "running": live state has its own layer/time values.
    b._state["filename"] = "running.gcode"
    b._state["total_layers"] = 999
    b._state["slicer_time"] = 12345
    b._state["layer_height"] = 0.3

    # Querying a DIFFERENT, unrelated file must use ITS OWN store row, not
    # the running job's live state.
    _insert_store_row(b, "other.gcode", layer_count=42, est_time=600, size_bytes=1000)
    meta = b._build_file_metadata("other.gcode")
    assert meta["layer_count"] == 42
    assert meta["estimated_time"] == 600
    assert meta["size"] == 1000


def test_metadata_for_tracked_file_still_uses_live_state():
    """The currently-tracked file's OWN metadata query should still prefer
    live state (fresher than what was known at upload time)."""
    b = _bridge()
    b._state["filename"] = "running.gcode"
    b._state["total_layers"] = 55
    b._state["slicer_time"] = 999
    _insert_store_row(b, "running.gcode", layer_count=1, est_time=1)
    meta = b._build_file_metadata("running.gcode")
    assert meta["layer_count"] == 55
    assert meta["estimated_time"] == 999


def test_metadata_for_nonexistent_file_falls_back_cleanly():
    b = _bridge()
    b._state["filename"] = "running.gcode"
    b._state["total_layers"] = 999
    meta = b._build_file_metadata("DOES_NOT_EXIST.gcode")
    assert meta["layer_count"] is None
    assert meta["size"] == 1  # documented fallback, unrelated to this fix


# --- Fix 2: terminal-state reset -------------------------------------------

def _print_payload(state, **extra):
    """print/report envelope: `state` is top-level, everything else is under
    `data` (see _on_print: kobra_state = payload.get("state", "")). """
    d = {"filename": "job.gcode"}
    d.update(extra)
    return {"state": state, "data": d}


def test_finished_resets_layer_fields_like_stoped_canceled():
    b = _bridge()
    b._state["curr_layer"] = 10
    b._state["total_layers"] = 20
    b._state["progress"] = 0.5
    b._state["filename"] = "job.gcode"
    b._on_print(_print_payload("finished"))
    assert b._state["curr_layer"] == 0
    assert b._state["total_layers"] == 0
    assert b._state["progress"] == 0.0
    assert b._state["filename"] == ""


def test_canceled_resets_layer_fields():
    b = _bridge()
    b._state["curr_layer"] = 7
    b._state["total_layers"] = 20
    b._on_print(_print_payload("canceled"))
    assert b._state["curr_layer"] == 0
    assert b._state["total_layers"] == 0


def test_on_info_resets_layer_fields_on_terminal_state():
    b = _bridge()
    b._state["curr_layer"] = 7
    b._state["total_layers"] = 20
    b._on_info({"data": {"project": {"state": "finished"}}})
    assert b._state["curr_layer"] == 0
    assert b._state["total_layers"] == 0


# --- Fix 3: progress clamping during pre-print phases ----------------------

def test_progress_not_updated_during_auto_leveling():
    b = _bridge()
    b._state["progress"] = 0.0
    b._on_print(_print_payload("auto_leveling", progress=87))
    assert b._state["progress"] == 0.0


def test_progress_not_updated_during_preheating():
    b = _bridge()
    b._state["progress"] = 0.0
    b._on_print(_print_payload("preheating", progress=42))
    assert b._state["progress"] == 0.0


def test_progress_updates_normally_once_printing():
    b = _bridge()
    b._on_print(_print_payload("printing", progress=33))
    assert b._state["progress"] == 0.33


def test_on_info_progress_clamped_during_checking():
    b = _bridge()
    b._state["progress"] = 0.0
    b._on_info({"data": {"project": {"state": "checking", "progress": 55}}})
    assert b._state["progress"] == 0.0
