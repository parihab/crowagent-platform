# ═══════════════════════════════════════════════════════════════════════════════
# CrowAgent™ Platform — UK Compliance Module Tests
# © 2026 Aparajita Parihar. All rights reserved.
# ═══════════════════════════════════════════════════════════════════════════════

import pytest
from app.compliance import (
    estimate_epc_rating,
    mees_gap_analysis,
    secr_carbon_baseline,
    part_l_check,
    validate_energy_kwh,
    validate_floor_area,
    validate_u_value,
    MEES_MEASURES,
)
from config.constants import EPC_BANDS


# ─────────────────────────────────────────────────────────────────────────────
# VALIDATION HELPERS
# ─────────────────────────────────────────────────────────────────────────────

class TestValidationHelpers:
    def test_validate_energy_kwh_valid(self):
        ok, msg = validate_energy_kwh(50_000)
        assert ok is True
        assert msg == "ok"

    def test_validate_energy_kwh_zero_is_valid(self):
        ok, msg = validate_energy_kwh(0)
        assert ok is True

    def test_validate_energy_kwh_negative(self):
        ok, msg = validate_energy_kwh(-1)
        assert ok is False
        assert "negative" in msg.lower()

    def test_validate_energy_kwh_unrealistically_large(self):
        ok, msg = validate_energy_kwh(200_000_000)
        assert ok is False
        assert "large" in msg.lower()

    def test_validate_energy_kwh_non_numeric(self):
        ok, msg = validate_energy_kwh("abc")
        assert ok is False

    def test_validate_floor_area_valid(self):
        ok, msg = validate_floor_area(500)
        assert ok is True

    def test_validate_floor_area_zero(self):
        ok, msg = validate_floor_area(0)
        assert ok is False

    def test_validate_floor_area_negative(self):
        ok, msg = validate_floor_area(-10)
        assert ok is False

    def test_validate_floor_area_too_large(self):
        ok, msg = validate_floor_area(2_000_000)
        assert ok is False

    def test_validate_u_value_valid(self):
        ok, msg = validate_u_value(1.8)
        assert ok is True

    def test_validate_u_value_zero(self):
        ok, msg = validate_u_value(0.0)
        assert ok is False

    def test_validate_u_value_too_high(self):
        ok, msg = validate_u_value(7.0)
        assert ok is False
        assert "plausible" in msg.lower()

    def test_validate_u_value_negative(self):
        ok, msg = validate_u_value(-0.5)
        assert ok is False


# ─────────────────────────────────────────────────────────────────────────────
# EPC RATING ESTIMATION
# ─────────────────────────────────────────────────────────────────────────────

class TestEstimateEpcRating:
    """Tests for estimate_epc_rating()."""

    # Typical very-efficient building should reach band B or A
    def test_efficient_building_high_band(self):
        result = estimate_epc_rating(
            building={'floor_area_m2': 500, 'baseline_energy_mwh': 20}
        )
        assert result["band"] in ("A", "B", "C")
        assert result["mees_2028_compliant"] is True
        assert result["mees_compliant_now"] is True

    # Typical pre-2000 poor office should land D or E
    def test_poor_building_low_band(self):
        result = estimate_epc_rating(
            building={'floor_area_m2': 500, 'baseline_energy_mwh': 200}
        )
        assert result["band"] in ("E", "F", "G")
        assert result["mees_2028_compliant"] is False

    # EUI is correctly calculated
    def test_eui_calculation(self):
        result = estimate_epc_rating(
            building={'floor_area_m2': 1000, 'baseline_energy_mwh': 150}
        )
        assert result["eui_kwh_m2"] == pytest.approx(150.0, abs=0.1)

    # SAP score within 0–100 range
    def test_sap_score_in_range(self):
        result = estimate_epc_rating(
            building={'floor_area_m2': 200, 'baseline_energy_mwh': 30}
        )
        assert 1.0 <= result["sap_score"] <= 100.0

    # MEES gap bands: C building should have gap 0
    def test_mees_gap_zero_for_c_band(self):
        result = estimate_epc_rating(
             building={'floor_area_m2': 500, 'baseline_energy_mwh': 30}
        )
        # C or above => gap is 0
        if result["band"] in ("A", "B", "C"):
            assert result["mees_gap_bands"] == 0

    # Invalid floor area raises ValueError
    def test_raises_on_invalid_floor_area(self):
        with pytest.raises(ValueError, match="(?i)floor area"):
            estimate_epc_rating(
                building={'floor_area_m2': -10, 'baseline_energy_mwh': 50}
            )

    # Result dict has all expected keys
    def test_result_has_required_keys(self):
        result = estimate_epc_rating(
            building={'floor_area_m2': 500, 'baseline_energy_mwh': 72}
        )
        for key in ("sap_score", "band", "color", "eui_kwh_m2",
                    "mees_compliant_now", "mees_2028_compliant",
                    "mees_gap_bands", "recommendation"):
            assert key in result, f"Missing key: {key}"

    # Recommendation string is non-empty
    def test_recommendation_non_empty(self):
        result = estimate_epc_rating(
            building={'floor_area_m2': 500, 'baseline_energy_mwh': 72}
        )
        assert len(result["recommendation"]) > 0


