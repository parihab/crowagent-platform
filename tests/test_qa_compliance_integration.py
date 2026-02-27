"""
QA Test Suite — compliance.py integration edge cases
======================================================
Tests for DEF-001 (glazing_ratio crash), compliance boundary conditions,
and all four segment compliance tool integrations.
"""
from __future__ import annotations

import os
import sys
import pytest

_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

import app.compliance as compliance


# ─────────────────────────────────────────────────────────────────────────────
# DEF-002 REGRESSION: part_l_compliance_check does NOT accept glazing_ratio
# ─────────────────────────────────────────────────────────────────────────────

class TestPartLSignatureRegression:
    """Ensure part_l_compliance_check raises TypeError if invalid kwarg passed."""

    def test_glazing_ratio_kwarg_raises_type_error(self):
        with pytest.raises(TypeError):
            compliance.part_l_compliance_check(
                u_wall=0.18, u_roof=0.11, u_glazing=1.2,
                floor_area_m2=150.0, annual_energy_kwh=15000.0,
                glazing_ratio=0.35,  # not a valid parameter
            )

    def test_valid_call_with_building_type_does_not_raise(self):
        result = compliance.part_l_compliance_check(
            u_wall=0.18, u_roof=0.11, u_glazing=1.2,
            floor_area_m2=150.0, annual_energy_kwh=15000.0,
            building_type="individual_selfbuild",
        )
        assert "part_l_2021_pass" in result

    def test_individual_selfbuild_uses_residential_targets(self):
        result = compliance.part_l_compliance_check(
            u_wall=0.18, u_roof=0.11, u_glazing=1.2,
            floor_area_m2=150.0, annual_energy_kwh=15000.0,
            building_type="individual_selfbuild",
        )
        # residential thresholds: wall ≤ 0.18, roof ≤ 0.11, glazing ≤ 1.20
        assert result["part_l_2021_pass"] is True

    def test_non_domestic_uses_different_targets(self):
        # For non-domestic: wall ≤ 0.26, roof ≤ 0.16, glazing ≤ 1.60
        result = compliance.part_l_compliance_check(
            u_wall=0.25, u_roof=0.15, u_glazing=1.5,
            floor_area_m2=1000.0, annual_energy_kwh=100000.0,
            building_type="non_domestic",
        )
        assert result["part_l_2021_pass"] is True


# ─────────────────────────────────────────────────────────────────────────────
# Boundary conditions for EPC rating estimator
# ─────────────────────────────────────────────────────────────────────────────

class TestEpcRatingBoundaries:
    def test_minimum_floor_area_accepted(self):
        # Minimum is > 0 but the function validates ≥ 1 m²
        result = compliance.estimate_epc_rating(
            floor_area_m2=10.0, annual_energy_kwh=1000.0,
            u_wall=0.5, u_roof=0.3, u_glazing=1.2, glazing_ratio=0.2,
        )
        assert "epc_band" in result

    def test_extremely_efficient_building_reaches_band_a(self):
        result = compliance.estimate_epc_rating(
            floor_area_m2=200.0, annual_energy_kwh=1000.0,  # 5 kWh/m²
            u_wall=0.1, u_roof=0.1, u_glazing=0.8, glazing_ratio=0.2,
        )
        assert result["epc_band"] in ("A", "B")

    def test_very_poor_building_reaches_band_g(self):
        result = compliance.estimate_epc_rating(
            floor_area_m2=50.0, annual_energy_kwh=500_000.0,  # 10,000 kWh/m²
            u_wall=5.0, u_roof=4.0, u_glazing=5.5, glazing_ratio=0.5,
        )
        assert result["epc_band"] == "G"

    def test_mees_compliant_now_flag(self):
        # D or above is MEES compliant now
        result = compliance.estimate_epc_rating(
            floor_area_m2=100.0, annual_energy_kwh=10000.0,
            u_wall=0.8, u_roof=0.5, u_glazing=2.0, glazing_ratio=0.25,
        )
        if result["epc_band"] in ("A", "B", "C", "D", "E"):
            assert result["mees_compliant_now"] is True
        else:
            assert result["mees_compliant_now"] is False


# ─────────────────────────────────────────────────────────────────────────────
# MEES gap analysis edge cases
# ─────────────────────────────────────────────────────────────────────────────

