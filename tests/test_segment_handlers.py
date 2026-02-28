from config.scenarios import SCENARIOS
from app.segments import get_segment_handler, SEGMENT_IDS

def test_all_handlers():
   for sid in SEGMENT_IDS:
       h = get_segment_handler(sid)
       assert len(h.building_registry) > 0
       for name in h.scenario_whitelist:
           assert name in SCENARIOS, f"{sid}: unknown scenario {name}"