# ─────────────────────────────────────────────────────────────────────────────
# MEES GAP ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

class TestMeesGapAnalysis:
    """Tests for mees_gap_analysis()."""

    def test_already_compliant_no_measures(self):
        result = mees_gap_analysis(current_sap=75.0, target_band="C")
        assert result["sap_gap"] == 0.0
        assert result["recommended_measures"] == []
        assert result["total_cost_low"] == 0
        assert result["achievable"] is True

    def test_gap_produces_measures(self):
        result = mees_gap_analysis(current_sap=40.0, target_band="C")
        assert result["sap_gap"] > 0
        assert len(result["recommended_measures"]) > 0

    def test_cost_range_is_positive(self):
        result = mees_gap_analysis(current_sap=30.0, target_band="C")
        if result["recommended_measures"]:
            assert result["total_cost_low"] > 0
            assert result["total_cost_high"] >= result["total_cost_low"]

    def test_target_sap_matches_band_c(self):
        result = mees_gap_analysis(current_sap=50.0, target_band="C")
        assert result["target_sap"] == 69  # band C threshold

    def test_target_band_a(self):
        result = mees_gap_analysis(current_sap=50.0, target_band="A")
        assert result["target_sap"] == 92

    def test_invalid_target_band_raises(self):
        with pytest.raises(ValueError, match="Invalid target band"):
            mees_gap_analysis(current_sap=50.0, target_band="Z")

    def test_measures_have_required_keys(self):
        result = mees_gap_analysis(current_sap=30.0, target_band="C")
        for m in result["recommended_measures"]:
            for key in ("name", "sap_lift", "cost_low", "cost_high", "regulation"):
                assert key in m, f"Measure missing key: {key}"

    def test_result_has_required_keys(self):
        result = mees_gap_analysis(current_sap=55.0, target_band="C")
        for key in ("target_sap", "sap_gap", "recommended_measures",
                    "total_cost_low", "total_cost_high", "achievable"):
            assert key in result


# ─────────────────────────────────────────────────────────────────────────────
# CARBON BASELINE (SECR)
# ─────────────────────────────────────────────────────────────────────────────