class TestMeesGapEdgeCases:
    def test_already_at_band_c_no_gap(self):
        # Band C requires SAP >= 69 (EPC_BANDS: (69, "C",...)); SAP 70 is already in band C
        result = compliance.mees_gap_analysis(current_sap=70.0, target_band="C")
        assert result["sap_gap"] <= 0.0
        assert result["recommended_measures"] == []

    def test_very_low_sap_large_gap(self):
        result = compliance.mees_gap_analysis(current_sap=10.0, target_band="C")
        assert result["sap_gap"] > 0.0
        assert len(result["recommended_measures"]) > 0
        assert result["total_cost_low"] > 0
        assert result["total_cost_high"] >= result["total_cost_low"]

    def test_target_band_d_is_accepted(self):
        result = compliance.mees_gap_analysis(current_sap=20.0, target_band="D")
        assert "sap_gap" in result

    def test_invalid_band_raises(self):
        with pytest.raises(ValueError):
            compliance.mees_gap_analysis(current_sap=30.0, target_band="Z")


# ─────────────────────────────────────────────────────────────────────────────
# SECR / carbon baseline edge cases
# ─────────────────────────────────────────────────────────────────────────────

class TestCarbonBaselineEdgeCases:
    def test_zero_floor_area_gives_none_intensity(self):
        result = compliance.calculate_carbon_baseline(
            elec_kwh=10000.0, gas_kwh=5000.0,
            oil_kwh=0.0, lpg_kwh=0.0, fleet_miles=0.0,
            floor_area_m2=None,
        )
        assert result["intensity_kgco2_m2"] is None

    def test_large_electricity_consistent_scope2(self):
        kwh = 1_000_000.0
        result = compliance.calculate_carbon_baseline(
            elec_kwh=kwh, gas_kwh=0.0, oil_kwh=0.0, lpg_kwh=0.0,
            fleet_miles=0.0, floor_area_m2=5000.0,
        )
        expected_scope2 = round(kwh * 0.20482 / 1000, 2)  # tCO₂e
        assert abs(result["scope2_tco2e"] - expected_scope2) < 0.1

    def test_oil_contributes_to_scope1(self):
        result = compliance.calculate_carbon_baseline(
            elec_kwh=0.0, gas_kwh=0.0,
            oil_kwh=10000.0, lpg_kwh=0.0, fleet_miles=0.0,
        )
        assert result["scope1_tco2e"] > 0.0
        assert result["scope2_tco2e"] == 0.0

    def test_lpg_contributes_to_scope1(self):
        result = compliance.calculate_carbon_baseline(
            elec_kwh=0.0, gas_kwh=0.0,
            oil_kwh=0.0, lpg_kwh=10000.0, fleet_miles=0.0,
        )
        assert result["scope1_tco2e"] > 0.0

    def test_fleet_miles_at_max_boundary(self):
        # Should not raise
        result = compliance.calculate_carbon_baseline(
            elec_kwh=0.0, gas_kwh=0.0, oil_kwh=0.0, lpg_kwh=0.0,
            fleet_miles=10_000_000.0,
        )
        assert result["scope1_tco2e"] > 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Part L FHS threshold
# ─────────────────────────────────────────────────────────────────────────────

class TestPartLFHSThreshold:
    def test_very_efficient_home_is_fhs_ready(self):
        # FHS ready requires: primary_energy_est = kwh/m² * 2.5 <= 35
        # i.e. annual_energy_kwh/floor_area_m2 <= 14 kWh/m²/yr
        # Use 500 kWh / 100 m² = 5 kWh/m²/yr * 2.5 = 12.5 <= 35
        result = compliance.part_l_compliance_check(
            u_wall=0.15, u_roof=0.10, u_glazing=0.8,
            floor_area_m2=100.0, annual_energy_kwh=500.0,
        )
        assert result["fhs_ready"] is True

    def test_poor_home_not_fhs_ready(self):
        result = compliance.part_l_compliance_check(
            u_wall=2.0, u_roof=2.0, u_glazing=5.5,
            floor_area_m2=100.0, annual_energy_kwh=50000.0,
        )
        assert result["fhs_ready"] is False

    def test_fhs_threshold_key_present(self):
        result = compliance.part_l_compliance_check(
            u_wall=0.18, u_roof=0.11, u_glazing=1.2,
            floor_area_m2=120.0, annual_energy_kwh=12000.0,
        )
        assert "fhs_threshold" in result
        assert result["fhs_threshold"] > 0

    def test_primary_energy_proportional_to_consumption(self):
        r_low = compliance.part_l_compliance_check(
            u_wall=0.18, u_roof=0.11, u_glazing=1.2,
            floor_area_m2=120.0, annual_energy_kwh=5000.0,
        )
        r_high = compliance.part_l_compliance_check(
            u_wall=0.18, u_roof=0.11, u_glazing=1.2,
            floor_area_m2=120.0, annual_energy_kwh=50000.0,
        )
        assert r_high["primary_energy_est"] > r_low["primary_energy_est"]
