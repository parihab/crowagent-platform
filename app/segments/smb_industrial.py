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
    },
    "Kingfisher Distribution Centre": {
        "floor_area_m2": 4800,
        "height_m": 10.0,
        "glazing_ratio": 0.06,
        "u_value_wall": 0.75,
        "u_value_roof": 0.55,
        "u_value_glazing": 3.0,
        "baseline_energy_mwh": 580,
        "occupancy_hours": 4200,
        "building_type": "Distribution",
        "built_year": 1992,
    },
    "Parkside Manufacturing Unit 7": {
        "floor_area_m2": 2100,
        "height_m": 8.0,
        "glazing_ratio": 0.08,
        "u_value_wall": 0.60,
        "u_value_roof": 0.48,
        "u_value_glazing": 3.1,
        "baseline_energy_mwh": 290,
        "occupancy_hours": 3800,
        "building_type": "Manufacturing",
        "built_year": 2001,
    },
    "Apex Logistics Hub — Bay 2": {
        "floor_area_m2": 3600,
        "height_m": 9.0,
        "glazing_ratio": 0.05,
        "u_value_wall": 0.85,
        "u_value_roof": 0.60,
        "u_value_glazing": 3.3,
        "baseline_energy_mwh": 420,
        "occupancy_hours": 5000,
        "building_type": "Logistics",
        "built_year": 1978,
    },
}

class SMBIndustrialHandler(SegmentHandler):
    segment_id = "smb_industrial"
    display_label = "🏭 SMB Industrial"
    building_registry = BUILDINGS
    scenario_whitelist = SEGMENT_SCENARIOS["smb_industrial"]
    default_scenarios = SEGMENT_DEFAULT_SCENARIOS["smb_industrial"]
    compliance_checks = ["secr", "part_l"]
