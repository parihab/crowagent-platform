"""
Defines the abstract base class for all segment handlers.
"""

from __future__ import annotations
import abc
from typing import Any

class SegmentHandler(abc.ABC):
    """
    Abstract base class for all segment-specific logic.

    Each subclass is responsible for defining the buildings, scenarios, and
    compliance checks relevant to its specific customer segment. This class
    defines the contract that all segment handlers must follow.
    """

    @property
    @abc.abstractmethod
    def segment_id(self) -> str:
        """A unique machine-readable identifier for the segment (e.g., 'university_he')."""
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def display_label(self) -> str:
        """The user-facing name of the segment (e.g., '🏛️ University / Higher Education')."""
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def building_registry(self) -> dict[str, dict[str, Any]]:
        """A dictionary of building templates available for this segment."""
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def scenario_whitelist(self) -> list[str]:
        """A list of scenario keys (from config.scenarios) applicable to this segment."""
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def default_scenarios(self) -> list[str]:
        """The list of scenario keys that should be selected by default for this segment."""
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def compliance_checks(self) -> list[str]:
        """A list of compliance check identifiers used by the Compliance Hub tab."""
        raise NotImplementedError

    def get_building(self, name: str) -> dict[str, Any]:
        """
        Retrieves a building template from the registry by its name.

        Args:
            name: The key of the building to retrieve from the registry.

        Returns:
            The building data dictionary.

        Raises:
            KeyError: If the building name is not found in this segment's registry,
                      providing a helpful error message.
        """
        try:
            return self.building_registry[name]
        except KeyError:
            raise KeyError(
                f"Building '{name}' not found in segment '{self.segment_id}'. "
                f"Available buildings: {list(self.building_registry.keys())}"
            )
