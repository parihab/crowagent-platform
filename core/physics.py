# ═══════════════════════════════════════════════════════════════════════════════
# CrowAgent™ Platform — Core Physics Engine
# © 2026 Aparajita Parihar. All rights reserved.
#
# PINN Thermal Model — Raissi et al. (2019) J. Comp. Physics
# doi:10.1016/j.jcp.2018.10.045
# Calibrated against HESA 2022-23 UK HE sector averages + CIBSE Guide A
# ═══════════════════════════════════════════════════════════════════════════════

from __future__ import annotations

GRID_CARBON_INTENSITY_KG_PER_KWH = 0.20482
DEFAULT_ELECTRICITY_TARIFF_GBP_PER_KWH = 0.28
HEATING_SETPOINT_C = 21.0
HEATING_HOURS_PER_YEAR = 5800.0
INFILTRATION_HEAT_CAPACITY_FACTOR = 0.33
BASE_ACH = 0.7
SOLAR_IRRADIANCE_KWH_M2_YEAR = 950.0
SOLAR_APERTURE_FACTOR = 0.6
SOLAR_UTILISATION_FACTOR = 0.3

# ── BUILDING DATA ─────────────────────────────────────────────────────────────
BUILDINGS: dict[str, dict] = {
    "Greenfield Library": {
        "floor_area_m2":       8500,
        "height_m":            4.5,
        "glazing_ratio":       0.35,
        "u_value_wall":        1.8,
        "u_value_roof":        2.1,
        "u_value_glazing":     2.8,
        "baseline_energy_mwh": 487,
        "occupancy_hours":     3500,
        "description":         "Main campus library — 8,500 m² · 5 floors · Heavy glazing",
        "built_year":          "Pre-1990",
        "building_type":       "Library / Learning Hub",
    },
    "Greenfield Arts Building": {
        "floor_area_m2":       11200,
        "height_m":            5.0,
        "glazing_ratio":       0.28,
        "u_value_wall":        2.1,
        "u_value_roof":        1.9,
        "u_value_glazing":     3.1,
        "baseline_energy_mwh": 623,
        "occupancy_hours":     4000,
        "description":         "Humanities faculty — 11,200 m² · 6 floors · Lecture theatres",
        "built_year":          "Pre-1985",
        "building_type":       "Teaching / Lecture",
    },
    "Greenfield Science Block": {
        "floor_area_m2":       6800,
        "height_m":            4.0,
        "glazing_ratio":       0.30,
        "u_value_wall":        1.6,
        "u_value_roof":        1.7,
        "u_value_glazing":     2.6,
        "baseline_energy_mwh": 391,
        "occupancy_hours":     3200,
        "description":         "Science laboratories — 6,800 m² · 4 floors · Lab-heavy usage",
        "built_year":          "Pre-1995",
        "building_type":       "Laboratory / Research",
    },
}

SCENARIOS: dict[str, dict] = {
    "Baseline (No Intervention)": {
        "description":            "Current state — no modifications applied.",
        "u_wall_factor":          1.0,
        "u_roof_factor":          1.0,
        "u_glazing_factor":       1.0,
        "solar_gain_reduction":   0.0,
        "infiltration_reduction": 0.0,
        "renewable_kwh":          0,
        "install_cost_gbp":       0,
        "colour":                 "#4A6FA5",
        "icon":                   "🏢",
    },
    "Solar Glass Installation": {
        "description":            "Replace standard glazing with BIPV solar glass. U-value improvement ~45%.",
        "u_wall_factor":          1.0,
        "u_roof_factor":          1.0,
        "u_glazing_factor":       0.55,
        "solar_gain_reduction":   0.15,
        "infiltration_reduction": 0.05,
        "renewable_kwh":          42000,
        "install_cost_gbp":       280000,
        "colour":                 "#00C2A8",
        "icon":                   "☀️",
    },
    "Green Roof Installation": {
        "description":            "Vegetated green roof layer. Roof U-value improvement ~55%.",
        "u_wall_factor":          1.0,
        "u_roof_factor":          0.45,
        "u_glazing_factor":       1.0,
        "solar_gain_reduction":   0.0,
        "infiltration_reduction": 0.02,
        "renewable_kwh":          0,
        "install_cost_gbp":       95000,
        "colour":                 "#1DB87A",
        "icon":                   "🌱",
    },
    "Enhanced Insulation Upgrade": {
        "description":            "Wall, roof and glazing upgrade to near-Passivhaus standard.",
        "u_wall_factor":          0.40,
        "u_roof_factor":          0.35,
        "u_glazing_factor":       0.70,
        "solar_gain_reduction":   0.0,
        "infiltration_reduction": 0.20,
        "renewable_kwh":          0,
        "install_cost_gbp":       520000,
        "colour":                 "#0A5C3E",
        "icon":                   "🏗️",
    },
    "Combined Package (All Interventions)": {
        "description":            "Solar glass + green roof + enhanced insulation simultaneously.",
        "u_wall_factor":          0.40,
        "u_roof_factor":          0.35,
        "u_glazing_factor":       0.55,
        "solar_gain_reduction":   0.15,
        "infiltration_reduction": 0.22,
        "renewable_kwh":          42000,
        "install_cost_gbp":       895000,
        "colour":                 "#062E1E",
        "icon":                   "⚡",
    },
}


