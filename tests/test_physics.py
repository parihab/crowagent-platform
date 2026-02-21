# © 2026 Aparajita Parihar. All rights reserved.
# CrowAgent™ Platform — Automated Testing Suite for the Physics Engine

import sys
import os
import pytest

# Path setup: ensure the 'core' folder is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.physics import calculate_thermal_load, BUILDINGS, SCENARIOS

# ─────────────────────────────────────────────────────────────────────────────
# Constants (must match physics.py)
# ─────────────────────────────────────────────────────────────────────────────
CARBON_INTENSITY = 0.20482   # kgCO2e/kWh  — BEIS 2023
UNIT_COST        = 0.28      # £/kWh        — HESA 2022-23
UK_AVG_TEMP      = 10.5      # °C


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def run(building_name, scenario_name, temp=UK_AVG_TEMP):
    return calculate_thermal_load(
        BUILDINGS[building_name], SCENARIOS[scenario_name], {"temperature_c": temp}
    )


# ─────────────────────────────────────────────────────────────────────────────
# 1. Baseline logic
# ─────────────────────────────────────────────────────────────────────────────
def test_baseline_logic():
    """Baseline scenario saves nothing and preserves declared U-values."""
    building = BUILDINGS["Greenfield Library"]
    result = run("Greenfield Library", "Baseline (No Intervention)")

    assert result["energy_saving_mwh"] == 0, "Baseline must save 0 MWh"
    assert result["u_wall"] == building["u_value_wall"]
    assert result["u_roof"] == building["u_value_roof"]
    assert result["u_glazing"] == building["u_value_glazing"]
    assert "carbon_saving_t" in result
    assert result["carbon_saving_t"] == 0.0, "Baseline carbon saving must be 0"
    assert result["payback_years"] is None, "Baseline has zero install cost — no payback"


