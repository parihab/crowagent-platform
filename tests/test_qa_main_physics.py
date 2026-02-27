"""
QA Test Suite — app/main.py local calculate_thermal_load
=========================================================
Tests the local physics implementation in app/main.py to ensure it stays
in sync with core/physics.py (DEF-001, DEF-003, DEF-004 regression guards).

Key scenarios tested:
- Baseline scenario returns exactly declared energy / 0% savings
- Division-by-zero guard for zero-baseline-energy building
- All intervention scenarios produce savings > baseline
- Local function output matches core/physics.py output for all combinations
"""
from __future__ import annotations

import os
import sys
import pytest

# Ensure app directory is importable
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

from app import main as app_main
import core.physics as core_physics


BASELINE_SCENARIO = app_main.SCENARIOS["Baseline (No Intervention)"]
WEATHER = {"temperature_c": 10.5, "is_live": False, "condition_icon": "", "humidity": 80}


# ─────────────────────────────────────────────────────────────────────────────
# DEF-001 REGRESSION: is_baseline check
# ─────────────────────────────────────────────────────────────────────────────

class TestBaselineScenario:
    """Baseline must return exactly the declared energy and zero savings."""

    @pytest.mark.parametrize("bname", list(app_main.BUILDINGS.keys()))
    def test_baseline_returns_declared_energy(self, bname):
        building = app_main.BUILDINGS[bname]
        result = app_main.calculate_thermal_load(building, BASELINE_SCENARIO, WEATHER)
        assert result["scenario_energy_mwh"] == building["baseline_energy_mwh"], (
            f"[{bname}] Baseline energy {result['scenario_energy_mwh']} != "
            f"declared {building['baseline_energy_mwh']}"
        )

    @pytest.mark.parametrize("bname", list(app_main.BUILDINGS.keys()))
    def test_baseline_has_zero_saving_pct(self, bname):
        building = app_main.BUILDINGS[bname]
        result = app_main.calculate_thermal_load(building, BASELINE_SCENARIO, WEATHER)
        assert result["energy_saving_pct"] == 0.0, (
            f"[{bname}] Baseline saving_pct should be 0.0, got {result['energy_saving_pct']}"
        )

    @pytest.mark.parametrize("bname", list(app_main.BUILDINGS.keys()))
    def test_baseline_has_zero_saving_mwh(self, bname):
        building = app_main.BUILDINGS[bname]
        result = app_main.calculate_thermal_load(building, BASELINE_SCENARIO, WEATHER)
        assert result["energy_saving_mwh"] == 0.0, (
            f"[{bname}] Baseline energy_saving_mwh should be 0.0, got {result['energy_saving_mwh']}"
        )

    @pytest.mark.parametrize("bname", list(app_main.BUILDINGS.keys()))
    def test_baseline_has_zero_annual_saving(self, bname):
        building = app_main.BUILDINGS[bname]
        result = app_main.calculate_thermal_load(building, BASELINE_SCENARIO, WEATHER)
        assert result["annual_saving_gbp"] == 0.0, (
            f"[{bname}] Baseline annual_saving_gbp should be 0, got {result['annual_saving_gbp']}"
        )

    @pytest.mark.parametrize("bname", list(app_main.BUILDINGS.keys()))
    def test_baseline_payback_is_none(self, bname):
        building = app_main.BUILDINGS[bname]
        result = app_main.calculate_thermal_load(building, BASELINE_SCENARIO, WEATHER)
        assert result["payback_years"] is None, (
            f"[{bname}] Baseline payback should be None, got {result['payback_years']}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# DEF-003 REGRESSION: division-by-zero guard
# ─────────────────────────────────────────────────────────────────────────────

class TestDivisionByZeroGuard:
    """energy_saving_pct must not raise ZeroDivisionError for zero-baseline buildings."""

    def test_zero_baseline_energy_no_crash(self):
        zero_building = {
            **app_main.BUILDINGS["Greenfield Library"],
            "baseline_energy_mwh": 0.0,
        }
        # Must not raise
        result = app_main.calculate_thermal_load(zero_building, BASELINE_SCENARIO, WEATHER)
        assert result["energy_saving_pct"] == 0.0

    def test_zero_baseline_with_intervention_no_crash(self):
        zero_building = {
            **app_main.BUILDINGS["Greenfield Library"],
            "baseline_energy_mwh": 0.0,
        }
        scenario = app_main.SCENARIOS["Solar Glass Installation"]
        # Must not raise
        result = app_main.calculate_thermal_load(zero_building, scenario, WEATHER)
        assert isinstance(result["energy_saving_pct"], float)


# ─────────────────────────────────────────────────────────────────────────────
# DEF-004 REGRESSION: local function matches core/physics.py
# ─────────────────────────────────────────────────────────────────────────────

class TestLocalVsCoreParity:
    """app/main.py calculate_thermal_load must produce identical output to core/physics.py."""

    @pytest.mark.parametrize("bname,sname", [
        (b, s)
        for b in list(app_main.BUILDINGS.keys())
        for s in list(app_main.SCENARIOS.keys())
    ])
    def test_results_match_core_physics(self, bname, sname):
        building = app_main.BUILDINGS[bname]
        scenario = app_main.SCENARIOS[sname]
        local_result = app_main.calculate_thermal_load(building, scenario, WEATHER)
        core_result  = core_physics.calculate_thermal_load(building, scenario, WEATHER)
        for key in ("scenario_energy_mwh", "energy_saving_pct", "energy_saving_mwh",
                    "carbon_saving_t", "annual_saving_gbp", "payback_years"):
            assert local_result[key] == core_result[key], (
                f"[{bname}/{sname}] key='{key}' mismatch: "
                f"local={local_result[key]} vs core={core_result[key]}"
            )


# ─────────────────────────────────────────────────────────────────────────────
# Intervention correctness: savings > 0 for all non-baseline scenarios
# ─────────────────────────────────────────────────────────────────────────────

class TestInterventionSavings:
    @pytest.mark.parametrize("sname", [
        s for s in app_main.SCENARIOS if s != "Baseline (No Intervention)"
    ])
    @pytest.mark.parametrize("bname", list(app_main.BUILDINGS.keys()))
    def test_interventions_produce_positive_savings(self, bname, sname):
        building = app_main.BUILDINGS[bname]
        scenario = app_main.SCENARIOS[sname]
        result = app_main.calculate_thermal_load(building, scenario, WEATHER)
        assert result["energy_saving_pct"] > 0.0, (
            f"[{bname}/{sname}] expected positive savings, got {result['energy_saving_pct']}%"
        )

    @pytest.mark.parametrize("sname", [
        s for s in app_main.SCENARIOS if s != "Baseline (No Intervention)"
    ])
    def test_scenario_energy_less_than_baseline(self, sname):
        building = app_main.BUILDINGS["Greenfield Library"]
        baseline = app_main.calculate_thermal_load(building, BASELINE_SCENARIO, WEATHER)
        scenario_r = app_main.calculate_thermal_load(
            building, app_main.SCENARIOS[sname], WEATHER)
        assert scenario_r["scenario_energy_mwh"] < baseline["scenario_energy_mwh"], (
            f"[{sname}] scenario energy should be < baseline"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Output key presence
# ─────────────────────────────────────────────────────────────────────────────

class TestOutputKeys:
    _REQUIRED = {
        "baseline_energy_mwh", "scenario_energy_mwh", "energy_saving_mwh",
        "energy_saving_pct", "baseline_carbon_t", "scenario_carbon_t",
        "carbon_saving_t", "annual_saving_gbp", "install_cost_gbp",
        "payback_years", "cost_per_tonne_co2", "renewable_mwh",
        "u_wall", "u_roof", "u_glazing",
    }

    @pytest.mark.parametrize("bname,sname", [
        (b, s)
        for b in list(app_main.BUILDINGS.keys())
        for s in list(app_main.SCENARIOS.keys())
    ])
    def test_all_output_keys_present(self, bname, sname):
        result = app_main.calculate_thermal_load(
            app_main.BUILDINGS[bname], app_main.SCENARIOS[sname], WEATHER)
        missing = self._REQUIRED - set(result.keys())
        assert not missing, f"[{bname}/{sname}] Missing keys: {missing}"


# ─────────────────────────────────────────────────────────────────────────────
# Temperature validation
# ─────────────────────────────────────────────────────────────────────────────

class TestTemperatureValidation:
    def test_extreme_cold_no_crash(self):
        building = app_main.BUILDINGS["Greenfield Library"]
        result = app_main.calculate_thermal_load(
            building, BASELINE_SCENARIO, {"temperature_c": -20.0, "is_live": False})
        assert result["scenario_energy_mwh"] >= 0.0

    def test_hot_day_no_crash(self):
        building = app_main.BUILDINGS["Greenfield Library"]
        result = app_main.calculate_thermal_load(
            building, BASELINE_SCENARIO, {"temperature_c": 35.0, "is_live": False})
        # delta_t clamped to 0 when temp > 21°C, so energy comes from baseline_energy_mwh
        assert result["scenario_energy_mwh"] >= 0.0

    def test_invalid_temperature_raises(self):
        building = app_main.BUILDINGS["Greenfield Library"]
        with pytest.raises(ValueError, match="Physics model validation"):
            app_main.calculate_thermal_load(
                building, BASELINE_SCENARIO, {"temperature_c": 99.0, "is_live": False})
