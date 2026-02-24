import os
import sys
import pytest
import json

# allow imports from repository root when running under pytest
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import main


def test_logo_loader_handles_tempfile(monkeypatch, tmp_path):
    """Ensure that the loader still finds the asset even if __file__ is bogus.

    Streamlit can copy the script to a temporary location before execution; in
    that case the module's ``__file__`` points to the temp file and our
    original relative paths would not work.  The loader should fall back to
    looking in the working directory, which is where users normally invoke the
    app.
    """
    # simulate being executed from a temporary directory
    monkeypatch.setattr(main, "__file__", str(tmp_path / "fake.py"))
    # cwd remains the repository root; the asset exists there
    uri = main._load_logo_uri()
    assert uri.startswith("data:image/svg+xml;base64,"), "Logo loader failed under temp __file__"
    icon_uri = main._load_icon_uri()
    assert icon_uri.startswith("data:image/svg+xml;base64,"), "Icon loader failed under temp __file__"


def test_add_building_success(monkeypatch):
    # preserve original data
    orig = dict(main.BUILDINGS)
    try:
        j = json.dumps({
            "name": "Test Building",
            "floor_area_m2": 1234,
            "height_m": 3.0,
            "glazing_ratio": 0.2,
            "u_value_wall": 1.5,
            "u_value_roof": 1.8,
            "u_value_glazing": 2.1,
            "baseline_energy_mwh": 100,
            "occupancy_hours": 2000,
            "description": "A test building",
            "built_year": "2025",
            "building_type": "Test",
        })
        ok, msg = main._add_building_from_json(j)
        assert ok
        assert "Test Building" in main.BUILDINGS
        assert main.BUILDINGS["Test Building"]["floor_area_m2"] == 1234
    finally:
        main.BUILDINGS.clear()
        main.BUILDINGS.update(orig)


def test_add_building_failure():
    ok, msg = main._add_building_from_json("not a json")
    assert not ok
    assert "JSON parse error" in msg
    ok, msg = main._add_building_from_json(json.dumps({}))
    assert not ok
    assert "Missing \"name\"" in msg


def test_add_scenario_success(monkeypatch):
    orig = dict(main.SCENARIOS)
    try:
        j = json.dumps({
            "name": "Test Scenario",
            "description": "Testing",
            "u_wall_factor": 1.0,
            "u_roof_factor": 1.0,
            "u_glazing_factor": 1.0,
            "solar_gain_reduction": 0.0,
            "infiltration_reduction": 0.0,
            "renewable_kwh": 0,
            "install_cost_gbp": 0,
            "colour": "#000000",
            "icon": "🧪",
        })
        ok, msg = main._add_scenario_from_json(j)
        assert ok
        assert "Test Scenario" in main.SCENARIOS
        assert main.SCENARIOS["Test Scenario"]["icon"] == "🧪"
    finally:
        main.SCENARIOS.clear()
        main.SCENARIOS.update(orig)


def test_add_scenario_failure():
    ok, msg = main._add_scenario_from_json("[]")
    assert not ok
    assert "JSON parse error" in msg or "Missing \"name\"" in msg