def test_baseline_energy_matches_declared():
    """Baseline energy should equal the declared baseline_energy_mwh for every building."""
    for bname, building in BUILDINGS.items():
        result = run(bname, "Baseline (No Intervention)")
        assert result["scenario_energy_mwh"] == building["baseline_energy_mwh"], (
            f"{bname}: baseline energy mismatch"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 2. Carbon maths
# ─────────────────────────────────────────────────────────────────────────────
def test_carbon_math():
    """Verify carbon savings match the BEIS 2023 factor (0.20482 kgCO2e/kWh)."""
    mwh_saved     = 100
    expected_tco2 = round((mwh_saved * 1000 * CARBON_INTENSITY) / 1000, 1)
    assert expected_tco2 == 20.5


def test_carbon_intensity_consistent():
    """Carbon figures in results must use 0.20482 kgCO2e/kWh."""
    for bname, building in BUILDINGS.items():
        result = run(bname, "Baseline (No Intervention)")
        expected_carbon = round(building["baseline_energy_mwh"] * 1000 * CARBON_INTENSITY / 1000, 1)
        assert result["baseline_carbon_t"] == expected_carbon, (
            f"{bname}: carbon mismatch (expected {expected_carbon}, "
            f"got {result['baseline_carbon_t']})"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 3. All scenarios produce valid outputs
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("building_name", list(BUILDINGS.keys()))
@pytest.mark.parametrize("scenario_name", list(SCENARIOS.keys()))
def test_all_combinations_return_valid_results(building_name, scenario_name):
    """Every building x scenario combination must return a complete, non-negative result."""
    result = run(building_name, scenario_name)

    required_keys = [
        "baseline_energy_mwh", "scenario_energy_mwh", "energy_saving_mwh",
        "energy_saving_pct", "baseline_carbon_t", "scenario_carbon_t",
        "carbon_saving_t", "annual_saving_gbp", "install_cost_gbp",
        "renewable_mwh", "u_wall", "u_roof", "u_glazing",
    ]
    for key in required_keys:
        assert key in result, (
            f"{building_name} x {scenario_name}: missing key '{key}'"
        )

    assert result["scenario_energy_mwh"] >= 0, "Energy must be non-negative"
    assert result["baseline_carbon_t"] >= 0, "Carbon must be non-negative"
    assert result["u_wall"] > 0, "U-wall must be positive"
    assert result["u_roof"] > 0, "U-roof must be positive"
    assert result["u_glazing"] > 0, "U-glazing must be positive"


@pytest.mark.parametrize("scenario_name", [
    "Solar Glass Installation",
    "Green Roof Installation",
    "Enhanced Insulation Upgrade",
    "Combined Package (All Interventions)",
])
def test_interventions_save_more_than_baseline(scenario_name):
    """Non-baseline scenarios must achieve a positive energy and carbon saving."""
    result = run("Greenfield Library", scenario_name)
    assert result["energy_saving_mwh"] > 0, (
        f"{scenario_name}: expected positive energy saving, "
        f"got {result['energy_saving_mwh']}"
    )
    assert result["carbon_saving_t"] > 0, (
        f"{scenario_name}: expected positive carbon saving"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 4. Financial calculations
# ─────────────────────────────────────────────────────────────────────────────
def test_financial_calculation_solar_glass():
    """Payback period and annual saving must be internally consistent for Solar Glass."""
    result = run("Greenfield Library", "Solar Glass Installation")
    install_cost  = result["install_cost_gbp"]
    annual_saving = result["annual_saving_gbp"]

    assert install_cost == 280000
    assert annual_saving > 0, "Solar Glass must have a positive annual saving"

    if result["payback_years"] is not None:
        calculated_payback = round(install_cost / annual_saving, 1)
        assert abs(result["payback_years"] - calculated_payback) < 0.2, (
            f"Payback mismatch: reported {result['payback_years']}, "
            f"calculated {calculated_payback}"
        )


def test_baseline_has_no_install_cost():
    """Baseline scenario has zero install cost and no payback period."""
    result = run("Greenfield Library", "Baseline (No Intervention)")
    assert result["install_cost_gbp"] == 0
    assert result["payback_years"] is None


# ─────────────────────────────────────────────────────────────────────────────
# 5. Edge cases
# ─────────────────────────────────────────────────────────────────────────────
def test_combined_package_best_carbon_saving():
    """Combined Package should achieve the largest carbon saving for each building."""
    for bname in BUILDINGS:
        combined = run(bname, "Combined Package (All Interventions)")
        for sname in SCENARIOS:
            if sname == "Combined Package (All Interventions)":
                continue
            other = run(bname, sname)
            assert combined["carbon_saving_t"] >= other["carbon_saving_t"], (
                f"{bname}: Combined Package should match or beat {sname} on carbon savings"
            )


def test_energy_saving_pct_bounded():
    """Energy saving percentage must be between 0% and 100%."""
    for bname in BUILDINGS:
        for sname in SCENARIOS:
            result = run(bname, sname)
            pct = result["energy_saving_pct"]
            assert 0.0 <= pct <= 100.0, (
                f"{bname} x {sname}: energy_saving_pct={pct} is out of bounds"
            )


def test_all_buildings_have_required_fields():
    """Every building dict must contain the fields expected by the physics engine."""
    required = [
        "floor_area_m2", "height_m", "glazing_ratio",
        "u_value_wall", "u_value_roof", "u_value_glazing",
        "baseline_energy_mwh", "occupancy_hours",
    ]
    for bname, bdata in BUILDINGS.items():
        for field in required:
            assert field in bdata, f"{bname}: missing field '{field}'"
        assert bdata["floor_area_m2"] > 0
        assert 0 < bdata["glazing_ratio"] < 1
        assert bdata["baseline_energy_mwh"] > 0


def test_all_scenarios_have_required_fields():
    """Every scenario dict must contain the fields expected by the physics engine."""
    required = [
        "u_wall_factor", "u_roof_factor", "u_glazing_factor",
        "solar_gain_reduction", "infiltration_reduction",
        "renewable_kwh", "install_cost_gbp",
    ]
    for sname, sdata in SCENARIOS.items():
        for field in required:
            assert field in sdata, f"{sname}: missing field '{field}'"
        assert 0 < sdata["u_wall_factor"] <= 1.0
        assert 0 < sdata["u_roof_factor"] <= 1.0
        assert 0 < sdata["u_glazing_factor"] <= 1.0
