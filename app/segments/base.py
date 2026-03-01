from abc import ABC, abstractmethod

class SegmentHandler(ABC):
    @property
    @abstractmethod
    def segment_id(self) -> str:
        pass

    @property
    @abstractmethod
    def display_label(self) -> str:
        pass

    @property
    @abstractmethod
    def building_registry(self) -> dict:
        pass

    @property
    @abstractmethod
    def scenario_whitelist(self) -> list[str]:
        pass

    @property
    @abstractmethod
    def default_scenarios(self) -> list[str]:
        pass

    @property
    @abstractmethod
    def compliance_checks(self) -> list[str]:
        pass

    def get_building(self, name: str) -> dict:
        if name not in self.building_registry:
            raise KeyError(f"Building {name!r} not found in {self.segment_id} registry")
        return self.building_registry[name]