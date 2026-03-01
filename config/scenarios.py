"""
Scenario definitions and segment whitelists.
"""

SCENARIOS = {
    "Baseline (No Intervention)": {
        "u_wall_factor": 1.0, "u_roof_factor": 1.0, "u_glazing_factor": 1.0,
        "solar_gain_reduction": 0.0, "infiltration_reduction": 0.0,
        "renewable_kwh": 0.0, "install_cost_gbp": 0.0, "colour": "#5A7A90"
    },
    "Fabric Upgrade (Insulation)": {
        "u_wall_factor": 0.6, "u_roof_factor": 0.5, "u_glazing_factor": 1.0,
        "solar_gain_reduction": 0.0, "infiltration_reduction": 0.2,
        "renewable_kwh": 0.0, "install_cost_gbp": 25000.0, "colour": "#00C2A8"
    },
    "Glazing Upgrade": {
        "u_wall_factor": 1.0, "u_roof_factor": 1.0, "u_glazing_factor": 0.4,
        "solar_gain_reduction": 0.1, "infiltration_reduction": 0.1,
        "renewable_kwh": 0.0, "install_cost_gbp": 15000.0, "colour": "#F0B429"
    },
    "Renewables (Solar PV)": {
        "u_wall_factor": 1.0, "u_roof_factor": 1.0, "u_glazing_factor": 1.0,
        "solar_gain_reduction": 0.0, "infiltration_reduction": 0.0,
        "renewable_kwh": 5000.0, "install_cost_gbp": 8000.0, "colour": "#E84C4C"
    },
    "Deep Retrofit (All Interventions)": {
        "u_wall_factor": 0.5, "u_roof_factor": 0.4, "u_glazing_factor": 0.4,
        "solar_gain_reduction": 0.1, "infiltration_reduction": 0.4,
        "renewable_kwh": 5000.0, "install_cost_gbp": 48000.0, "colour": "#9B59B6"
    }
}

SEGMENT_SCENARIOS = {
    "university_he": list(SCENARIOS.keys()),
    "smb_landlord": list(SCENARIOS.keys()),
    "smb_industrial": list(SCENARIOS.keys()),
    "individual_selfbuild": list(SCENARIOS.keys()),
}

SEGMENT_DEFAULT_SCENARIOS = {
    "university_he": ["Baseline (No Intervention)", "Deep Retrofit (All Interventions)"],
    "smb_landlord": ["Baseline (No Intervention)", "Fabric Upgrade (Insulation)"],
    "smb_industrial": ["Baseline (No Intervention)", "Renewables (Solar PV)"],
    "individual_selfbuild": ["Baseline (No Intervention)", "Deep Retrofit (All Interventions)"],
}