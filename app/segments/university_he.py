from app.segments.base import SegmentHandler
from config.scenarios import SEGMENT_SCENARIOS, SEGMENT_DEFAULT_SCENARIOS

BUILDINGS = {
    "Greenfield Library": {
        "floor_area_m2": 8500,
        "height_m": 18.0,
        "glazing_ratio": 0.40,
        "u_value_wall": 0.35,
        "u_value_roof": 0.25,
        "u_value_glazing": 2.8,
        "baseline_energy_mwh": 1450,
        "occupancy_hours": 3500,
        "building_type": "Library / Resource Centre",
        "built_year": 1995,
    },
    "Greenfield Arts Building": {
        "floor_area_m2": 4200,
        "height_m": 12.0,
        "glazing_ratio": 0.55,
        "u_value_wall": 0.45,
        "u_value_roof": 0.30,
        "u_value_glazing": 2.8,
        "baseline_energy_mwh": 680,
        "occupancy_hours": 2800,
        "building_type": "Teaching / Studio",
        "built_year": 1988,
    },
    "Greenfield Science Block": {
        "floor_area_m2": 12500,
        "height_m": 24.0,
        "glazing_ratio": 0.30,
        "u_value_wall": 0.28,
        "u_value_roof": 0.20,
        "u_value_glazing": 1.8,
        "baseline_energy_mwh": 3200,
        "occupancy_hours": 4000,
        "building_type": "Lab / Research",
        "built_year": 2005,
    },
}

class UniversityHEHandler(SegmentHandler):
    segment_id = "university_he"
    display_label = "🏛️ University / Higher Education"
    building_registry = BUILDINGS
    scenario_whitelist = SEGMENT_SCENARIOS["university_he"]
    default_scenarios = SEGMENT_DEFAULT_SCENARIOS["university_he"]
    compliance_checks = ["epc_mees"]