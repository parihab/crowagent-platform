import os
import sys
import pytest
import streamlit as st

# ensure the "app" folder is on sys.path so modules can be imported directly
_app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app"))
if _app_dir not in sys.path:
    sys.path.insert(0, _app_dir)

import visualization_3d


def test_import_and_basic_functions(monkeypatch):
    # ensure module loads
    assert hasattr(visualization_3d, "render_3d_energy_map")
    assert hasattr(visualization_3d, "render_4d_carbon_timeline")
    assert hasattr(visualization_3d, "fetch_osm_buildings")

    # dummy building data
    data = [
        {"name": "A", "lat": 0.0, "lon": 0.0, "energy_kwh": 10, "carbon_tonnes": 1, "scenario": "x"}
    ]
    # calling the render functions should not raise (streamlit st.* calls are no-ops in tests)
    visualization_3d.render_3d_energy_map(data)
    visualization_3d.render_4d_carbon_timeline(data, {1: data})

    # simulate Overpass API failure by causing Overpass.query to raise
    class Dummy:
        def query(self, q):
            raise Exception("fail")
    monkeypatch.setattr(visualization_3d.overpy, "Overpass", lambda: Dummy())
    assert visualization_3d.fetch_osm_buildings(0.0, 0.0) == []


@pytest.mark.parametrize("month", range(1, 13))
def test_month_names(month):
    assert visualization_3d._MONTH_NAMES[month-1]