class TestSecrCarbonBaseline:
    """Tests for secr_carbon_baseline()."""

    def test_zero_inputs_zero_emissions(self):
        result = secr_carbon_baseline(building={'floor_area_m2': 100})
        assert result["total_tco2e"] == 0.0
        assert result["scope1_tco2e"] == 0.0
        assert result["scope2_tco2e"] == 0.0

    def test_electricity_only(self):
        result = secr_carbon_baseline(building={'floor_area_m2': 100}, elec_kwh=1_000_000)
        expected = 1_000_000 * 0.20482 / 1000
        assert result["scope2_tco2e"] == pytest.approx(expected, rel=0.001)
        assert result["scope1_tco2e"] == 0.0

    def test_gas_only(self):
        result = secr_carbon_baseline(building={'floor_area_m2': 100}, gas_kwh=1_000_000)
        expected = 1_000_000 * 0.18316 / 1000
        assert result["scope1_tco2e"] == pytest.approx(expected, rel=0.001)
        assert result["scope2_tco2e"] == 0.0

    def test_combined_scope1_scope2(self):
        result = secr_carbon_baseline(building={'floor_area_m2': 100}, elec_kwh=100_000, gas_kwh=80_000)
        expected_s2 = 100_000 * 0.20482 / 1000
        expected_s1 = 80_000  * 0.18316 / 1000
        assert result["scope2_tco2e"] == pytest.approx(expected_s2, rel=0.001)
        assert result["scope1_tco2e"] == pytest.approx(expected_s1, rel=0.001)
        assert result["total_tco2e"]  == pytest.approx(expected_s1 + expected_s2, rel=0.001)

    def test_intensity_calculated_when_area_given(self):
        result = secr_carbon_baseline(building={'floor_area_m2': 500}, elec_kwh=100_000)
        assert result["intensity_kgco2_m2"] is not None
        assert result["intensity_kgco2_m2"] > 0

    def test_intensity_none_when_area_not_given(self):
        result = secr_carbon_baseline(building={'floor_area_m2': 0}, elec_kwh=100_000)
        assert result["intensity_kgco2_m2"] is None

    def test_negative_input_raises(self):
        with pytest.raises(ValueError):
            secr_carbon_baseline(building={'floor_area_m2': 100}, elec_kwh=-1)

    def test_invalid_floor_area_raises(self):
        with pytest.raises(ValueError):
            secr_carbon_baseline(building={'floor_area_m2': -50}, elec_kwh=100_000)

    def test_fleet_miles_contribute_to_scope1(self):
        result_no_fleet   = secr_carbon_baseline(building={'floor_area_m2': 100}, gas_kwh=50_000)
        result_with_fleet = secr_carbon_baseline(building={'floor_area_m2': 100}, gas_kwh=50_000, fleet_miles=10_000)
        assert result_with_fleet["scope1_tco2e"] > result_no_fleet["scope1_tco2e"]

    def test_breakdown_keys_present(self):
        result = secr_carbon_baseline(building={'floor_area_m2': 100}, elec_kwh=50_000, gas_kwh=30_000)
        for key in ("electricity_scope2_tco2e", "gas_scope1_tco2e",
                    "oil_scope1_tco2e", "lpg_scope1_tco2e", "fleet_scope1_tco2e"):
            assert key in result["breakdown"]

    def test_secr_threshold_check_present(self):
        result = secr_carbon_baseline(building={'floor_area_m2': 100}, elec_kwh=100_000)
        chk = result["secr_threshold_check"]
        assert "mandatory_reporter" in chk
        assert "supply_chain_pressure" in chk
        assert "pas2060_candidacy" in chk
        assert "note" in chk

    def test_supply_chain_pressure_threshold(self):
        # >50 tCO2e triggers supply-chain flag
        # 50 tCO2e / 0.20482 ≈ 244,120 kWh electricity
        large  = secr_carbon_baseline(building={'floor_area_m2': 100}, elec_kwh=300_000)
        small  = secr_carbon_baseline(building={'floor_area_m2': 100}, elec_kwh=10_000)
        assert large["secr_threshold_check"]["supply_chain_pressure"] is True
        assert small["secr_threshold_check"]["supply_chain_pressure"] is False

    def test_annual_energy_kwh_aggregates_fuels(self):
        result = secr_carbon_baseline(building={'floor_area_m2': 100}, elec_kwh=50_000, gas_kwh=30_000, oil_kwh=10_000)
        assert result["annual_energy_kwh"] == pytest.approx(90_000, abs=1)


# ─────────────────────────────────────────────────────────────────────────────
# PART L / FUTURE HOMES STANDARD COMPLIANCE
# ─────────────────────────────────────────────────────────────────────────────

