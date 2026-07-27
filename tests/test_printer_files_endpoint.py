"""
Tests für /kx/printer-files (list) und /kx/printer-files/delete —
der zweite Browser-Tab, der Dateien auf dem Drucker selbst zeigt
(via MQTT file/listLocal + file/deleteBatch, live gegen den echten
Kobra X verifiziert, siehe Memory reference_mqtt_listlocal.md).

Important: publish()'s own return value for these actions is just a
generic immediate ACK skeleton (code=0, empty fields) - the real answer
arrives asynchronously via the file/report callback (_on_file), same as
the existing fileDetails fire-and-forget pattern. So publish() itself
returns None/skeleton here, and the "real" response is delivered by
firing bridge._on_file(...) from a background thread, simulating what
the MQTT reader thread would do when the printer's file/report arrives.
"""
import threading
import time

import pytest


LISTLOCAL_SUCCESS = {
    "action": "listLocal",
    "code": 200,
    "state": "success",
    "data": {
        "list_mode": 0,
        "records": [
            {"filename": "a.gcode", "is_dir": False, "size": 100, "timestamp": 1700000000000},
            {"filename": "subdir", "is_dir": True, "size": 0, "timestamp": 1700000001000},
            {"filename": "b.gcode", "is_dir": False, "size": 200, "timestamp": 1700000002000},
        ],
    },
}

LISTLOCAL_FAILED = {
    "action": "listLocal",
    "code": 10112,
    "state": "failed",
    "data": None,
}

DELETEBATCH_SUCCESS = {
    "action": "deleteBatch",
    "code": 200,
    "state": "success",
    "data": None,
    "msg": "done",
}

DELETEBATCH_FAILED = {
    "action": "deleteBatch",
    "code": 10112,
    "state": "failed",
    "data": None,
}

FILEDETAILS_SUCCESS = {
    "action": "fileDetails",
    "code": 200,
    "state": "done",
    "data": {
        "file_details": {
            "thumbnail": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAAB",
            "png_image": "",
            "svg_image": "",
            "objects_skip_parts": [],
        },
        "filename": "a.gcode",
        "root": "local",
    },
}

FILEDETAILS_NO_THUMBNAIL = {
    "action": "fileDetails",
    "code": 200,
    "state": "done",
    "data": {
        "file_details": {"thumbnail": "", "png_image": "", "svg_image": "", "objects_skip_parts": []},
        "filename": "a.gcode",
        "root": "local",
    },
}

FILEDETAILS_FAILED = {
    "action": "fileDetails",
    "code": 10112,
    "state": "failed",
    "data": None,
}


def _deliver_async(bridge, payload, delay=0.05):
    """Simulates the MQTT reader thread delivering a file/report a moment
    after the fire-and-forget publish() call returns."""
    def _fire():
        time.sleep(delay)
        bridge._on_file(payload)
    threading.Thread(target=_fire, daemon=True).start()


@pytest.mark.asyncio
async def test_printer_files_lists_files_and_excludes_dirs(client):
    c, bridge = client
    bridge.client.publish.side_effect = lambda *a, **kw: (_deliver_async(bridge, LISTLOCAL_SUCCESS), None)[1]
    resp = await c.get("/kx/printer-files")
    assert resp.status == 200
    data = await resp.json()
    filenames = [f["filename"] for f in data["result"]]
    assert filenames == ["a.gcode", "b.gcode"]  # "subdir" (is_dir=True) excluded


@pytest.mark.asyncio
async def test_printer_files_uses_correct_mqtt_payload(client):
    c, bridge = client
    bridge.client.publish.side_effect = lambda *a, **kw: (_deliver_async(bridge, LISTLOCAL_SUCCESS), None)[1]
    await c.get("/kx/printer-files")
    args, kwargs = bridge.client.publish.call_args
    assert args[0] == "file"
    assert args[1] == "listLocal"
    assert args[2] == {"page_num": 1, "page_size": 200, "path": "/"}


@pytest.mark.asyncio
async def test_printer_files_returns_502_on_printer_failure(client):
    c, bridge = client
    bridge.client.publish.side_effect = lambda *a, **kw: (_deliver_async(bridge, LISTLOCAL_FAILED), None)[1]
    resp = await c.get("/kx/printer-files")
    assert resp.status == 502


@pytest.mark.asyncio
async def test_printer_files_returns_502_on_timeout(client):
    c, bridge = client
    bridge.client.publish.return_value = None  # no file/report ever arrives
    resp = await c.get("/kx/printer-files")
    assert resp.status == 502


