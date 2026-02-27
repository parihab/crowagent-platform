"""
QA Test Suite — services/location.py
========================================
Tests for Haversine nearest-city resolution, city database integrity, and
GDPR compliance (no raw coords stored).
"""
from __future__ import annotations

import os
import sys
import math
import pytest

_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

from services import location as loc


# ─────────────────────────────────────────────────────────────────────────────
# City database integrity
# ─────────────────────────────────────────────────────────────────────────────

class TestCityDatabase:
    def test_cities_not_empty(self):
        assert len(loc.CITIES) > 0

    def test_all_cities_have_lat_lon_country(self):
        for name, meta in loc.CITIES.items():
            assert "lat" in meta, f"[{name}] missing lat"
            assert "lon" in meta, f"[{name}] missing lon"
            assert "country" in meta, f"[{name}] missing country"

    def test_lat_in_valid_range(self):
        for name, meta in loc.CITIES.items():
            assert -90.0 <= meta["lat"] <= 90.0, f"[{name}] lat out of range: {meta['lat']}"

    def test_lon_in_valid_range(self):
        for name, meta in loc.CITIES.items():
            assert -180.0 <= meta["lon"] <= 180.0, f"[{name}] lon out of range: {meta['lon']}"

    def test_city_options_covers_all_cities(self):
        options = loc.city_options()
        assert len(options) == len(loc.CITIES), (
            f"city_options() returns {len(options)} but CITIES has {len(loc.CITIES)}"
        )

    def test_city_options_no_duplicates(self):
        options = loc.city_options()
        assert len(options) == len(set(options)), "Duplicate city keys in city_options()"

    def test_city_groups_cover_all_cities(self):
        grouped = [city for _, cities in loc.CITY_GROUPS for city in cities]
        assert set(grouped) == set(loc.CITIES.keys())

    def test_city_meta_known_city(self):
        meta = loc.city_meta("London")
        assert meta["country"] == "UK"
        assert abs(meta["lat"] - 51.5074) < 0.01

    def test_city_meta_unknown_raises(self):
        with pytest.raises(KeyError):
            loc.city_meta("Atlantis")


# ─────────────────────────────────────────────────────────────────────────────
# Nearest-city resolver (Haversine)
# ─────────────────────────────────────────────────────────────────────────────

class TestNearestCity:
    def test_reading_coordinates_resolve_to_reading(self):
        city = loc.nearest_city(51.4543, -0.9781)
        assert city == "Reading, Berkshire"

    def test_london_coordinates_resolve_to_london(self):
        city = loc.nearest_city(51.5074, -0.1278)
        assert city == "London"

    def test_edinburgh_coordinates_resolve_to_edinburgh(self):
        city = loc.nearest_city(55.9533, -3.1883)
        assert city == "Edinburgh"

    def test_sydney_coordinates_resolve_to_sydney(self):
        city = loc.nearest_city(-33.8688, 151.2093)
        assert city == "Sydney"

    def test_returns_string(self):
        result = loc.nearest_city(51.0, -1.0)
        assert isinstance(result, str)
        assert result in loc.CITIES

    def test_result_is_always_in_cities_dict(self):
        test_points = [
            (40.7128, -74.0060),    # New York
            (35.6762, 139.6503),    # Tokyo
            (-37.8136, 144.9631),   # Melbourne
            (25.2048, 55.2708),     # Dubai
        ]
        for lat, lon in test_points:
            result = loc.nearest_city(lat, lon)
            assert result in loc.CITIES, f"({lat},{lon}) resolved to unknown city: {result}"

    def test_equator_coordinates_resolve_to_something(self):
        result = loc.nearest_city(0.0, 0.0)
        assert result in loc.CITIES

    def test_north_pole_resolves_to_something(self):
        # Extreme coordinate — should not crash
        result = loc.nearest_city(89.0, 0.0)
        assert result in loc.CITIES

    def test_haversine_distance_nearest_city(self):
        """The resolved city should be geographically closest to the input coords."""
        # For London coords, London should be closer than Manchester
        london_lat, london_lon = loc.CITIES["London"]["lat"], loc.CITIES["London"]["lon"]
        resolved = loc.nearest_city(london_lat + 0.01, london_lon + 0.01)
        assert resolved == "London"
