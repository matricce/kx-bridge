"""Per-printer filament-profile isolation (config_loader).

Regression test for the multi-printer bug (issue #74): the slot->profile mapping
and ``visible_vendors`` lived in a single global ``[filament_profiles]`` section,
so configuring one printer overwrote the other and after a restart both loaded
the same map. Each printer now uses its own ``[filament_profiles_<id>]`` section,
with a read-fallback to the legacy global section for backward compatibility.
"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))  # repo root
import config_loader  # noqa: E402

BASE_INI = (
    "[printer_1]\nname = K1\n\n"
    "[printer_2]\nname = K2\n\n"
    "[filament_profiles]\n"
    "visible_vendors = Anycubic, SUNLU\n"
    "slot_0_vendor = Anycubic\nslot_0_name = Anycubic PLA+\nslot_0_id = GFPLA+\n"
)


def _use_ini(monkeypatch, tmp_path, text=BASE_INI):
    path = tmp_path / "config.ini"
    path.write_text(text, encoding="utf-8")
    monkeypatch.setattr(config_loader, "_find_config_file", lambda: path)
    return path


def test_legacy_global_still_works(tmp_path, monkeypatch):
    """No printer_id -> original global section (single-printer back-compat)."""
    _use_ini(monkeypatch, tmp_path)
    assert config_loader.list_filament_profiles()[0]["name"] == "Anycubic PLA+"
    assert config_loader.list_visible_vendors() == ["Anycubic", "SUNLU"]


def test_read_falls_back_to_global_until_first_save(tmp_path, monkeypatch):
    """Before any per-printer save, both printers see the global mapping."""
    _use_ini(monkeypatch, tmp_path)
    assert config_loader.list_filament_profiles("1")[0]["name"] == "Anycubic PLA+"
    assert config_loader.list_filament_profiles("2")[0]["name"] == "Anycubic PLA+"


def test_saving_one_printer_does_not_touch_the_other(tmp_path, monkeypatch):
    """Core regression: configuring printer 1 must not change printer 2."""
    _use_ini(monkeypatch, tmp_path)
    config_loader.save_filament_profiles(
        {0: {"vendor": "KINGROON", "name": "KINGROON PLA Basic", "id": "Pc0b8a01"}}, "1")
    assert config_loader.list_filament_profiles("1")[0]["name"] == "KINGROON PLA Basic"
    assert config_loader.list_filament_profiles("2")[0]["name"] == "Anycubic PLA+"
    # legacy global section preserved untouched
    assert config_loader.list_filament_profiles()[0]["name"] == "Anycubic PLA+"


def test_visible_vendors_isolated_per_printer(tmp_path, monkeypatch):
    _use_ini(monkeypatch, tmp_path)
    config_loader.save_visible_vendors(["KINGROON"], "1")
    assert config_loader.list_visible_vendors("1") == ["KINGROON"]
    assert config_loader.list_visible_vendors("2") == ["Anycubic", "SUNLU"]


def test_save_visible_vendors_keeps_slot_fallback(tmp_path, monkeypatch):
    """Creating a per-printer section only for vendors must not orphan slots."""
    _use_ini(monkeypatch, tmp_path)
    config_loader.save_visible_vendors(["KINGROON"], "1")
    assert config_loader.list_filament_profiles("1")[0]["name"] == "Anycubic PLA+"