class TestPartLCheck:
    """Tests for part_l_check()."""

    def test_compliant_build_passes_all(self):
        result = part_l_check(
            building = {'floor_area_m2': 120, 'building_type': 'residential'},
            fabric = {'u_wall': 0.18, 'u_roof': 0.11, 'u_glazing': 1.2},
            scenario_energy_kwh=4_200,   # low PE
        )
        assert result["part_l_2021_pass"] is True
        assert all(item["pass"] for item in result["compliance_items"])

    def test_non_compliant_build_fails(self):
        result = part_l_check(
            building = {'floor_area_m2': 120, 'building_type': 'residential'},
            fabric = {'u_wall': 1.6, 'u_roof': 2.0, 'u_glazing': 2.8},
            scenario_energy_kwh=18_000,
        )
        assert result["part_l_2021_pass"] is False
        fails = [item for item in result["compliance_items"] if not item["pass"]]
        assert len(fails) > 0

    def test_improvement_actions_generated_on_failure(self):
        result = part_l_check(
            building = {'floor_area_m2': 120, 'building_type': 'residential'},
            fabric = {'u_wall': 1.6, 'u_roof': 2.0, 'u_glazing': 2.8},
            scenario_energy_kwh=18_000,
        )
        assert len(result["improvement_actions"]) > 0

    def test_no_improvement_actions_on_full_pass(self):
        result = part_l_check(
            building = {'floor_area_m2': 120, 'building_type': 'residential'},
            fabric = {'u_wall': 0.18, 'u_roof': 0.11, 'u_glazing': 1.2},
            scenario_energy_kwh=4_200,
        )
        assert result["part_l_2021_pass"] is True

    def test_gap_calculated_correctly(self):
        result = part_l_check(
            building = {'floor_area_m2': 120, 'building_type': 'residential'},
            fabric = {'u_wall': 0.50, 'u_roof': 0.30, 'u_glazing': 2.0},
            scenario_energy_kwh=12_000,
        )
        wall_item = next(i for i in result["compliance_items"] if "Wall" in i["element"])
        assert wall_item["gap"] == pytest.approx(0.50 - 0.18, abs=0.001)

    def test_primary_energy_estimated(self):
        result = part_l_check(
            building = {'floor_area_m2': 100, 'building_type': 'residential'},
            fabric = {'u_wall': 0.18, 'u_roof': 0.11, 'u_glazing': 1.2},
            scenario_energy_kwh=10_000,
        )
        # PE = 10000/100 * 2.5 = 250 kWh/m²/yr
        assert result["primary_energy_est"] == pytest.approx(250.0, abs=0.1)

    def test_fhs_threshold_returned(self):
        result = part_l_check(
            building = {'floor_area_m2': 120, 'building_type': 'residential'},
            fabric = {'u_wall': 0.18, 'u_roof': 0.11, 'u_glazing': 1.2},
            scenario_energy_kwh=5_000,
        )
        assert result["fhs_threshold"] == 35

    def test_non_domestic_uses_different_targets(self):
        # non-domestic targets are less stringent than domestic
        result_nd = part_l_check(
            building = {'floor_area_m2': 500, 'building_type': 'commercial'},
            fabric = {'u_wall': 0.25, 'u_roof': 0.15, 'u_glazing': 1.4},
            scenario_energy_kwh=50_000,
        )
        # Should pass non-domestic but potentially fail domestic
        assert result_nd["part_l_2021_pass"] is True

    def test_raises_on_invalid_floor_area(self):
        with pytest.raises(ValueError, match="Part L check"):
            part_l_check(
                building = {'floor_area_m2': 0, 'building_type': 'residential'},
                fabric = {'u_wall': 0.18, 'u_roof': 0.11, 'u_glazing': 1.2},
                scenario_energy_kwh=10_000,
            )

    def test_raises_on_invalid_u_value(self):
        with pytest.raises(ValueError, match="Part L check"):
            part_l_check(
                building = {'floor_area_m2': 120, 'building_type': 'residential'},
                fabric = {'u_wall': -0.5, 'u_roof': 0.11, 'u_glazing': 1.2},
                scenario_energy_kwh=10_000,
            )

    def test_result_has_required_keys(self):
        result = part_l_check(
            building = {'floor_area_m2': 120, 'building_type': 'residential'},
            fabric = {'u_wall': 0.18, 'u_roof': 0.11, 'u_glazing': 1.2},
            scenario_energy_kwh=10_000,
        )
        for key in ("part_l_2021_pass", "fhs_ready", "primary_energy_est",
                    "fhs_threshold", "regs_label", "compliance_items",
                    "overall_verdict", "improvement_actions"):
            assert key in result

    def test_overall_verdict_non_empty(self):
        result = part_l_check(
            building = {'floor_area_m2': 120, 'building_type': 'residential'},
            fabric = {'u_wall': 1.6, 'u_roof': 2.0, 'u_glazing': 2.8},
            scenario_energy_kwh=18_000,
        )
        assert len(result["overall_verdict"]) > 0


# ─────────────────────────────────────────────────────────────────────────────
# EPC BANDS CONSTANT INTEGRITY
# ─────────────────────────────────────────────────────────────────────────────

class TestEpcBandsConstant:
    def test_seven_bands(self):
        assert len(EPC_BANDS) == 7

    def test_bands_in_descending_threshold_order(self):
        thresholds = [t['threshold'] for t in EPC_BANDS]
        assert thresholds == sorted(thresholds, reverse=True)

    def test_all_bands_a_to_g_present(self):
        bands = {b['band'] for b in EPC_BANDS}
        assert bands == {"A", "B", "C", "D", "E", "F", "G"}


# ─────────────────────────────────────────────────────────────────────────────
# MEES MEASURES CONSTANT INTEGRITY
# ─────────────────────────────────────────────────────────────────────────────

class TestMeesMeasuresConstant:
    def test_at_least_four_measures(self):
        assert len(MEES_MEASURES) >= 4

    def test_each_measure_has_required_keys(self):
        for m in MEES_MEASURES:
            for key in ("name", "sap_lift", "cost_low", "cost_high", "regulation"):
                assert key in m, f"Measure '{m.get('name')}' missing key: {key}"

    def test_sap_lifts_positive(self):
        for m in MEES_MEASURES:
            assert m["sap_lift"] > 0

    def test_costs_ordered(self):
        for m in MEES_MEASURES:
            assert m["cost_high"] >= m["cost_low"] > 0
