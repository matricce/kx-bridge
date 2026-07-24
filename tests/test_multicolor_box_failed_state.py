"""AttributeError crash on multiColorBox/report failure (Issue #100).

Real KX2-Pro bug: manually assigning a filament profile to an ACE slot
(custom-RFID / third-party filament) gets rejected by the printer. Instead of
echoing the normal success shape, the printer replies with `state: "failed"`
and `data` as a 2-element LIST (`["multi_color_box", [...]]`) instead of the
usual dict (`{"multi_color_box": [...]}`). `_on_multicolor_box` called
`data.get(...)` unconditionally, crashing with
`AttributeError: 'list' object has no attribute 'get'` and silently dropping
the report (including the slot-state update it would otherwise have done).
"""
import argparse
import tempfile
from unittest.mock import MagicMock

from kobrax_moonraker_bridge import KobraXBridge

# Exact failure payload from the Issue #100 log.
FAILED_PAYLOAD = {
    "state": "failed",
    "data": ["multi_color_box", [{"filaments": {"id": 2}, "id": 0}]],
}

SUCCESS_PAYLOAD = {
    "state": "success",
    "data": {
        "head_tools_model": 1,
        "multi_color_box": [
            {"id": -1, "slots": []},
            {
                "id": 0,
                "slots": [
                    {"index": 0, "type": "PLA", "color": [0, 156, 189], "status": 5},
                ],
            },
        ],
    },
}


def _bridge():
    c = MagicMock(); c.callbacks = {}; c.connected = False
    args = argparse.Namespace(
        printer_ip="", mqtt_port=9883, username="", password="",
        mode_id="20030", device_id="", host="127.0.0.1", port=7125,
        data_dir=tempfile.mkdtemp(prefix="kxmcb-"),
    )
    return KobraXBridge(c, args=args)


def test_failed_state_does_not_crash():
    b = _bridge()
    b._on_multicolor_box(FAILED_PAYLOAD)  # must not raise
    assert b._state["last_ams_set_error"] is True


def test_success_after_failure_clears_error_flag():
    b = _bridge()
    b._on_multicolor_box(FAILED_PAYLOAD)
    assert b._state["last_ams_set_error"] is True
    b._on_multicolor_box(SUCCESS_PAYLOAD)
    assert b._state["last_ams_set_error"] is False


def test_non_dict_data_without_failed_state_does_not_crash():
    """Defensive guard: any future non-dict `data` shape must not crash,
    even if the printer doesn't set state="failed" for it."""
    b = _bridge()
    b._on_multicolor_box({"state": "success", "data": ["multi_color_box", []]})


def test_failed_report_is_logged_with_the_triggering_request(caplog):
    """The failure payload alone carries no slot/type/color info - the log
    must correlate it with the setInfo request that triggered it, otherwise
    the failure reason can't be diagnosed from bridge logs alone."""
    import logging
    b = _bridge()
    b._last_ams_set_request = {"global": 6, "box": 0, "local_slot": 3, "type": "PLA", "color": [33, 39, 33]}
    with caplog.at_level(logging.WARNING):
        b._on_multicolor_box(FAILED_PAYLOAD)
    assert any("global" in r.message and "6" in r.message for r in caplog.records)
