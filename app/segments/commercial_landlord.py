from app.segments.base import SegmentHandler
from config.scenarios import SEGMENT_SCENARIOS, SEGMENT_DEFAULT_SCENARIOS

BUILDINGS = {
    "Retail Unit 1": {
        "floor_area_m2": 250,
        "height_m": 4.0,
        "glazing_ratio": 0.80,
        "u_value_wall": 0.6,
        "u_value_roof": 0.4,
        "u_value_glazing": 2.8,
        "baseline_energy_mwh": 45,
        "occupancy_hours": 3000,
        "building_type": "Retail",
        "built_year": 1990,
    },
    "Office Block A": {
        "floor_area_m2": 1200,
        "height_m": 12.0,
        "glazing_ratio": 0.40,
        "u_value_wall": 0.45,
        "u_value_roof": 0.3,
        "u_value_glazing": 2.2,
        "baseline_energy_mwh": 180,
        "occupancy_hours": 2500,
        "building_type": "Office",
        "built_year": 2000,
    },
    "Meridian House": {
        "floor_area_m2": 2400,
        "height_m": 14.0,
        "glazing_ratio": 0.45,
        "u_value_wall": 0.55,
        "u_value_roof": 0.35,
        "u_value_glazing": 2.4,
        "baseline_energy_mwh": 380,
        "occupancy_hours": 2600,
        "building_type": "Office",
        "built_year": 1999,
    },
    "Riverside Retail Park — Unit 3": {
        "floor_area_m2": 680,
        "height_m": 5.0,
        "glazing_ratio": 0.70,
        "u_value_wall": 0.65,
        "u_value_roof": 0.42,
        "u_value_glazing": 2.9,
        "baseline_energy_mwh": 95,
        "occupancy_hours": 3200,
        "building_type": "Retail",
        "built_year": 2003,
    },
    "The Granary Business Centre": {
        "floor_area_m2": 1150,
        "height_m": 8.0,
        "glazing_ratio": 0.30,
        "u_value_wall": 0.90,
        "u_value_roof": 0.55,
        "u_value_glazing": 3.2,
        "baseline_energy_mwh": 165,
        "occupancy_hours": 2000,
        "building_type": "Mixed-Use",
        "built_year": 1987,
    },
}

class CommercialLandlordHandler(SegmentHandler):
    segment_id = "smb_landlord"
    display_label = "🏢 Commercial Landlord"
    building_registry = BUILDINGS
    scenario_whitelist = SEGMENT_SCENARIOS["smb_landlord"]
    default_scenarios = SEGMENT_DEFAULT_SCENARIOS["smb_landlord"]
    compliance_checks = ["epc_mees", "part_l"]
