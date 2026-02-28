from config.scenarios import SCENARIOS
from app.segments import get_segment_handler, SEGMENT_IDS

def test_all_handlers():
    """Smoke test to ensure all segment handlers instantiate and have valid configuration."""
    for sid in SEGMENT_IDS:
        h = get_segment_handler(sid)
        assert len(h.building_registry) > 0, f"{sid}: empty building registry"
        for name in h.scenario_whitelist:
            assert name in SCENARIOS, f"{sid}: unknown scenario {name}"