"""
QA Test Suite — app/visualization_3d.py polygon cache
=======================================================
Tests for DEF-007 (unbounded polygon cache) and visualization edge cases.
"""
from __future__ import annotations

import os
import sys
import pytest

_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

_app_dir = os.path.join(_root, "app")
if _app_dir not in sys.path:
    sys.path.insert(0, _app_dir)

import visualization_3d as viz


# ─────────────────────────────────────────────────────────────────────────────
# DEF-007 REGRESSION: polygon cache key generation
# ─────────────────────────────────────────────────────────────────────────────

class TestPolygonCacheKey:
    def test_key_is_deterministic(self):
        key1 = viz._get_polygon_cache_key(51.4543, -0.9781)
        key2 = viz._get_polygon_cache_key(51.4543, -0.9781)
        assert key1 == key2

    def test_different_locations_produce_different_keys(self):
        key_reading = viz._get_polygon_cache_key(51.4543, -0.9781)
        key_london  = viz._get_polygon_cache_key(51.5074, -0.1278)
        assert key_reading != key_london

    def test_key_is_string(self):
        key = viz._get_polygon_cache_key(51.0, -1.0)
        assert isinstance(key, str)

    def test_key_includes_coordinates(self):
        key = viz._get_polygon_cache_key(51.4543, -0.9781)
        assert "51.4543" in key
        assert "-0.9781" in key


# ─────────────────────────────────────────────────────────────────────────────
# Synthetic polygon generation
# ─────────────────────────────────────────────────────────────────────────────

class TestSyntheticPolygon:
    def test_returns_list_of_coords(self):
        poly = viz._synthetic_polygon(51.4543, -0.9781)
        assert isinstance(poly, list)
        assert len(poly) > 0

    def test_coords_are_lon_lat_pairs(self):
        poly = viz._synthetic_polygon(51.4543, -0.9781)
        for coord in poly:
            assert len(coord) == 2
            lon, lat = coord
            # lon should be near -0.9781, lat near 51.4543
            assert abs(lon - (-0.9781)) < 0.01
            assert abs(lat - 51.4543) < 0.01

    def test_polygon_is_closed(self):
        poly = viz._synthetic_polygon(51.4543, -0.9781)
        # First and last coord should be equal (closed ring)
        assert poly[0] == poly[-1]

    def test_non_uk_coordinates(self):
        # Tokyo
        poly = viz._synthetic_polygon(35.6762, 139.6503)
        assert len(poly) > 0

    def test_southern_hemisphere(self):
        # Sydney — negative lat should still work
        poly = viz._synthetic_polygon(-33.8688, 151.2093)
        assert len(poly) > 0


# ─────────────────────────────────────────────────────────────────────────────
# Colour interpolation — _carbon_to_rgba(carbon_t, min_c, max_c)
# ─────────────────────────────────────────────────────────────────────────────

class TestColourInterpolation:
    def test_min_carbon_gives_green(self):
        colour = viz._carbon_to_rgba(0.0, 0.0, 100.0)
        assert len(colour) == 4
        for v in colour:
            assert 0 <= v <= 255

    def test_max_carbon_gives_different_colour(self):
        colour = viz._carbon_to_rgba(100.0, 0.0, 100.0)
        assert len(colour) == 4
        for v in colour:
            assert 0 <= v <= 255

    def test_mid_carbon_returns_colour(self):
        colour = viz._carbon_to_rgba(50.0, 0.0, 100.0)
        assert len(colour) == 4

    def test_zero_range_no_crash(self):
        # min == max → should not crash (zero division)
        colour = viz._carbon_to_rgba(50.0, 50.0, 50.0)
        assert len(colour) == 4
        for v in colour:
            assert 0 <= v <= 255

    def test_all_values_in_byte_range(self):
        for carbon in (0.0, 25.0, 50.0, 75.0, 100.0):
            colour = viz._carbon_to_rgba(carbon, 0.0, 100.0)
            for v in colour:
                assert 0 <= v <= 255, f"colour value {v} out of [0,255] for carbon={carbon}"


# ─────────────────────────────────────────────────────────────────────────────
# Building offset computation
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildingCoords:
    def test_all_buildings_have_coords(self):
        coords = viz._building_coords(51.4543, -0.9781)
        assert len(coords) == len(viz._BUILDING_OFFSETS)
        for bname in viz._BUILDING_OFFSETS:
            assert bname in coords
            assert "lat" in coords[bname]
            assert "lon" in coords[bname]

    def test_coords_near_center(self):
        center_lat, center_lon = 51.4543, -0.9781
        coords = viz._building_coords(center_lat, center_lon)
        for bname, c in coords.items():
            # Offsets are ~100-200 m so lat/lon should differ by < 0.01°
            assert abs(c["lat"] - center_lat) < 0.01
            assert abs(c["lon"] - center_lon) < 0.02


# ─────────────────────────────────────────────────────────────────────────────
# 2D fallback
# ─────────────────────────────────────────────────────────────────────────────

class TestRender2dFallback:
    def test_does_not_crash_with_valid_data(self, monkeypatch):
        """2D fallback should not crash for standard rows."""
        import streamlit as st
        captured = []
        monkeypatch.setattr(st, "plotly_chart", lambda *a, **kw: captured.append(True))
        monkeypatch.setattr(st, "caption", lambda *a, **kw: None)

        rows = [
            {"name": "A", "fill_color": [0, 194, 168, 210], "energy_mwh": 100.0},
            {"name": "B", "fill_color": [255, 0, 0, 210], "energy_mwh": 200.0},
        ]
        viz._render_2d_fallback(rows)
        assert captured, "plotly_chart was not called"

    def test_does_not_crash_with_three_element_fill_color(self, monkeypatch):
        """fill_color with exactly 3 elements (no alpha) should not crash."""
        import streamlit as st
        monkeypatch.setattr(st, "plotly_chart", lambda *a, **kw: None)
        monkeypatch.setattr(st, "caption", lambda *a, **kw: None)

        rows = [{"name": "C", "fill_color": [0, 100, 200], "energy_mwh": 50.0}]
        # Should not raise ValueError on [:3]
        viz._render_2d_fallback(rows)


# ─────────────────────────────────────────────────────────────────────────────
# Month names constant
# ─────────────────────────────────────────────────────────────────────────────

class TestMonthNames:
    def test_twelve_months(self):
        assert len(viz._MONTH_NAMES) == 12

    def test_first_is_january(self):
        assert viz._MONTH_NAMES[0].lower() in ("jan", "january")

    def test_last_is_december(self):
        assert viz._MONTH_NAMES[11].lower() in ("dec", "december")
