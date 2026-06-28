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
async def test_settings_post_writes_env(client):
    """POST /api/settings schreibt Werte in .env-Datei."""
    c, bridge = client

    with tempfile.TemporaryDirectory() as tmpdir:
        env_path = pathlib.Path(tmpdir) / ".env"
        env_path.write_text("")
        bridge._find_env_path = lambda: env_path

        resp = await c.post("/api/settings", json={
            "printer_ip": "10.0.0.5",
            "mqtt_port":  9883,
            "username":   "userABCD",
            "password":   "secret123",
            "device_id":  "deadbeef01234567",
            "mode_id":    "20030",
        })
        assert resp.status == 200

        content = env_path.read_text()
        assert "PRINTER_IP=10.0.0.5"          in content
        assert "MQTT_USERNAME=userABCD"        in content
        assert "DEVICE_ID=deadbeef01234567"    in content


@pytest.mark.asyncio
async def test_settings_post_preserves_existing_keys(client):
    """POST darf unbekannte Keys in .env nicht löschen (z.B. GITEA_TOKEN)."""
    c, bridge = client

    with tempfile.TemporaryDirectory() as tmpdir:
        env_path = pathlib.Path(tmpdir) / ".env"
        env_path.write_text("GITEA_TOKEN=mytoken\nPRINTER_IP=old\n")
        bridge._find_env_path = lambda: env_path

        await c.post("/api/settings", json={"printer_ip": "10.0.0.99"})

        content = env_path.read_text()
        assert "GITEA_TOKEN=mytoken" in content
        assert "PRINTER_IP=10.0.0.99" in content
