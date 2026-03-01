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
    }
}

class IndividualSelfBuildHandler(SegmentHandler):
    segment_id = "individual_selfbuild"
    display_label = "🏠 Individual Self-Build"
    building_registry = BUILDINGS
    scenario_whitelist = SEGMENT_SCENARIOS["individual_selfbuild"]
    default_scenarios = SEGMENT_DEFAULT_SCENARIOS["individual_selfbuild"]
    compliance_checks = ["part_l", "fhs"]