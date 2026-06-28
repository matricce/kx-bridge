"""
Tests für Moonraker-kompatible Endpunkte die OrcaSlicer aufruft.
"""
import pytest


@pytest.mark.asyncio
async def test_server_info(client):
    c, _ = client
    resp = await c.get("/server/info")
    assert resp.status == 200
    data = await resp.json()
    assert data["result"]["klippy_state"] in ("ready", "standby", "error")


@pytest.mark.asyncio
async def test_printer_info(client):
    c, _ = client
    resp = await c.get("/printer/info")
    assert resp.status == 200
    data = await resp.json()
    assert "hostname" in data["result"]


@pytest.mark.asyncio
async def test_objects_list(client):
    c, _ = client
    resp = await c.get("/printer/objects/list")
    assert resp.status == 200
    data = await resp.json()
    objects = data["result"]["objects"]
    # OrcaSlicer erwartet mindestens diese Objekte
    for obj in ("print_stats", "heater_bed", "extruder", "display_status"):
        assert obj in objects


@pytest.mark.asyncio
async def test_objects_query_print_stats(client):
    c, _ = client
    resp = await c.get("/printer/objects/query?print_stats")
    assert resp.status == 200
    data = await resp.json()
    ps = data["result"]["status"]["print_stats"]
    assert "state"          in ps
    assert "filename"       in ps
    assert "print_duration" in ps


@pytest.mark.asyncio
async def test_objects_query_temperatures(client):
    c, _ = client
    resp = await c.get("/printer/objects/query?extruder&heater_bed")
    assert resp.status == 200
    data = await resp.json()
    status = data["result"]["status"]
    assert "temperature" in status["extruder"]
    assert "temperature" in status["heater_bed"]


@pytest.mark.asyncio
async def test_octoprint_version(client):
    """OrcaSlicer probt /api/version um Drucker-Typ zu erkennen."""
    c, _ = client
    resp = await c.get("/api/version")
    assert resp.status == 200
    data = await resp.json()
    assert "server" in data
    assert "api"    in data


@pytest.mark.asyncio
async def test_files_list(client):
    c, _ = client
    resp = await c.get("/server/files/list")
    assert resp.status == 200
    data = await resp.json()
    assert isinstance(data["result"], list)