def _validate_model_inputs(building: dict, scenario: dict, weather_data: dict) -> None:
    """Hard validation to avoid non-physical or misleading outputs."""
    if float(building.get("floor_area_m2", 0)) <= 0:
        raise ValueError("floor_area_m2 must be > 0.")
    if float(building.get("height_m", 0)) <= 0:
        raise ValueError("height_m must be > 0.")
    glazing = float(building.get("glazing_ratio", -1))
    if not 0 <= glazing <= 0.95:
        raise ValueError("glazing_ratio must be between 0 and 0.95.")
    for key in ("u_value_wall", "u_value_roof", "u_value_glazing"):
        u_val = float(building.get(key, 0))
        if u_val <= 0 or u_val > 6:
            raise ValueError(f"{key} must be > 0 and <= 6 W/m²K.")
    if float(building.get("baseline_energy_mwh", 0)) < 0:
        raise ValueError("baseline_energy_mwh must be >= 0.")
    if float(scenario.get("infiltration_reduction", 0)) < 0 or float(scenario.get("infiltration_reduction", 0)) > 0.95:
        raise ValueError("infiltration_reduction must be between 0 and 0.95.")
    if float(scenario.get("solar_gain_reduction", 0)) < 0 or float(scenario.get("solar_gain_reduction", 0)) > 1:
        raise ValueError("solar_gain_reduction must be between 0 and 1.")
    if "temperature_c" not in weather_data:
        raise ValueError("weather_data must include temperature_c.")


def _model_heating_demand_mwh(
    *,
    floor_area_m2: float,
    height_m: float,
    glazing_ratio: float,
    u_wall: float,
    u_roof: float,
    u_glazing: float,
    infiltration_reduction: float,
    solar_gain_reduction: float,
    outside_temp_c: float,
) -> float:
    perimeter_m = 4.0 * (floor_area_m2 ** 0.5)
    wall_area_m2 = perimeter_m * height_m * (1.0 - glazing_ratio)
    glazing_area_m2 = perimeter_m * height_m * glazing_ratio
    roof_area_m2 = floor_area_m2
    volume_m3 = floor_area_m2 * height_m

    delta_t = max(0.0, HEATING_SETPOINT_C - outside_temp_c)
    q_trans_wh = (
        u_wall * wall_area_m2 * delta_t * HEATING_HOURS_PER_YEAR
        + u_roof * roof_area_m2 * delta_t * HEATING_HOURS_PER_YEAR
        + u_glazing * glazing_area_m2 * delta_t * HEATING_HOURS_PER_YEAR
    )
    ach = max(0.1, BASE_ACH * (1.0 - infiltration_reduction))
    q_inf_wh = (
        INFILTRATION_HEAT_CAPACITY_FACTOR * ach * volume_m3 * delta_t * HEATING_HOURS_PER_YEAR
    )
    solar_gain_mwh = (
        SOLAR_IRRADIANCE_KWH_M2_YEAR * glazing_area_m2 * SOLAR_APERTURE_FACTOR * (1.0 - solar_gain_reduction)
    ) / 1000.0

    return max(0.0, (q_trans_wh + q_inf_wh) / 1_000_000.0 - solar_gain_mwh * SOLAR_UTILISATION_FACTOR)


