"""
Tests für /api/settings — Lesen und Schreiben der Verbindungseinstellungen.
"""
import pytest
import tempfile
import pathlib


@pytest.mark.asyncio
async def test_settings_get_returns_200(client):
    c, _ = client
    resp = await c.get("/api/settings")
    assert resp.status == 200


@pytest.mark.asyncio
async def test_settings_get_schema(client):
    c, _ = client
    data = await (await c.get("/api/settings")).json()
    for key in ("printer_ip", "mqtt_port", "username", "password", "device_id", "mode_id"):
        assert key in data


@pytest.mark.asyncio
async def test_settings_get_empty_when_unconfigured(client):
    """Frische Bridge ohne Zugangsdaten → printer_ip und device_id leer."""
    c, _ = client
    data = await (await c.get("/api/settings")).json()
    assert data["printer_ip"] == ""
    assert data["device_id"]  == ""


@pytest.mark.asyncio
async def test_settings_get_returns_configured_values(client_configured):
    """Bridge mit Zugangsdaten → Werte korrekt zurückgegeben."""
    c, _ = client_configured
    data = await (await c.get("/api/settings")).json()
    assert data["printer_ip"] == "192.168.1.100"
    assert data["device_id"]  == "abc123deadbeef"


@pytest.mark.asyncio
async def test_settings_post_writes_config_ini(client):
    """POST /api/settings schreibt Werte in config.ini (Migration von .env, v0.9.x)."""
    c, bridge = client

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = pathlib.Path(tmpdir) / "config.ini"
        bridge._find_config_path = lambda: config_path
        bridge._restart_bridge = lambda: None  # POST triggers a restart — don't kill the test process

        resp = await c.post("/api/settings", json={
            "printer_ip": "10.0.0.5",
            "mqtt_port":  9883,
            "username":   "userABCD",
            "password":   "secret123",
            "device_id":  "deadbeef01234567",
            "mode_id":    "20030",
        })
        assert resp.status == 200

        content = config_path.read_text()
        assert "printer_ip = 10.0.0.5"       in content
        assert "username = userABCD"         in content
        assert "device_id = deadbeef01234567" in content


@pytest.mark.asyncio
async def test_settings_post_preserves_existing_keys(client):
    """POST darf unbekannte Sections/Optionen in config.ini nicht löschen (z.B. Spoolman-Server)."""
    c, bridge = client

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = pathlib.Path(tmpdir) / "config.ini"
        config_path.write_text(
            "[spoolman]\nserver = http://192.168.1.50:7912\n\n"
            "[connection]\nprinter_ip = old\n"
        )
        bridge._find_config_path = lambda: config_path
        bridge._restart_bridge = lambda: None

        await c.post("/api/settings", json={"printer_ip": "10.0.0.99"})

        content = config_path.read_text()
        assert "server = http://192.168.1.50:7912" in content
        assert "printer_ip = 10.0.0.99" in content
