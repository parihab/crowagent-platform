import importlib
from typing import Any

# Lazy loading registry
_MODULE_MAP = {
    "university_he":        ("app.segments.university_he",       "UniversityHEHandler"),
    "smb_landlord":         ("app.segments.commercial_landlord", "CommercialLandlordHandler"),
    "smb_industrial":       ("app.segments.smb_industrial",      "SMBIndustrialHandler"),
    "individual_selfbuild": ("app.segments.individual_selfbuild","IndividualSelfBuildHandler"),
}

SEGMENT_IDS = list(_MODULE_MAP.keys())

SEGMENT_LABELS = {
    "university_he": "🏛️ University / Higher Education",
    "smb_landlord": "🏢 Commercial Landlord",
    "smb_industrial": "🏭 SMB Industrial",
    "individual_selfbuild": "🏠 Individual Self-Build",
}

def get_segment_handler(segment_id: str) -> Any:
    if segment_id not in _MODULE_MAP:
        raise ValueError(f"Unknown segment: {segment_id!r}")
    
    mod_name, cls_name = _MODULE_MAP[segment_id]
    module = importlib.import_module(mod_name)
    cls = getattr(module, cls_name)
    return cls()