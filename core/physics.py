# ══════════════════════════════════════════════════════════════════════════════
# CrowAgent™ Platform — Physics-Informed Thermal Model
# © 2026 Aparajita Parihar. All rights reserved.
#
# PINN-inspired simplified physics model for campus building thermal load estimation
# Includes interventions such as: solar glass, green roofs, enhanced insulation, renewables
# ══════════════════════════════════════════════════════════════════════════════

from typing import Dict, Any

# ─────────────────────────────────────────────────────────────────────────────
# PHYSICS CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
CARBON_INTENSITY_KG_CO2_PER_KWH = 0.20482  # BEIS 2023 UK grid mix
ELECTRICITY_COST_GBP_PER_KWH = 0.28  # HESA 2022-23 HE sector average
HEATING_SETPOINT_C = 21  # UK Building Regulations Part L
HEATING_SEASON_HOURS_PER_YEAR = 5800  # CIBSE Guide A
SOLAR_IRRADIANCE_KWH_M2_PER_YEAR = 950  # PVGIS Reading, UK

# ─────────────────────────────────────────────────────────────────────────────
# BUILDING DATABASE
# Based on published UK HE sector averages — fictional buildings for demonstration
# ─────────────────────────────────────────────────────────────────────────────
BUILDINGS: Dict[str, Dict[str, Any]] = {
    "Greenfield Library": {
        "u_value_wall": 0.35,              # W/m²K — current performance
        "u_value_roof": 0.25,
        "u_value_window": 2.8,
        "u_value_floor": 0.30,
        "gross_floor_area_m2": 15000,      # ~4,400 students on campus
        "window_area_m2": 2500,            # ~17% of facade
        "roof_area_m2": 3500,
        "wall_area_m2": 8000,
        "floor_area_m2": 3500,
        "ventilation_rate_ach": 0.5,       # air changes per hour
        "occupancy_pattern": "student_library",  # highly variable
        "primary_fuel": "electricity",      # electrically heated (no gas)
        "co2_emissions_t_per_year": 120,   # baseline estimate
    },
    "Greenfield Arts Building": {
        "u_value_wall": 0.40,
        "u_value_roof": 0.30,
        "u_value_window": 3.0,
        "u_value_floor": 0.35,
        "gross_floor_area_m2": 12000,
        "window_area_m2": 2000,
        "roof_area_m2": 3000,
        "wall_area_m2": 7000,
        "floor_area_m2": 3000,
        "ventilation_rate_ach": 0.6,
        "occupancy_pattern": "office_teaching",
        "primary_fuel": "electricity",
        "co2_emissions_t_per_year": 100,
    },
    "Greenfield Science Block": {
        "u_value_wall": 0.38,
        "u_value_roof": 0.28,
        "u_value_window": 2.9,
        "u_value_floor": 0.32,
        "gross_floor_area_m2": 18000,
        "window_area_m2": 3000,
        "roof_area_m2": 4500,
        "wall_area_m2": 9000,
        "floor_area_m2": 4500,
        "ventilation_rate_ach": 0.8,       # labs require higher ventilation
        "occupancy_pattern": "lab_intensive",
        "primary_fuel": "electricity",
        "co2_emissions_t_per_year": 160,
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# INTERVENTION SCENARIOS
# Energy-saving measures with typical cost and energy impact
# ─────────────────────────────────────────────────────────────────────────────
SCENARIOS: Dict[str, Dict[str, Any]] = {
    "Baseline (No Intervention)": {
        "name": "Baseline (No Intervention)",
        "u_wall_multiplier": 1.0,          # no change
        "u_roof_multiplier": 1.0,
        "u_window_multiplier": 1.0,
        "solar_gain_reduction": 0.0,
        "ventilation_reduction": 0.0,
        "heat_recovery_efficiency": 0.0,
        "pv_capacity_kwp": 0,
        "description": "Current condition — no energy interventions",
        "cost_gbp": 0,
        "installation_months": 0,
    },
    "Solar Glass": {
        "name": "Solar Glass",
        "u_wall_multiplier": 1.0,
        "u_roof_multiplier": 1.0,
        "u_window_multiplier": 0.85,       # modest U-value improvement
        "solar_gain_reduction": 0.15,      # 15% reduction in unwanted solar gain
        "ventilation_reduction": 0.0,
        "heat_recovery_efficiency": 0.0,
        "pv_capacity_kwp": 0,
        "description": "High-performance glazing with low-E coating",
        "cost_gbp_per_m2": 180,            # typical range £120–£250/m²
        "installation_months": 4,
    },
    "Green Roof": {
        "name": "Green Roof",
        "u_wall_multiplier": 1.0,
        "u_roof_multiplier": 0.70,         # improved thermal resistance
        "u_window_multiplier": 1.0,
        "solar_gain_reduction": 0.08,
        "ventilation_reduction": 0.0,
        "heat_recovery_efficiency": 0.0,
        "pv_capacity_kwp": 0,
        "description": "Extensive green roof + improved insulation",
        "cost_gbp_per_m2": 150,            # typical range £100–£200/m²
        "installation_months": 3,
    },
    "Enhanced Insulation": {
        "name": "Enhanced Insulation",
        "u_wall_multiplier": 0.60,         # significant improvement
        "u_roof_multiplier": 0.60,
        "u_window_multiplier": 1.0,
        "solar_gain_reduction": 0.0,
        "ventilation_reduction": 0.0,
        "heat_recovery_efficiency": 0.0,
        "pv_capacity_kwp": 0,
        "description": "External wall insulation (EWI) + roof upgrade",
        "cost_gbp_per_m2": 85,             # typical range £60–£120/m² for EWI
        "installation_months": 6,
    },
    "Combined Package": {
        "name": "Combined Package",
        "u_wall_multiplier": 0.55,         # EWI
        "u_roof_multiplier": 0.60,         # green roof
        "u_window_multiplier": 0.85,       # solar glass
        "solar_gain_reduction": 0.20,
        "ventilation_reduction": 0.15,     # enhanced controls
        "heat_recovery_efficiency": 0.65,  # heat recovery ventilation (HRV)
        "pv_capacity_kwp": 0,              # no PV in this variant
        "description": "Holistic retrofit: EWI + green roof + solar glass + HRV",
        "cost_gbp_per_m2": 220,
        "installation_months": 8,
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# SIMPLIFIED STEADY-STATE THERMAL LOAD CALCULATION
# ─────────────────────────────────────────────────────────────────────────────
def calculate_thermal_load(
    building: Dict[str, Any],
    scenario: Dict[str, Any],
    weather: Dict[str, float],
) -> Dict[str, Any]:
    """
    Calculate annual thermal loads and energy/carbon savings for a building under a scenario.
    
    Args:
        building: Dictionary with U-values, areas, and building characteristics
        scenario: Dictionary with intervention multipliers and performance data
        weather: Dictionary with temperature_c and other climate data
    
    Returns:
        Dictionary with energy, carbon, cost savings and final U-values
    
    Physics model notes:
    - Simplified steady-state balance: Q = U·A·ΔT
    - Annual heating demand estimated from degree-days
    - No dynamic thermal mass effects (simplified)
    - Assumes heating season only (5,800 hr/yr standard)
    """
    
    # Extract weather
    outdoor_temp_c = weather.get("temperature_c", 10.5)  # UK average if not provided
    
    # Temperature difference for heating season
    delta_t = max(0, HEATING_SETPOINT_C - outdoor_temp_c)
    
    # Apply scenario multipliers to U-values
    u_wall_adjusted = building["u_value_wall"] * scenario["u_wall_multiplier"]
    u_roof_adjusted = building["u_value_roof"] * scenario["u_roof_multiplier"]
    u_window_adjusted = building["u_value_window"] * scenario["u_window_multiplier"]
    u_floor_adjusted = building["u_value_floor"]  # floor usually not retrofitted
    
    # Calculate baseline heat loss (W)
    q_wall = u_wall_adjusted * building["wall_area_m2"] * delta_t
    q_roof = u_roof_adjusted * building["roof_area_m2"] * delta_t
    q_window = u_window_adjusted * building["window_area_m2"] * delta_t
    q_floor = u_floor_adjusted * building["floor_area_m2"] * delta_t
    
    # Total transmission heat loss
    q_transmission = q_wall + q_roof + q_window + q_floor  # Watts
    
    # Ventilation heat loss (simplified)
    # Q = ρ·cp·V̇·ΔT, where V̇ = ventilation_rate_ach × volume
    volume_m3 = building["gross_floor_area_m2"] * 3.5  # assume 3.5m floor-to-ceiling
    air_change_rate_m3_s = (building["ventilation_rate_ach"] / 3600) * volume_m3
    q_ventilation = 1.2 * 1006 * air_change_rate_m3_s * delta_t  # ρ·cp for air
    
    # Apply ventilation reduction (e.g., heat recovery)
    q_ventilation *= (1.0 - scenario["ventilation_reduction"])
    
    # Total heating load
    q_total_w = q_transmission + q_ventilation
    
    # Annual energy (baseline scenario)
    baseline_annual_mwh = (q_total_w * HEATING_SEASON_HOURS_PER_YEAR) / 1e6
    
    # If baseline scenario (no intervention), energy_saving = 0
    if scenario["name"] == "Baseline (No Intervention)":
        energy_saving_mwh = 0.0
    else:
        # Calculate baseline (without scenario)
        q_baseline_wall = (building["u_value_wall"] * building["wall_area_m2"] * delta_t)
        q_baseline_roof = (building["u_value_roof"] * building["roof_area_m2"] * delta_t)
        q_baseline_window = (building["u_value_window"] * building["window_area_m2"] * delta_t)
        q_baseline_floor = (building["u_value_floor"] * building["floor_area_m2"] * delta_t)
        q_baseline_transmission = q_baseline_wall + q_baseline_roof + q_baseline_window + q_baseline_floor
        q_baseline_ventilation = 1.2 * 1006 * air_change_rate_m3_s * delta_t
        q_baseline_total = q_baseline_transmission + q_baseline_ventilation
        baseline_annual_mwh = (q_baseline_total * HEATING_SEASON_HOURS_PER_YEAR) / 1e6
        
        energy_saving_mwh = max(0, baseline_annual_mwh - ((q_total_w * HEATING_SEASON_HOURS_PER_YEAR) / 1e6))
    
    # Carbon savings (kgCO2 → tonnes)
    carbon_saving_t = round((energy_saving_mwh * 1000 * CARBON_INTENSITY_KG_CO2_PER_KWH) / 1000, 1)
    
    # Cost savings (£)
    cost_saving_gbp = round(energy_saving_mwh * 1000 * ELECTRICITY_COST_GBP_PER_KWH, 0)
    
    # Payback period (years) — if scenario has cost
    payback_years = None
    if scenario["cost_gbp"] > 0 and cost_saving_gbp > 0:
        payback_years = round(scenario["cost_gbp"] / (cost_saving_gbp / HEATING_SEASON_HOURS_PER_YEAR * 8760), 1)
    elif "cost_gbp_per_m2" in scenario and cost_saving_gbp > 0:
        total_cost = scenario["cost_gbp_per_m2"] * (building["wall_area_m2"] + building["roof_area_m2"])
        payback_years = round(total_cost / (cost_saving_gbp / HEATING_SEASON_HOURS_PER_YEAR * 8760), 1)
    
    return {
        "building_name": "Greenfield Library",  # Placeholder
        "scenario_name": scenario["name"],
        "energy_saving_mwh": energy_saving_mwh,
        "carbon_saving_t": carbon_saving_t,
        "cost_saving_gbp": cost_saving_gbp,
        "payback_years": payback_years,
        "u_wall": u_wall_adjusted,
        "u_roof": u_roof_adjusted,
        "u_window": u_window_adjusted,
        "u_floor": u_floor_adjusted,
        "baseline_annual_mwh": baseline_annual_mwh,
        "source": "CrowAgent™ Simplified PINN Physics Model",
    }
