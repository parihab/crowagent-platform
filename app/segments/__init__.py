"""
This package contains the logic for different customer segments.

The __init__.py file acts as a public interface, exporting a factory function
(get_segment_handler) to retrieve the correct handler class for a given
segment ID. It also defines the canonical list of segment IDs and their
display labels.

This setup uses lazy loading via importlib to avoid importing all segment
modules on startup, which can speed up cold-start times.
"""

import importlib
from typing import TYPE_CHECKING

# Use TYPE_CHECKING to avoid circular import at runtime
if TYPE_CHECKING:
    from .base import SegmentHandler

# Define the canonical segment identifiers and their display labels
SEGMENT_IDS = [
    "university_he",
    "commercial_landlord",
    "smb_industrial",
    "individual_selfbuild",
]

SEGMENT_LABELS = {
    "university_he": "🏛️ University / Higher Education",
    "commercial_landlord": "🏢 Commercial Landlord",
    "smb_industrial": "🏭 SMB Industrial",
    "individual_selfbuild": "🏠 Individual Self-Build",
}

# The registry maps segment IDs to the relative path of their handler classes.
# This allows for lazy loading.
_REGISTRY = {
    "university_he": ".university_he.UniversityHEHandler",
    "commercial_landlord": ".commercial_landlord.CommercialLandlordHandler",
    "smb_industrial": ".smb_industrial.SMBIndustrialHandler",
    "individual_selfbuild": ".individual_selfbuild.IndividualSelfBuildHandler",
}

def get_segment_handler(segment_id: str) -> "SegmentHandler":
    """
    Lazily imports and returns an instance of the appropriate segment handler.

    This function acts as a factory. Based on the segment_id, it dynamically
    imports the necessary module and instantiates the handler class within it.

    Args:
        segment_id: The identifier for the desired customer segment.

    Returns:
        An instance of the corresponding SegmentHandler subclass.

    Raises:
        ValueError: If the segment_id is not found in the registry.
    """
    if segment_id not in _REGISTRY:
        raise ValueError(f"Unknown segment: {segment_id!r}")

    module_path, class_name = _REGISTRY[segment_id].rsplit('.', 1)

    # Lazily import the required module relative to the current package
    try:
        module = importlib.import_module(module_path, package=__package__)
    except ImportError as e:
        raise ImportError(f"Could not import module for segment '{segment_id}'. {e}")

    # Get the handler class from the imported module
    try:
        handler_class = getattr(module, class_name)
    except AttributeError:
        raise AttributeError(f"Could not find class '{class_name}' in module '{module_path}'")

    # Return an instance of the handler
    return handler_class()
