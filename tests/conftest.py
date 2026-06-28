"""
Shared fixtures für KX-Bridge Tests.
Startet die Bridge in-process mit einem Mock-MQTT-Client (kein Drucker nötig).
"""
import sys, types, argparse, pytest, pytest_asyncio
from unittest.mock import MagicMock
from aiohttp.test_utils import TestClient, TestServer

# ── Pfad ──────────────────────────────────────────────────────────────────────
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent / "bridge"))

# ── env_loader mocken (keine .env nötig) ──────────────────────────────────────
env_mod = types.ModuleType("env_loader")
env_mod.PRINTER_IP = ""
env_mod.MQTT_PORT  = 9883
env_mod.USERNAME   = ""
env_mod.PASSWORD   = ""
env_mod.MODE_ID    = "20030"
env_mod.DEVICE_ID  = ""
sys.modules["env_loader"] = env_mod

# ── Bridge + App importieren ───────────────────────────────────────────────────
from kobrax_moonraker_bridge import KobraXBridge, build_app  # noqa: E402


def make_mock_client():
    """Minimaler Mock-MQTT-Client — keine Verbindung, keine Threads."""
    c = MagicMock()
    c.callbacks = {}
    c.connected = False
    return c


def make_args(**overrides):
    args = argparse.Namespace(
        printer_ip  = "",
        mqtt_port   = 9883,
        username    = "",
        password    = "",
        mode_id     = "20030",
        device_id   = "",
        host        = "127.0.0.1",
        port        = 7125,
    )
    for k, v in overrides.items():
        setattr(args, k, v)
    return args


@pytest_asyncio.fixture
async def client():
    """TestClient mit frischer Bridge-Instanz, ohne MQTT-Verbindung."""
    mock_client = make_mock_client()
    bridge = KobraXBridge(mock_client, args=make_args())
    app = build_app(bridge)
    async with TestClient(TestServer(app)) as c:
        yield c, bridge


@pytest_asyncio.fixture
async def client_configured():
    """TestClient mit bereits konfigurierten Zugangsdaten."""
    mock_client = make_mock_client()
    args = make_args(printer_ip="192.168.1.100", device_id="abc123deadbeef")
    bridge = KobraXBridge(mock_client, args=args)
    app = build_app(bridge)
    async with TestClient(TestServer(app)) as c:
        yield c, bridge
