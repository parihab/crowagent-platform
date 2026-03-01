from app.segments.base import SegmentHandler
from config.scenarios import SEGMENT_SCENARIOS, SEGMENT_DEFAULT_SCENARIOS

BUILDINGS = {
    "Detached House": {
        "floor_area_m2": 150,
        "height_m": 6.0,
        "glazing_ratio": 0.25,
        "u_value_wall": 1.2,
        "u_value_roof": 0.8,
        "u_value_glazing": 2.8,
        "baseline_energy_mwh": 25,
        "occupancy_hours": 5000,
        "building_type": "Residential",
        "built_year": 1970,
    },
    "14 Ashwood Close": {
        "floor_area_m2": 165,
        "height_m": 6.0,
        "glazing_ratio": 0.22,
        "u_value_wall": 1.40,
        "u_value_roof": 0.90,
        "u_value_glazing": 2.8,
        "baseline_energy_mwh": 28,
        "occupancy_hours": 5500,
        "building_type": "Detached",
        "built_year": 1967,
    },
    "7 Millbrook Lane": {
        "floor_area_m2": 98,
        "height_m": 5.5,
        "glazing_ratio": 0.18,
        "u_value_wall": 1.60,
        "u_value_roof": 1.10,
        "u_value_glazing": 3.0,
        "baseline_energy_mwh": 19,
        "occupancy_hours": 5800,
        "building_type": "Semi-Detached",
        "built_year": 1952,
    },
    "Bramble Cottage": {
        "floor_area_m2": 210,
        "height_m": 5.0,
        "glazing_ratio": 0.15,
        "u_value_wall": 1.80,
        "u_value_roof": 1.30,
        "u_value_glazing": 3.2,
        "baseline_energy_mwh": 38,
        "occupancy_hours": 6000,
        "building_type": "Detached",
        "built_year": 1935,
    },
}

class IndividualSelfBuildHandler(SegmentHandler):
    segment_id = "individual_selfbuild"
    display_label = "🏠 Individual Self-Build"
    building_registry = BUILDINGS
    scenario_whitelist = SEGMENT_SCENARIOS["individual_selfbuild"]
    default_scenarios = SEGMENT_DEFAULT_SCENARIOS["individual_selfbuild"]
    compliance_checks = ["part_l", "fhs"]
