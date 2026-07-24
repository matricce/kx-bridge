"""Camera stream hangs forever after printer reboot (Issue #99).

The printer rotates its stream token on reboot, changing the camera URL.
CameraCache.set_url() used to be a bare assignment - the running ffmpeg loops
never noticed since they only re-read self._url at the top of their outer
loop, which they never reach while permanently blocked reading stdout from
the now-silent, stale-token connection. set_url() must detect the change and
tear the loops down so the next ensure_running() respawns them against the
new URL.
"""
from kobrax_moonraker_bridge import CameraCache


def test_set_url_first_time_does_not_reset():
    """No prior URL - nothing stale to tear down."""
    c = CameraCache()
    calls = []
    c.reset = lambda: calls.append(True)
    c.set_url("http://printer/live/tokenA")
    assert c._url == "http://printer/live/tokenA"
    assert not calls


def test_set_url_same_value_does_not_reset():
    c = CameraCache()
    calls = []
    c.set_url("http://printer/live/tokenA")
    c.reset = lambda: calls.append(True)
    c.set_url("http://printer/live/tokenA")
    assert not calls


def test_set_url_changed_triggers_reset():
    """The actual bug scenario: token rotates after a printer reboot."""
    c = CameraCache()
    calls = []
    c.set_url("http://printer/live/tokenA")
    c.reset = lambda: calls.append(True)
    c.set_url("http://printer/live/tokenB")
    assert c._url == "http://printer/live/tokenB"
    assert calls == [True]


def test_set_url_empty_to_value_does_not_reset():
    """Startup case: no URL known yet, first status push sets it - nothing
    running to tear down."""
    c = CameraCache()
    calls = []
    c.reset = lambda: calls.append(True)
    c.set_url("http://printer/live/tokenA")
    assert not calls