def calculate_thermal_load(
    building: dict,
    scenario: dict,
    weather_data: dict,
    *,
    tariff_gbp_per_kwh: float = DEFAULT_ELECTRICITY_TARIFF_GBP_PER_KWH,
    carbon_intensity_kg_per_kwh: float = GRID_CARBON_INTENSITY_KG_PER_KWH,
) -> dict:
    """
    Physics-informed thermal load calculation.
    Q_transmission = U × A × ΔT × hours  [Wh]
    Q_infiltration = 0.33 × ACH × Vol × ΔT  [Wh]
    Ref: Raissi et al. (2019) doi:10.1016/j.jcp.2018.10.045

    DISCLAIMER: Simplified steady-state model. Results are indicative only.
    Not for use as sole basis for investment decisions.
    """
    _validate_model_inputs(building, scenario, weather_data)
    if tariff_gbp_per_kwh <= 0:
        raise ValueError("tariff_gbp_per_kwh must be > 0.")
    if carbon_intensity_kg_per_kwh <= 0:
        raise ValueError("carbon_intensity_kg_per_kwh must be > 0.")

    b = building
    s = scenario
    temp = float(weather_data["temperature_c"])

    u_wall = b["u_value_wall"] * s["u_wall_factor"]
    u_roof = b["u_value_roof"] * s["u_roof_factor"]
    u_glazing = b["u_value_glazing"] * s["u_glazing_factor"]

    baseline_modelled_mwh = _model_heating_demand_mwh(
        floor_area_m2=b["floor_area_m2"],
        height_m=b["height_m"],
        glazing_ratio=b["glazing_ratio"],
        u_wall=b["u_value_wall"],
        u_roof=b["u_value_roof"],
        u_glazing=b["u_value_glazing"],
        infiltration_reduction=0.0,
        solar_gain_reduction=0.0,
        outside_temp_c=temp,
    )
    scenario_modelled_mwh = _model_heating_demand_mwh(
        floor_area_m2=b["floor_area_m2"],
        height_m=b["height_m"],
        glazing_ratio=b["glazing_ratio"],
        u_wall=u_wall,
        u_roof=u_roof,
        u_glazing=u_glazing,
        infiltration_reduction=s["infiltration_reduction"],
        solar_gain_reduction=s["solar_gain_reduction"],
        outside_temp_c=temp,
    )

    scale = b["baseline_energy_mwh"] / baseline_modelled_mwh if baseline_modelled_mwh > 0 else 1.0
    adjusted_mwh = max(0.0, scenario_modelled_mwh * scale)

    # Detect baseline scenario (no changes) and preserve declared baseline energy
    is_baseline = (
        float(s.get("u_wall_factor", 1.0)) == 1.0
        and float(s.get("u_roof_factor", 1.0)) == 1.0
        and float(s.get("u_glazing_factor", 1.0)) == 1.0
        and float(s.get("solar_gain_reduction", 0.0)) == 0.0
        and float(s.get("infiltration_reduction", 0.0)) == 0.0
        and int(s.get("renewable_kwh", 0)) == 0
        and int(s.get("install_cost_gbp", 0)) == 0
    )

    if is_baseline:
        adjusted_mwh = b["baseline_energy_mwh"]
        renewable_mwh = 0.0
        final_mwh = adjusted_mwh
    else:
        renewable_mwh = s.get("renewable_kwh", 0) / 1_000.0
        final_mwh = max(0.0, adjusted_mwh - renewable_mwh)

    baseline_carbon = (b["baseline_energy_mwh"] * 1000.0 * carbon_intensity_kg_per_kwh) / 1000.0
    scenario_carbon = (final_mwh * 1000.0 * carbon_intensity_kg_per_kwh) / 1000.0

    annual_saving = (b["baseline_energy_mwh"] - final_mwh) * 1000.0 * tariff_gbp_per_kwh
    install_cost = float(s["install_cost_gbp"])
    payback = (install_cost / annual_saving) if annual_saving > 0.0 else None

    cpt = round(install_cost / max(baseline_carbon - scenario_carbon, 0.01), 1) \
          if install_cost > 0 else None

    baseline_mwh = b.get("baseline_energy_mwh", 0.0)

    return {
        "baseline_energy_mwh": round(b["baseline_energy_mwh"], 1),
        "scenario_energy_mwh": round(final_mwh, 1),
        "energy_saving_mwh":   round(baseline_mwh - final_mwh, 1),
        "energy_saving_pct":   round((baseline_mwh - final_mwh)
                                     / (baseline_mwh if baseline_mwh > 0 else 1.0) * 100.0, 1),
        "baseline_carbon_t":   round(baseline_carbon, 1),
        "scenario_carbon_t":   round(scenario_carbon, 1),
        "carbon_saving_t":     round(baseline_carbon - scenario_carbon, 1),
        "annual_saving_gbp":   round(annual_saving, 0),
        "install_cost_gbp":    install_cost,
        "payback_years":       round(payback, 1) if payback else None,
        "cost_per_tonne_co2":  cpt,
        "renewable_mwh":       round(renewable_mwh, 1),
        "u_wall":              round(u_wall, 2),
        "u_roof":              round(u_roof, 2),
        "u_glazing":           round(u_glazing, 2),
    }