@pytest.mark.asyncio
async def test_printer_file_delete_success(client):
    c, bridge = client
    bridge.client.publish.side_effect = lambda *a, **kw: (_deliver_async(bridge, DELETEBATCH_SUCCESS), None)[1]
    resp = await c.post("/kx/printer-files/delete", json={"filenames": ["a.gcode"]})
    assert resp.status == 200
    data = await resp.json()
    assert data["result"] == "ok"


@pytest.mark.asyncio
async def test_printer_file_delete_uses_correct_mqtt_payload(client):
    c, bridge = client
    bridge.client.publish.side_effect = lambda *a, **kw: (_deliver_async(bridge, DELETEBATCH_SUCCESS), None)[1]
    await c.post("/kx/printer-files/delete", json={"filenames": ["a.gcode", "b.gcode"]})
    args, kwargs = bridge.client.publish.call_args
    assert args[0] == "file"
    assert args[1] == "deleteBatch"
    assert args[2] == {
        "root": "local",
        "files": [
            {"path": "/", "filename": "a.gcode"},
            {"path": "/", "filename": "b.gcode"},
        ],
    }


@pytest.mark.asyncio
async def test_printer_file_delete_empty_filenames_returns_400(client):
    c, _ = client
    resp = await c.post("/kx/printer-files/delete", json={"filenames": []})
    assert resp.status == 400


@pytest.mark.asyncio
async def test_printer_file_delete_returns_502_on_printer_rejection(client):
    c, bridge = client
    bridge.client.publish.side_effect = lambda *a, **kw: (_deliver_async(bridge, DELETEBATCH_FAILED), None)[1]
    resp = await c.post("/kx/printer-files/delete", json={"filenames": ["a.gcode"]})
    assert resp.status == 502


@pytest.mark.asyncio
async def test_printer_file_thumbnail_success(client):
    c, bridge = client
    bridge.client.publish.side_effect = lambda *a, **kw: (_deliver_async(bridge, FILEDETAILS_SUCCESS), None)[1]
    resp = await c.get("/kx/printer-files/a.gcode/thumbnail")
    assert resp.status == 200
    data = await resp.json()
    assert data["result"]["thumbnail"] == "iVBORw0KGgoAAAANSUhEUgAAAAEAAAAB"


@pytest.mark.asyncio
async def test_printer_file_thumbnail_uses_correct_mqtt_payload(client):
    c, bridge = client
    bridge.client.publish.side_effect = lambda *a, **kw: (_deliver_async(bridge, FILEDETAILS_SUCCESS), None)[1]
    await c.get("/kx/printer-files/a.gcode/thumbnail")
    args, kwargs = bridge.client.publish.call_args
    assert args[0] == "file"
    assert args[1] == "fileDetails"
    assert args[2] == {"root": "local", "filename": "a.gcode"}


@pytest.mark.asyncio
async def test_printer_file_thumbnail_empty_when_no_thumbnail_embedded(client):
    c, bridge = client
    bridge.client.publish.side_effect = lambda *a, **kw: (_deliver_async(bridge, FILEDETAILS_NO_THUMBNAIL), None)[1]
    resp = await c.get("/kx/printer-files/a.gcode/thumbnail")
    assert resp.status == 200
    data = await resp.json()
    assert data["result"]["thumbnail"] == ""


@pytest.mark.asyncio
async def test_printer_file_thumbnail_returns_502_on_printer_failure(client):
    c, bridge = client
    bridge.client.publish.side_effect = lambda *a, **kw: (_deliver_async(bridge, FILEDETAILS_FAILED), None)[1]
    resp = await c.get("/kx/printer-files/a.gcode/thumbnail")
    assert resp.status == 502


@pytest.mark.asyncio
async def test_printer_file_thumbnail_is_cached_after_first_fetch(client):
    """Second request for the same filename must not call publish() again."""
    c, bridge = client
    bridge.client.publish.side_effect = lambda *a, **kw: (_deliver_async(bridge, FILEDETAILS_SUCCESS), None)[1]
    resp1 = await c.get("/kx/printer-files/a.gcode/thumbnail")
    assert resp1.status == 200
    call_count_after_first = bridge.client.publish.call_count

    resp2 = await c.get("/kx/printer-files/a.gcode/thumbnail")
    assert resp2.status == 200
    data2 = await resp2.json()
    assert data2["result"]["thumbnail"] == "iVBORw0KGgoAAAANSUhEUgAAAAEAAAAB"
    assert bridge.client.publish.call_count == call_count_after_first  # no new MQTT call
