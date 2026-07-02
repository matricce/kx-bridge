"""Per-printer Spoolman slot-map isolation + persistence (config_loader).

Regression test for two bugs in the Spoolman slot→spool persistence:

  1. The bridge referenced ``config_loader`` while the module alias is
     ``env_loader`` → ``NameError`` swallowed by a bare ``except``, so the map
     was never loaded nor saved (persistence looked implemented but was dead).
  2. The map lived in a single global ``[spoolman] slot_spools`` key, so two
     printers/two AMS units overwrote each other (same class as issue #74/#75).

Each printer now uses its own ``[spoolman_<id>]`` section, with a read-fallback
to the legacy global key for backward compatibility. The global ``[spoolman]``
section keeps ``server`` / ``sync_rate``.
"""
import sys
import pathlib
import configparser

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))  # repo root
import config_loader  # noqa: E402

BASE_INI = (
    "[printer_1]\nname = K1\n\n"
    "[printer_2]\nname = K2\n\n"
    "[spoolman]\n"
    "server = http://192.168.3.200:7912\n"
    "sync_rate = 0\n"
    "slot_spools = 0:1,1:2\n"
)


def _use_ini(monkeypatch, tmp_path, text=BASE_INI):
    path = tmp_path / "config.ini"
    path.write_text(text, encoding="utf-8")
    monkeypatch.setattr(config_loader, "_find_config_file", lambda: path)
    return path


def test_legacy_global_read(tmp_path, monkeypatch):
    """No printer_id -> original global [spoolman] slot_spools (back-compat)."""
    _use_ini(monkeypatch, tmp_path)
    assert config_loader.list_spool_map() == {0: 1, 1: 2}


def test_read_falls_back_to_global_until_first_save(tmp_path, monkeypatch):
    """Before any per-printer save, both printers see the global mapping."""
    _use_ini(monkeypatch, tmp_path)
    assert config_loader.list_spool_map("1") == {0: 1, 1: 2}
    assert config_loader.list_spool_map("2") == {0: 1, 1: 2}


def test_saving_one_printer_does_not_touch_the_other(tmp_path, monkeypatch):
    """Core regression: mapping printer 1 must not change printer 2."""
    _use_ini(monkeypatch, tmp_path)
    config_loader.save_spool_map({0: 42, 1: 17}, "1")
    assert config_loader.list_spool_map("1") == {0: 42, 1: 17}
    # printer 2 has no own section yet -> still the global fallback
    assert config_loader.list_spool_map("2") == {0: 1, 1: 2}
    # legacy global key preserved untouched
    assert config_loader.list_spool_map() == {0: 1, 1: 2}


def test_both_printers_isolated_after_each_saves(tmp_path, monkeypatch):
    _use_ini(monkeypatch, tmp_path)
    config_loader.save_spool_map({0: 42, 1: 17}, "1")
    config_loader.save_spool_map({0: 5, 1: 6}, "2")
    assert config_loader.list_spool_map("1") == {0: 42, 1: 17}
    assert config_loader.list_spool_map("2") == {0: 5, 1: 6}


def test_save_preserves_server_and_sync_rate(tmp_path, monkeypatch):
    """Writing a per-printer map must not clobber [spoolman] server/sync_rate."""
    path = _use_ini(monkeypatch, tmp_path)
    config_loader.save_spool_map({0: 42}, "1")
    cfg = configparser.ConfigParser()
    cfg.read(path, encoding="utf-8")
    assert cfg.get("spoolman", "server") == "http://192.168.3.200:7912"
    assert cfg.get("spoolman", "sync_rate") == "0"
    assert cfg.get("spoolman_1", "slot_spools") == "0:42"


def test_persistence_round_trips(tmp_path, monkeypatch):
    """Save then read back (simulates a bridge restart) — the map survives."""
    _use_ini(monkeypatch, tmp_path, text="[spoolman]\nserver = http://x:7912\n")
    config_loader.save_spool_map({0: 7, 2: 9}, "1")
    assert config_loader.list_spool_map("1") == {0: 7, 2: 9}


def test_empty_map_clears_the_key(tmp_path, monkeypatch):
    _use_ini(monkeypatch, tmp_path)
    config_loader.save_spool_map({0: 42}, "1")
    config_loader.save_spool_map({}, "1")            # clear
    # per-printer key gone -> falls back to the legacy global map
    assert config_loader.list_spool_map("1") == {0: 1, 1: 2}


def test_parse_ignores_malformed_and_nonpositive(tmp_path, monkeypatch):
    _use_ini(monkeypatch, tmp_path,
             text="[spoolman]\nslot_spools = 0:1, x:y, 2:0, 3:-4, 4:5, junk\n")
    assert config_loader.list_spool_map() == {0: 1, 4: 5}
