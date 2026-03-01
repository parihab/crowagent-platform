from app.segments.base import SegmentHandler
from config.scenarios import SEGMENT_SCENARIOS, SEGMENT_DEFAULT_SCENARIOS

BUILDINGS = {
    "Warehouse Unit 4": {
        "floor_area_m2": 2000,
        "height_m": 8.0,
        "glazing_ratio": 0.05,
        "u_value_wall": 0.7,
        "u_value_roof": 0.5,
        "u_value_glazing": 3.0,
        "baseline_energy_mwh": 250,
        "occupancy_hours": 4000,
        "building_type": "Warehouse",
        "built_year": 1985,
    }
}

class SMBIndustrialHandler(SegmentHandler):
    segment_id = "smb_industrial"
    display_label = "🏭 SMB Industrial"
    building_registry = BUILDINGS
    scenario_whitelist = SEGMENT_SCENARIOS["smb_industrial"]
    default_scenarios = SEGMENT_DEFAULT_SCENARIOS["smb_industrial"]
    compliance_checks = ["secr", "part_l"]