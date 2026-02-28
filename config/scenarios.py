"""
Defines all available intervention scenarios and their assignment to segments.

This file contains three main dictionaries:
1.  SCENARIOS: The master dictionary of all possible interventions. Each entry
    details the physical changes (e.g., U-value reductions) and associated
    costs of a given scenario.
2.  SEGMENT_SCENARIOS: A whitelist mapping each customer segment ID to the
    list of scenario keys they are allowed to use.
3.  SEGMENT_DEFAULT_SCENARIOS: The list of scenarios that should be selected
    by default when a user first enters a given segment.
"""

# ─────────────────────────────────────────────────────────────────────────────
# 1. MASTER SCENARIO DEFINITIONS
# ─────────────────────────────────────────────────────────────────────────────
# Each scenario is a dictionary of factors that will be applied to a
# baseline building model.
# - u_..._factor: Multiplier for U-values (lower is better).
# - ..._reduction: Fractional reduction (0.0 to 1.0).
# - renewable_kwh: Direct addition to energy generation.
# - install_cost_gbp: Estimated total cost of the intervention.
# - colour: Plotly hex colour used in scenario comparison charts.
# - icon: Emoji icon used in UI labels and tables.

SCENARIOS = {
    # ── Baseline (no intervention) ────────────────────────────────────────
    "baseline": {
        "display_name": "Baseline (No Intervention)",
        "u_wall_factor": 1.0,
        "u_roof_factor": 1.0,
        "u_glazing_factor": 1.0,
        "infiltration_reduction": 0.0,
        "solar_gain_reduction": 0.0,
        "renewable_kwh": 0,
        "install_cost_gbp": 0,
        "colour": "#4A6FA5",
        "icon": "🏢",
    },

    # ── Fabric-focused upgrades ───────────────────────────────────────────
    "fabric_moderate": {
        "display_name": "Moderate Fabric Upgrade",
        "u_wall_factor": 0.7,
        "u_roof_factor": 0.6,
        "u_glazing_factor": 1.0,
        "infiltration_reduction": 0.1,
        "solar_gain_reduction": 0.0,
        "renewable_kwh": 0,
        "install_cost_gbp": 50000,
        "colour": "#5B8DB8",
        "icon": "🧱",
    },
    "fabric_deep": {
        "display_name": "Deep Fabric Retrofit",
        "u_wall_factor": 0.4,
        "u_roof_factor": 0.3,
        "u_glazing_factor": 0.7,
        "infiltration_reduction": 0.3,
        "solar_gain_reduction": 0.1,
        "renewable_kwh": 0,
        "install_cost_gbp": 120000,
        "colour": "#1A5276",
        "icon": "🏗️",
    },

    # ── Glazing-focused upgrades ──────────────────────────────────────────
    "glazing_advanced": {
        "display_name": "Advanced Glazing (Triple Pane)",
        "u_wall_factor": 1.0,
        "u_roof_factor": 1.0,
        "u_glazing_factor": 0.5,
        "infiltration_reduction": 0.05,
        "solar_gain_reduction": 0.2,
        "renewable_kwh": 0,
        "install_cost_gbp": 40000,
        "colour": "#E9B44C",
        "icon": "🪟",
    },

    # ── Renewable energy generation ───────────────────────────────────────
    "pv_small": {
        "display_name": "Small Solar PV (10 kWp)",
        "u_wall_factor": 1.0,
        "u_roof_factor": 1.0,
        "u_glazing_factor": 1.0,
        "infiltration_reduction": 0.0,
        "solar_gain_reduction": 0.0,
        "renewable_kwh": 10000,
        "install_cost_gbp": 15000,
        "colour": "#F0B429",
        "icon": "☀️",
    },
    "pv_large": {
        "display_name": "Large Solar PV (50 kWp)",
        "u_wall_factor": 1.0,
        "u_roof_factor": 1.0,
        "u_glazing_factor": 1.0,
        "infiltration_reduction": 0.0,
        "solar_gain_reduction": 0.0,
        "renewable_kwh": 50000,
        "install_cost_gbp": 60000,
        "colour": "#E67E22",
        "icon": "🌞",
    },

    # ── Comprehensive package deal ────────────────────────────────────────
    "netzero_ready": {
        "display_name": "Net Zero Ready Package",
        "u_wall_factor": 0.4,
        "u_roof_factor": 0.3,
        "u_glazing_factor": 0.5,
        "infiltration_reduction": 0.4,
        "solar_gain_reduction": 0.2,
        "renewable_kwh": 25000,
        "install_cost_gbp": 180000,
        "colour": "#00C2A8",
        "icon": "🔄",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# 2. SEGMENT-SPECIFIC SCENARIO ASSIGNMENTS
# ─────────────────────────────────────────────────────────────────────────────
SEGMENT_SCENARIOS = {
    "university_he": [
        "baseline",
        "fabric_moderate",
        "fabric_deep",
        "pv_large",
        "netzero_ready",
    ],
    "commercial_landlord": [
        "baseline",
        "fabric_moderate",
        "glazing_advanced",
        "pv_small",
        "pv_large",
        "netzero_ready",
    ],
    "smb_landlord": [
        "baseline",
        "fabric_moderate",
        "glazing_advanced",
        "pv_small",
        "netzero_ready",
    ],
    "smb_industrial": [
        "baseline",
        "fabric_moderate",
        "fabric_deep",
        "pv_large",
    ],
    "individual_selfbuild": [
        "baseline",
        "fabric_deep",
        "glazing_advanced",
        "pv_small",
        "netzero_ready",
    ],
}


# ─────────────────────────────────────────────────────────────────────────────
# 3. DEFAULT SCENARIOS PER SEGMENT
# ─────────────────────────────────────────────────────────────────────────────
SEGMENT_DEFAULT_SCENARIOS = {
    "university_he": ["baseline", "fabric_deep", "pv_large"],
    "commercial_landlord": ["baseline", "fabric_moderate", "pv_small"],
    "smb_landlord": ["baseline", "fabric_moderate"],
    "smb_industrial": ["baseline", "fabric_deep"],
    "individual_selfbuild": ["baseline", "netzero_ready"],
}
