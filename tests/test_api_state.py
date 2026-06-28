"""
Tests für /api/state — Drucker-Zustandsabfrage.
"""
import pytest


@pytest.mark.asyncio
async def test_state_returns_200(client):
    c, _ = client
    resp = await c.get("/api/state")
    assert resp.status == 200


@pytest.mark.asyncio
async def test_state_schema(client):
    """Alle erwarteten Felder müssen vorhanden und typsicher sein."""
    c, _ = client
    resp = await c.get("/api/state")
    data = await resp.json()

    assert isinstance(data["print_state"],      str)
    assert isinstance(data["kobra_state"],       str)
    assert isinstance(data["nozzle_temp"],       float)
    assert isinstance(data["nozzle_target"],     float)
    assert isinstance(data["bed_temp"],          float)
    assert isinstance(data["bed_target"],        float)
    assert isinstance(data["progress"],          float)
    assert isinstance(data["print_duration"],    int)
    assert isinstance(data["remain_time"],       int)
    assert isinstance(data["curr_layer"],        int)
    assert isinstance(data["total_layers"],      int)
    assert isinstance(data["filename"],          str)
    assert isinstance(data["fan_speed"],         int)
    assert isinstance(data["light_on"],          bool)
    assert isinstance(data["ams_slots"],         list)


@pytest.mark.asyncio
async def test_state_initial_values(client):
    """Im Offline-Start müssen Temperaturen 0 und Zustand 'standby' sein."""
    c, _ = client
    data = await (await c.get("/api/state")).json()

    assert data["print_state"]   == "standby"
    assert data["nozzle_temp"]   == 0.0
    assert data["bed_temp"]      == 0.0
    assert data["progress"]      == 0.0
    assert data["filename"]      == ""


@pytest.mark.asyncio
async def test_state_updates_after_mqtt_print_report(client):
    """Simuliert ein eingehendes print/report MQTT-Paket und prüft State-Update."""
    c, bridge = client

    # Simuliere MQTT-Nachricht wie vom echten Drucker
    bridge._on_print({
        "state": "printing",
        "data": {
            "filename":     "test.gcode",
            "progress":     42,
            "print_time":   10,     # Minuten → 600s
            "remain_time":  5,      # Minuten → 300s
            "curr_layer":   20,
            "total_layers": 100,
        }
    })

    data = await (await c.get("/api/state")).json()

    assert data["print_state"]   == "printing"
    assert data["filename"]      == "test.gcode"
    assert data["progress"]      == pytest.approx(0.42)
    assert data["print_duration"] == 600
    assert data["remain_time"]   == 300
    assert data["curr_layer"]    == 20
    assert data["total_layers"]  == 100


@pytest.mark.asyncio
async def test_state_updates_after_mqtt_temp_report(client):
    """Simuliert ein tempature/report Paket."""
    c, bridge = client

    bridge._on_temp({
        "data": {
            "curr_nozzle_temp":   215.3,
            "target_nozzle_temp": 220.0,
            "curr_hotbed_temp":   59.8,
            "target_hotbed_temp": 60.0,
        }
    })

    data = await (await c.get("/api/state")).json()
    assert data["nozzle_temp"]   == pytest.approx(215.3)
    assert data["nozzle_target"] == pytest.approx(220.0)
    assert data["bed_temp"]      == pytest.approx(59.8)
    assert data["bed_target"]    == pytest.approx(60.0)


@pytest.mark.asyncio
async def test_state_resets_on_cancel(client):
    """Nach 'stoped' müssen Progress und Filename zurückgesetzt werden."""
    c, bridge = client

    # Erst Druck simulieren
    bridge._on_print({"state": "printing", "data": {"filename": "x.gcode", "progress": 50}})
    # Dann Abbruch
    bridge._on_print({"state": "stoped", "data": {}})

    data = await (await c.get("/api/state")).json()
    assert data["progress"]  == 0.0
    assert data["filename"]  == ""
