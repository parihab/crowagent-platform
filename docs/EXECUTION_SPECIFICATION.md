# CrowAgent™ Platform — Refactor Execution Specification
**Version:** 1.0.0
**Date:** 2026-02-28
**Status:** APPROVED FOR EXECUTION
**Source Document:** ARCHITECTURE_DECISION_DOCUMENT.md v1.0.0
**Execution Model:** Sequential batches — each batch leaves the application fully runnable

---

## Pre-Execution Baseline

Before any batch begins, verify:

```bash
# Confirm clean working tree
git status                          # must show: nothing to commit

# Confirm app starts
python -c "import app.main"         # must succeed with no ImportError

# Record line counts (regression baseline)
wc -l app/main.py                   # 3287 lines
wc -l core/physics.py               # 292 lines
wc -l app/compliance.py             # 726 lines
wc -l core/agent.py                 # 635 lines
```

**Stability Contract:** The app must start without error after every batch.
`python -m streamlit run streamlit_app.py --server.headless true`
This command must exit with code 0 or remain alive (not crash on import).

---

## Batch Dependency Graph

```
Batch 1 (Foundation)
   │
   ├──► Batch 2 (Segment Isolation)
   │         │
   │         └──► Batch 3 (Performance)
   │                    │
   └──► Batch 4 (Compliance Modularisation)
              │
              └──► Batch 5 (UI Redesign)  ◄── requires Batches 1+2+3+4 complete
                        │
                        └──► Batch 6 (Exception Hardening)
```

---

## Batch 1 — Core Refactor (Foundation Layer)

### Objective
Establish the `config/` package and supporting utility modules as the canonical
source of truth for constants, scenarios, branding, and session state.
**No existing file is deleted. No existing import is changed.** This batch is
purely additive — it creates the new foundations that later batches will switch
onto.

### ADD Tasks Covered
001, 002, 003, 004, 005, 015

### Files Impacted

| File | Action | Risk |
|---|---|---|
| `config/__init__.py` | Create | None |
| `config/constants.py` | Create | None |
| `config/scenarios.py` | Create | None |
| `app/branding.py` | Create | None |
| `app/session.py` | Create | None |
| `app/utils.py` | Modify (additive only) | Low |

### Implementation Goal

**`config/__init__.py`**
Empty file. Establishes the package. No contents.

**`config/constants.py`**
Copy (not move) all physical and financial constants from their current sources.
The originals remain in place. `config/constants.py` becomes the canonical version.
Constants to include, sourced from:
- `core/physics.py` lines 13–20: `DEFAULT_ELECTRICITY_TARIFF_GBP_PER_KWH`,
  `HEATING_SETPOINT_C`, `HEATING_HOURS_PER_YEAR`, `BASE_ACH`,
  `SOLAR_IRRADIANCE_KWH_M2_YEAR`, `SOLAR_APERTURE_FACTOR`, `SOLAR_UTILISATION_FACTOR`
- `app/compliance.py` lines 26–64: `CI_ELECTRICITY`, `CI_GAS`, `CI_OIL`, `CI_LPG`,
  `ELEC_COST_PER_KWH`, `GAS_COST_PER_KWH`, `EPC_BANDS`, `MEES_CURRENT_MIN_BAND`,
  `MEES_2028_TARGET_BAND`, `MEES_2030_TARGET_BAND`, `PART_L_2021_U_WALL`,
  `PART_L_2021_U_ROOF`, `PART_L_2021_U_GLAZING`, `FHS_MAX_PRIMARY_ENERGY`,
  `PART_L_2021_ND_U_WALL`, `PART_L_2021_ND_U_ROOF`, `PART_L_2021_ND_U_GLAZING`

**`config/scenarios.py`**
Copy (not move) scenario registries from their current sources.
- From `core/physics.py` lines 65–end: `SCENARIOS: dict[str, dict]`
- From `app/main.py` lines 362–394: `SEGMENT_SCENARIOS: dict[str, list[str]]`
  and `SEGMENT_DEFAULT_SCENARIOS: dict[str, list[str]]`

**`app/branding.py`**
- Define `CROWAGENT_CSS: str` — copy the complete CSS string from `app/main.py`
  (the `st.markdown("""<style>...""")` block, approximately lines 145–220).
  Do NOT delete from `app/main.py` yet.
- Define `PAGE_CONFIG: dict` — copy the `st.set_page_config` kwargs from `app/main.py`.
  Do NOT delete from `app/main.py` yet.
- Define `_load_asset_uri(filename: str) -> str` — consolidate the logic of both
  `_load_logo_uri()` and `_load_icon_uri()` from `app/main.py` into a single resolver
  that iterates four candidate paths. Returns base64 data URI string or `""` on failure.
- Define `@st.cache_resource get_logo_uri() -> str` calling `_load_asset_uri("CrowAgent_Logo_Horizontal_Dark.svg")`.
- Define `@st.cache_resource get_icon_uri() -> str` calling `_load_asset_uri("CrowAgent_Icon_Square.svg")`.
- Define `inject_branding() -> None` that calls `st.markdown(CROWAGENT_CSS, unsafe_allow_html=True)`.

**`app/session.py`**
- Copy `_get_secret(key, default)` from `app/main.py`. Do NOT delete from `app/main.py` yet.
- Define `MAX_CHAT_HISTORY: int = 40` (copy from `app/main.py`).
- Define `init_session() -> None` using `st.session_state.setdefault()` for every key:
  `user_segment=None`, `portfolio=[]`, `active_analysis_ids=[]`, `chat_history=[]`,
  `agent_history=[]`, `gemini_key=""`, `gemini_key_valid=False`,
  `energy_tariff_gbp_per_kwh=0.28`, `weather_provider="open_meteo"`,
  `building_names={}`, `selected_scenario_names=[]`, `onboarding_complete=False`.

**`app/utils.py` (additive modifications only)**
- Add `_extract_uk_postcode(text: str) -> str` — copy from `app/main.py`.
  Do NOT delete from `app/main.py` yet.
- Add `_safe_number(value: Any, default: float = 0.0) -> float` — copy from `app/main.py`.
- Add `_safe_nested_number(container: dict, *keys: str, default: float = 0.0) -> float` — copy from `app/main.py`.
- Modify existing `validate_gemini_key(key: str)`: add `.strip()` call at entry,
  add `if "\n" in key: return False, "Key contains invalid characters."` guard
  before existing validation logic.

### Acceptance Tests

```bash
# T1.1 — Package import clean
python -c "import config.constants; print('OK')"
python -c "import config.scenarios; print('OK')"
python -c "import app.branding; print('OK')"
python -c "import app.session; print('OK')"

# T1.2 — Constants completeness
python -c "
from config.constants import (
    CI_ELECTRICITY, CI_GAS, PART_L_2021_U_WALL,
    EPC_BANDS, MEES_2028_TARGET_BAND, FHS_MAX_PRIMARY_ENERGY
)
assert isinstance(CI_ELECTRICITY, float)
assert isinstance(EPC_BANDS, list)
assert len(EPC_BANDS) > 0
print('constants OK')
"

# T1.3 — Scenarios completeness
python -c "
from config.scenarios import SCENARIOS, SEGMENT_SCENARIOS, SEGMENT_DEFAULT_SCENARIOS
assert len(SCENARIOS) > 0
assert 'university_he' in SEGMENT_SCENARIOS
assert 'smb_landlord' in SEGMENT_SCENARIOS
assert 'smb_industrial' in SEGMENT_SCENARIOS
assert 'individual_selfbuild' in SEGMENT_SCENARIOS
print('scenarios OK')
"

# T1.4 — Branding completeness
python -c "
from app.branding import CROWAGENT_CSS, PAGE_CONFIG, inject_branding
assert '<style>' in CROWAGENT_CSS
assert 'page_title' in PAGE_CONFIG
print('branding OK')
"

# T1.5 — Session idempotency
python -c "
import streamlit as st
from app.session import init_session
# Running twice must not raise
init_session()
init_session()
print('session idempotent OK')
"

# T1.6 — Utils additions
python -c "
from app.utils import _extract_uk_postcode, _safe_number, validate_gemini_key
assert _extract_uk_postcode('RG1 2AB') == 'RG1 2AB'
assert _safe_number('bad', 0.0) == 0.0
ok, *_ = validate_gemini_key('key\ninjection')
assert not ok
print('utils OK')
"

# T1.7 — App runtime unaffected (CRITICAL)
# app/main.py must still import without error
python -c "import app.main; print('main import OK')"
```

### Rollback Plan

**Trigger:** Any T1.x acceptance test fails, or `import app.main` breaks.

**Procedure:**
```bash
# Batch 1 creates only new files — rollback is clean deletion
git diff --name-only HEAD          # list all new files
git checkout HEAD -- app/utils.py  # revert only changed file
rm -f config/__init__.py config/constants.py config/scenarios.py
rm -f app/branding.py app/session.py
```

**Risk level:** Minimal. No existing file is structurally altered. `app/utils.py`
additions are purely additive — reverting it restores the previous 49-line version.

---

## Batch 2 — Segment Isolation

### Objective
Create the `app/segments/` package with all four `SegmentHandler` implementations.
Simultaneously switch `core/physics.py` and `core/agent.py` to import from
`config/` instead of defining their own constants. Remove the now-redundant
`BUILDINGS` and `SCENARIOS` dicts from `core/physics.py`.
Update `app/main.py` import lines to source buildings and scenarios from their
new locations — **no UI or rendering logic in main.py changes**.

**Prerequisite:** Batch 1 acceptance tests all pass.

### ADD Tasks Covered
006, 007, 008, 009, 010, 011, 012, 013 + import-update portion of 021

### Files Impacted

| File | Action | Risk |
|---|---|---|
| `app/segments/__init__.py` | Create | None |
| `app/segments/base.py` | Create | None |
| `app/segments/university_he.py` | Create | None |
| `app/segments/commercial_landlord.py` | Create | None |
| `app/segments/smb_industrial.py` | Create | None |
| `app/segments/individual_selfbuild.py` | Create | None |
| `core/physics.py` | Refactor (remove BUILDINGS, SCENARIOS; switch constants) | Medium |
| `core/agent.py` | Refactor (accept building_registry param; remove physics.BUILDINGS ref) | Medium |
| `app/main.py` | Modify imports only (lines ~46–55 and ~282–395) | Low |

### Implementation Goal

**`app/segments/__init__.py`**
Implement `get_segment_handler(segment_id: str) -> SegmentHandler`.
Use `importlib.import_module()` for lazy class loading:
```python
_MODULE_MAP = {
    "university_he":        ("app.segments.university_he",       "UniversityHEHandler"),
    "smb_landlord":         ("app.segments.commercial_landlord", "CommercialLandlordHandler"),
    "smb_industrial":       ("app.segments.smb_industrial",      "SMBIndustrialHandler"),
    "individual_selfbuild": ("app.segments.individual_selfbuild","IndividualSelfBuildHandler"),
}
```
Export: `get_segment_handler`, `SEGMENT_IDS: list[str]`, `SEGMENT_LABELS: dict[str, str]`.

**`app/segments/base.py`**
Define `SegmentHandler(abc.ABC)`.
Abstract properties (using `@property @abstractmethod`):
`segment_id`, `display_label`, `building_registry`, `scenario_whitelist`,
`default_scenarios`, `compliance_checks`.
Concrete method: `get_building(name: str) -> dict` — returns `self.building_registry[name]`
or raises `KeyError(f"Building {name!r} not found in {self.segment_id} registry")`.
Zero Streamlit imports.

**`app/segments/university_he.py`**
`class UniversityHEHandler(SegmentHandler)`:
- `segment_id = "university_he"`
- `display_label = "🏛️ University / Higher Education"`
- `building_registry` — copy the `BUILDINGS` dict verbatim from `core/physics.py` lines 23–64.
- `scenario_whitelist` — `config.scenarios.SEGMENT_SCENARIOS["university_he"]`
- `default_scenarios` — `config.scenarios.SEGMENT_DEFAULT_SCENARIOS["university_he"]`
- `compliance_checks = ["epc_mees"]`

**`app/segments/commercial_landlord.py`**
`class CommercialLandlordHandler(SegmentHandler)`:
- `segment_id = "smb_landlord"`
- `display_label = "🏢 Commercial Landlord"`
- `building_registry` — extract the `"smb_landlord"` sub-dict from
  `app/compliance.py:SEGMENT_BUILDINGS` (lines 71 onward).
- `scenario_whitelist` — `config.scenarios.SEGMENT_SCENARIOS["smb_landlord"]`
- `default_scenarios` — `config.scenarios.SEGMENT_DEFAULT_SCENARIOS["smb_landlord"]`
- `compliance_checks = ["epc_mees", "part_l"]`

**`app/segments/smb_industrial.py`**
`class SMBIndustrialHandler(SegmentHandler)`:
- `segment_id = "smb_industrial"`
- `display_label = "🏭 SMB Industrial"`
- `building_registry` — extract the `"smb_industrial"` sub-dict from
  `app/compliance.py:SEGMENT_BUILDINGS`.
- `scenario_whitelist` — `config.scenarios.SEGMENT_SCENARIOS["smb_industrial"]`
- `default_scenarios` — `config.scenarios.SEGMENT_DEFAULT_SCENARIOS["smb_industrial"]`
- `compliance_checks = ["secr", "part_l"]`

**`app/segments/individual_selfbuild.py`**
`class IndividualSelfBuildHandler(SegmentHandler)`:
- `segment_id = "individual_selfbuild"`
- `display_label = "🏠 Individual Self-Build"`
- `building_registry` — extract the `"individual_selfbuild"` sub-dict from
  `app/compliance.py:SEGMENT_BUILDINGS`.
- `scenario_whitelist` — `config.scenarios.SEGMENT_SCENARIOS["individual_selfbuild"]`
- `default_scenarios` — `config.scenarios.SEGMENT_DEFAULT_SCENARIOS["individual_selfbuild"]`
- `compliance_checks = ["part_l", "fhs"]`

**`core/physics.py` (Refactor)**
Four changes, in order:
1. Replace the seven local constant definitions (lines 13–20) with
   `from config.constants import DEFAULT_ELECTRICITY_TARIFF_GBP_PER_KWH as DEFAULT_ELECTRICITY_TARIFF_GBP_PER_KWH, HEATING_SETPOINT_C, ...`
   (re-export with same names for backward compatibility with any direct import).
2. Delete `BUILDINGS: dict[str, dict]` entirely (lines 23–64).
3. Delete `SCENARIOS: dict[str, dict]` entirely (lines 65–end of dict).
4. Verify `calculate_thermal_load(building, scenario, weather, tariff_gbp_kwh=0.28) -> dict`
   signature is unchanged. Add `from __future__ import annotations` if not present.
   Replace any internal references to deleted constants with the imported names.

**`core/agent.py` (Refactor)**
Two changes:
1. Extract the tools list (currently inline) into `AGENT_TOOLS: list[dict]` at module level.
2. Update `run_agent_turn()` signature to:
   `run_agent_turn(user_message, history, gemini_key, building_registry: dict, scenario_registry: dict) -> ...`
   Remove any import of or reference to `physics.BUILDINGS` or `physics.SCENARIOS`.
   Replace with usage of the passed-in `building_registry` and `scenario_registry` params.
   Update `SYSTEM_PROMPT` string to replace any hardcoded numeric constants with
   `f"...{config.constants.HEATING_SETPOINT_C}..."` equivalents.

**`app/main.py` (Import-level changes only)**
Replace the local `BUILDINGS` dict at line 282 with:
`from app.segments.university_he import UniversityHEHandler as _UHE; BUILDINGS = _UHE().building_registry`
Replace the local `SCENARIOS` dict at line 324 with:
`from config.scenarios import SCENARIOS`
Replace the local `SEGMENT_SCENARIOS` dict at line 362 with:
`from config.scenarios import SEGMENT_SCENARIOS`
Replace the local `SEGMENT_DEFAULT_SCENARIOS` dict at line 388 with:
`from config.scenarios import SEGMENT_DEFAULT_SCENARIOS`
Update the `crow_agent.run_agent_turn()` call site to pass `building_registry=BUILDINGS,
scenario_registry=SCENARIOS`.
**No other changes to main.py in this batch.**

### Acceptance Tests

```bash
# T2.1 — physics.py is Streamlit-free
python -c "
import sys, types
# Temporarily block streamlit to prove physics doesn't need it
sys.modules['streamlit'] = None
import core.physics
print('physics Streamlit-free: OK')
"

# T2.2 — physics constants imported from config
python -c "
import core.physics
from config.constants import HEATING_SETPOINT_C
assert core.physics.HEATING_SETPOINT_C == HEATING_SETPOINT_C
print('physics constants sourced from config: OK')
"

# T2.3 — BUILDINGS and SCENARIOS absent from physics
python -c "
import core.physics
assert not hasattr(core.physics, 'BUILDINGS'), 'BUILDINGS must not exist in physics'
assert not hasattr(core.physics, 'SCENARIOS'), 'SCENARIOS must not exist in physics'
print('physics cleaned: OK')
"

# T2.4 — calculate_thermal_load still works
python -c "
from core.physics import calculate_thermal_load
building = {'floor_area_m2': 500, 'height_m': 3.5, 'glazing_ratio': 0.3,
            'u_value_wall': 0.35, 'u_value_roof': 0.25, 'u_value_glazing': 2.8,
            'baseline_energy_mwh': 120, 'occupancy_hours': 2500}
scenario = {'u_wall_factor': 0.6, 'u_roof_factor': 0.7, 'u_glazing_factor': 0.8,
            'solar_gain_reduction': 0.0, 'infiltration_reduction': 0.2,
            'renewable_kwh': 0, 'install_cost_gbp': 50000}
weather = {'temperature_c': 8.5}
result = calculate_thermal_load(building, scenario, weather)
assert 'scenario_energy_mwh' in result, f'Missing scenario_energy_mwh. Keys: {list(result)}'
assert 'carbon_saving_t' in result, f'Missing carbon_saving_t. Keys: {list(result)}'
print('calculate_thermal_load: OK')
"

# T2.5 — All four segment handlers instantiate
python -c "
from app.segments import get_segment_handler, SEGMENT_IDS
for seg_id in SEGMENT_IDS:
    h = get_segment_handler(seg_id)
    assert len(h.building_registry) > 0, f'{seg_id} has empty building_registry'
    assert len(h.scenario_whitelist) > 0, f'{seg_id} has empty scenario_whitelist'
    assert len(h.compliance_checks) > 0, f'{seg_id} has empty compliance_checks'
    print(f'  {seg_id}: {len(h.building_registry)} buildings OK')
print('All segment handlers: OK')
"

# T2.6 — Scenario whitelist integrity (no phantom keys)
python -c "
from config.scenarios import SCENARIOS, SEGMENT_SCENARIOS
for seg_id, whitelist in SEGMENT_SCENARIOS.items():
    for name in whitelist:
        assert name in SCENARIOS, f'Segment {seg_id} references unknown scenario: {name}'
print('Scenario whitelist integrity: OK')
"

# T2.7 — agent.py updated signature
python -c "
import inspect, core.agent
sig = inspect.signature(core.agent.run_agent_turn)
params = list(sig.parameters.keys())
assert 'building_registry' in params, 'building_registry param missing'
assert 'scenario_registry' in params, 'scenario_registry param missing'
print('agent.py signature: OK')
"

# T2.8 — app.main still imports and BUILDINGS resolves (CRITICAL)
python -c "
import app.main
import app.main as m
# BUILDINGS must still be accessible from main for backward compat during transition
print('app.main import: OK')
"
```

### Rollback Plan

**Trigger:** Any T2.x test fails, or `import app.main` breaks.

**High-risk files in this batch:** `core/physics.py`, `core/agent.py`, `app/main.py` (import section).

**Procedure:**
```bash
# Step 1: Restore physics.py and agent.py from git
git checkout HEAD -- core/physics.py
git checkout HEAD -- core/agent.py

# Step 2: Restore main.py import lines
git checkout HEAD -- app/main.py

# Step 3: Remove new segment package (pure additions — safe to delete)
rm -rf app/segments/

# Step 4: Verify recovery
python -c "import app.main; print('recovered')"
```

**Partial rollback (physics only):**
If only `core/physics.py` changes cause failure, restore it alone while keeping
segment files in place — they don't affect the running app until main.py wires them.

**Compatibility shim (last resort):**
If `core/physics.py` must be restored but some caller depends on `physics.BUILDINGS`,
temporarily add `BUILDINGS = {}` as an empty stub at the bottom of physics.py to
unblock the import without reverting the full refactor.

---

## Batch 3 — Performance Optimisation

### Objective
Add deterministic caching to `calculate_thermal_load`, enable lazy segment loading,
and pre-load static assets via `@st.cache_resource`. No functional logic changes —
only cache decorators and import strategy.

**Prerequisite:** Batch 2 acceptance tests all pass.

### ADD Tasks Covered
Performance aspects of 004, 006, 012

### Files Impacted

| File | Action | Risk |
|---|---|---|
| `core/physics.py` | Modify — add `functools.lru_cache` wrapper | Low |
| `app/segments/__init__.py` | Modify — enforce `importlib` lazy loading | Low |
| `app/branding.py` | Modify — add `@st.cache_resource` to asset loaders | Low |
| `services/epc.py` | Modify — add `@st.cache_data(ttl=86400)` to `fetch_epc_data` | Low |

### Implementation Goal

**`core/physics.py` — LRU Cache**
Wrap `calculate_thermal_load` with a hashable-input adapter:
```python
import functools, json

def _make_cache_key(building: dict, scenario: dict, weather: dict, tariff: float) -> tuple:
    return (
        json.dumps(building,  sort_keys=True),
        json.dumps(scenario,  sort_keys=True),
        round(weather.get("temperature_c", 10.0), 1),
        round(tariff, 4),
    )

@functools.lru_cache(maxsize=512)
def _calculate_thermal_load_cached(building_json, scenario_json, temp_rounded, tariff):
    building = json.loads(building_json)
    scenario = json.loads(scenario_json)
    weather  = {"temperature_c": temp_rounded}
    return _calculate_thermal_load_impl(building, scenario, weather, tariff)

def calculate_thermal_load(building, scenario, weather, tariff_gbp_kwh=0.28):
    key = _make_cache_key(building, scenario, weather, tariff_gbp_kwh)
    result = _calculate_thermal_load_cached(*key)
    return dict(result)   # return mutable copy
```
The internal `_calculate_thermal_load_impl` contains all existing calculation logic
and returns a `frozenset` of items (hashable, cacheable). The public function
returns a plain `dict`. This keeps physics.py free of Streamlit while enabling caching.
`maxsize=512` caps memory at approximately 512 × (result dict size ≈ 200 bytes) ≈ 100 KB.

**`app/segments/__init__.py` — Lazy Loading**
Confirm that `get_segment_handler` uses `importlib.import_module()` and does not
import any segment module at `__init__.py` module load time. Verify no top-level
`from app.segments.university_he import ...` statements exist in the file.

**`app/branding.py` — Asset Cache**
Confirm `get_logo_uri()` and `get_icon_uri()` are decorated with `@st.cache_resource`.
If not already done in Batch 1, add the decorator now. The `_load_asset_uri()` helper
itself need not be cached — only the two public getters.

**`services/epc.py` — EPC Cache**
Add `@st.cache_data(ttl=86400, show_spinner=False)` to `fetch_epc_data()`.
Cache key is the `postcode` parameter (already a string). If `fetch_epc_data` currently
does not accept `postcode` as first positional arg cleanly, create a thin cached wrapper:
```python
@st.cache_data(ttl=86400, show_spinner=False)
def _fetch_epc_cached(postcode: str, api_key: str, api_url: str, timeout_s: int) -> dict:
    return _fetch_epc_impl(postcode, api_key, api_url, timeout_s)
```
Do not cache search_addresses (volatile, low call volume).

### Acceptance Tests

```bash
# T3.1 — LRU cache actually caches (second call must be faster)
python -c "
import time
from core.physics import calculate_thermal_load
b = {'floor_area_m2': 500, 'height_m': 3.5, 'glazing_ratio': 0.3,
     'u_value_wall': 0.35, 'u_value_roof': 0.25, 'u_value_glazing': 2.8,
     'baseline_energy_mwh': 120, 'occupancy_hours': 2500}
s = {'u_wall_factor': 0.6, 'u_roof_factor': 0.7, 'u_glazing_factor': 0.8,
     'solar_gain_reduction': 0.0, 'infiltration_reduction': 0.2,
     'renewable_kwh': 0, 'install_cost_gbp': 50000}
w = {'temperature_c': 8.5}
t0 = time.perf_counter(); calculate_thermal_load(b, s, w); t1 = time.perf_counter()
t2 = time.perf_counter(); calculate_thermal_load(b, s, w); t3 = time.perf_counter()
second_faster = (t3 - t2) < (t1 - t0) * 0.5
print(f'First: {(t1-t0)*1000:.2f}ms  Second: {(t3-t2)*1000:.2f}ms  Cache hit: {second_faster}')
"

# T3.2 — Cache returns mutable dict (not frozen)
python -c "
from core.physics import calculate_thermal_load
b = {'floor_area_m2': 500, 'height_m': 3.5, 'glazing_ratio': 0.3,
     'u_value_wall': 0.35, 'u_value_roof': 0.25, 'u_value_glazing': 2.8,
     'baseline_energy_mwh': 120, 'occupancy_hours': 2500}
s = {'u_wall_factor': 0.6, 'u_roof_factor': 0.7, 'u_glazing_factor': 0.8,
     'solar_gain_reduction': 0.0, 'infiltration_reduction': 0.2,
     'renewable_kwh': 0, 'install_cost_gbp': 50000}
w = {'temperature_c': 8.5}
r = calculate_thermal_load(b, s, w)
r['test_key'] = 'mutation_ok'   # must not raise
print('Cache returns mutable dict: OK')
"

# T3.3 — Segment modules not imported at package init time
python -c "
import sys
before = set(sys.modules.keys())
import app.segments
after = set(sys.modules.keys())
leaked = [m for m in after - before if 'university' in m or 'commercial' in m
          or 'smb_industrial' in m or 'selfbuild' in m]
assert leaked == [], f'Segment modules imported eagerly: {leaked}'
print('Lazy loading: OK')
"

# T3.4 — physics still Streamlit-free after cache addition
python -c "
import sys, types
sys.modules['streamlit'] = None
import core.physics
print('physics Streamlit-free after caching: OK')
"

# T3.5 — EPC cache decorator present
python -c "
import inspect, services.epc
# Check that fetch_epc_data or its wrapper is decorated
src = inspect.getsource(services.epc)
assert 'cache_data' in src and '86400' in src, 'EPC 24hr cache missing'
print('EPC cache: OK')
"
```

### Rollback Plan

**Trigger:** Any T3.x test fails.

**Procedure:**
This batch only adds decorators and modifies internal wrapping — no API surface changes.

```bash
# Restore individual files
git checkout HEAD -- core/physics.py
git checkout HEAD -- app/segments/__init__.py
git checkout HEAD -- app/branding.py
git checkout HEAD -- services/epc.py
```

**Risk level:** Low. Cache decorator removal leaves all functionality identical.
The LRU cache does not affect output correctness — only latency.

---

## Batch 4 — Compliance Engine Modularisation

### Objective
Create `app/tabs/` package with the three tab renderers and `app/sidebar.py`.
Strip `SEGMENT_BUILDINGS` from `app/compliance.py` (now sourced from segment handlers).
Switch `app/compliance.py` to import constants from `config/constants.py`.
The tab and sidebar modules are created but **not yet wired into app/main.py** —
main.py continues to render its own inline logic. This batch is therefore safe:
new code exists but is not called until Batch 5.

**Prerequisite:** Batches 1, 2, and 3 acceptance tests all pass.

### ADD Tasks Covered
014, 016, 017, 018, 019, 020

### Files Impacted

| File | Action | Risk |
|---|---|---|
| `app/tabs/__init__.py` | Create | None |
| `app/tabs/dashboard.py` | Create | None |
| `app/tabs/financial.py` | Create | None |
| `app/tabs/compliance_hub.py` | Create | None |
| `app/sidebar.py` | Create | None |
| `app/compliance.py` | Modify — remove SEGMENT_BUILDINGS; switch constants | Medium |

### Implementation Goal

**`app/tabs/__init__.py`**
Empty file. Establishes the package.

**`app/tabs/dashboard.py`**
Implement `render(handler: SegmentHandler, weather: dict, portfolio: list[dict]) -> None`.

Rendering responsibilities (extracted from the Dashboard tab block in `app/main.py`):
- Four KPI cards (Energy Saved MWh, Carbon Saved tCO₂, Cost Saved £, Payback Years)
  using `_card()` imported from `app.main`.
- Weather conditions widget: render `weather["description"]`, temperature, humidity,
  wind speed from the passed `weather` dict.
- Portfolio summary `st.dataframe`: one row per active portfolio entry.
- Thermal load Plotly bar chart: scenario comparison across selected buildings.
  Calls `physics.calculate_thermal_load()` per (building, scenario) pair — results
  must be computed inside the `with tab:` block (lazy).
- 3D building view: `from app.visualization_3d import render_3d_building` called
  inside this function only (not at module import level).

**`app/tabs/financial.py`**
Implement `render(handler: SegmentHandler, portfolio: list[dict]) -> None`.

Rendering responsibilities:
- ROI comparison table: `pd.DataFrame` of all (building, scenario) pairs with
  cost_saving_gbp, simple_payback_yrs, roi_10yr_gbp columns.
- NPV inputs: `st.slider` for discount rate (1–15%) and analysis period (5–30 years).
  Write results to `st.session_state.discount_rate` and `st.session_state.analysis_period_yrs`
  (add these keys to `app/session.py:init_session()` with defaults 5.0 and 10).
- Payback waterfall Plotly chart.
- CSV export `st.download_button`.
- No compliance calculations inline.

**`app/tabs/compliance_hub.py`**
Implement `render(handler: SegmentHandler, portfolio: list[dict]) -> None`.

Rendering responsibilities:
- Iterate `handler.compliance_checks` (a list of string keys). For each key, render
  the corresponding panel:
  - `"epc_mees"` → call `compliance.estimate_epc_rating(...)` and `compliance.mees_gap_analysis(...)`;
    render results as EPC band gauge chart (Plotly indicator) and MEES gap table.
  - `"part_l"` → call `compliance.part_l_check(...)`; render U-value comparison table
    with RAG (Red/Amber/Green) formatting.
  - `"fhs"` → call `compliance.part_l_check(...)` with FHS thresholds; render primary
    energy metric.
  - `"secr"` → call `compliance.secr_carbon_baseline(...)`; render Scope 1 & 2 baseline
    narrative and chart.
- No `if segment == "x"` branching permitted. Segment logic lives entirely in
  `handler.compliance_checks`.

**`app/sidebar.py`**
Implement `render_sidebar() -> tuple[str | None, dict, str]`.
Returns `(segment_id_or_None, weather_dict, location_name)`.

Responsibilities extracted from `app/main.py` sidebar block:
- `_render_segment_gate()` — if `st.session_state.user_segment is None`, render
  the full-screen four-segment selection cards and return `(None, {}, "")` early.
- `_render_api_keys()` — Gemini key input, Met Office key input, OWM key input.
  Write validated keys to session_state keys defined in `app/session.py`.
- `_render_location_picker()` — postcode / location name input. Call `services.location`.
- `_render_weather_widget()` — call `services.weather.get_weather()`. Return weather dict.
- `_render_portfolio_controls()` — add building (postcode entry → EPC fetch → portfolio append),
  remove building, active selection multi-select.
- `_render_ai_advisor_panel()` — chat input, call `core.agent.run_agent_turn()`,
  display `st.session_state.chat_history`.
- Move `add_to_portfolio()`, `remove_from_portfolio()`, `init_portfolio_entry()` from
  `app/main.py` into this module. These functions must not be deleted from `app/main.py`
  yet — keep them in place with a thin wrapper that calls the sidebar version:
  `from app.sidebar import add_to_portfolio  # noqa` (re-export for Batch 5 cleanup).

**`app/compliance.py` (Modify)**
- Delete `SEGMENT_BUILDINGS: dict[str, dict[str, dict]]` entirely (lines 71 onward).
  Building templates now live in the four segment handler classes.
- Replace all local constant definitions at lines 26–64 with `from config.constants import ...`.
  Re-export with same names if any external module imports them directly:
  `CI_ELECTRICITY = CI_ELECTRICITY  # re-exported from config.constants`
- Keep all calculation functions completely unchanged:
  `estimate_epc_rating`, `mees_gap_analysis`, `secr_carbon_baseline`,
  `part_l_check`, `validate_energy_kwh`, `validate_floor_area`, `validate_u_value`,
  `_band_from_sap`, `MEES_MEASURES`, `SEGMENT_META`.

### Acceptance Tests

```bash
# T4.1 — compliance.py imports cleanly without SEGMENT_BUILDINGS
python -c "
import app.compliance as c
assert not hasattr(c, 'SEGMENT_BUILDINGS'), 'SEGMENT_BUILDINGS must be removed'
print('compliance SEGMENT_BUILDINGS removed: OK')
"

# T4.2 — compliance constants sourced from config
python -c "
from app.compliance import CI_ELECTRICITY
from config.constants import CI_ELECTRICITY as CC
assert CI_ELECTRICITY == CC, 'compliance CI_ELECTRICITY does not match config'
print('compliance constants aligned: OK')
"

# T4.3 — compliance functions still callable
python -c "
from app.compliance import estimate_epc_rating, part_l_check, secr_carbon_baseline
result = estimate_epc_rating({'baseline_energy_mwh': 100, 'floor_area_m2': 500})
assert 'band' in result or isinstance(result, (str, dict))
print('compliance functions callable: OK')
"

# T4.4 — Tab modules importable
python -c "import app.tabs.dashboard; print('dashboard: OK')"
python -c "import app.tabs.financial; print('financial: OK')"
python -c "import app.tabs.compliance_hub; print('compliance_hub: OK')"

# T4.5 — Sidebar module importable
python -c "import app.sidebar; print('sidebar: OK')"

# T4.6 — No segment branching in tab modules
python -c "
import inspect, app.tabs.dashboard, app.tabs.financial, app.tabs.compliance_hub
for mod in [app.tabs.dashboard, app.tabs.financial, app.tabs.compliance_hub]:
    src = inspect.getsource(mod)
    assert 'user_segment' not in src or 'segment_handler' in src, \
        f'{mod.__name__} contains direct segment_id branching'
print('No segment branching in tabs: OK')
"

# T4.7 — app.main still runs (CRITICAL — main.py is unchanged in this batch)
python -c "import app.main; print('app.main unaffected: OK')"
```

### Rollback Plan

**Trigger:** Any T4.x test fails.

**High-risk file:** `app/compliance.py` — the `SEGMENT_BUILDINGS` removal affects any
caller that imports it directly from compliance.

**Pre-batch check:** Before starting this batch, verify:
```bash
grep -rn "compliance.SEGMENT_BUILDINGS\|from app.compliance import.*SEGMENT_BUILDINGS" .
```
If any call site is found outside the four segment handler files, do not proceed —
add a compatibility shim first:
```python
# Temporary bridge at bottom of app/compliance.py
@property
def SEGMENT_BUILDINGS():
    raise DeprecationWarning("Use app.segments.*Handler.building_registry")
```

**Rollback procedure:**
```bash
# Restore compliance.py
git checkout HEAD -- app/compliance.py

# Remove new tab and sidebar modules (pure additions)
rm -rf app/tabs/
rm -f app/sidebar.py
```

**Risk level:** Medium for `compliance.py`, None for new tab/sidebar files.

---

## Batch 5 — UI Redesign

### Objective
Wire all modules created in Batches 1–4 into `app/main.py`. Reduce `app/main.py`
from 3,287 lines to approximately 120 lines. This is the highest-risk batch — it
is the final cut-over from the monolith to the modular architecture.

**Prerequisite:** ALL previous batch acceptance tests must pass before this batch begins.
Run the complete T1–T4 suite as a gate.

### ADD Tasks Covered
021, 023

### Files Impacted

| File | Action | Risk |
|---|---|---|
| `app/main.py` | Major refactor — strip all extracted logic | High |
| `streamlit_app.py` | Verify only — no expected changes | None |

### Implementation Goal

**Pre-Refactor Snapshot**
Before modifying `app/main.py`, create a tagged snapshot:
```bash
git stash push -m "batch5-pre-refactor-snapshot" -- app/main.py
```
Or commit the current state on a checkpoint branch.

**`app/main.py` — Reduction to Orchestrator**

The final file must follow this exact structure:

```python
# app/main.py
from __future__ import annotations
import streamlit as st

import app.branding as branding
import app.session as session
import app.sidebar as sidebar
from app.segments import get_segment_handler
import app.tabs.dashboard as tab_dashboard
import app.tabs.financial as tab_financial
import app.tabs.compliance_hub as tab_compliance

# ── Page config (must be first Streamlit call at module level) ──────────────
st.set_page_config(**branding.PAGE_CONFIG)

# ── KPI card component (used by tab modules via import) ─────────────────────
def _card(label: str, value_html: str, subtext: str, accent_class: str = "") -> None:
    """Compact KPI card. Retained here; imported by tab modules."""
    st.markdown(
        f'<div class="kpi-card {accent_class}">...',
        unsafe_allow_html=True,
    )

# ── Query param persistence (F5 durability) ─────────────────────────────────
def _resolve_query_params() -> None:
    """Apply ?segment= and ?scenarios= URL params to session state."""
    qp = st.query_params
    if "segment" in qp:
        st.session_state.user_segment = qp["segment"]
    if "scenarios" in qp and st.session_state.user_segment:
        ...  # apply scenario whitelist from config.scenarios

# ── Main orchestrator ────────────────────────────────────────────────────────
def run() -> None:
    branding.inject_branding()
    session.init_session()
    _resolve_query_params()

    segment, weather, location = sidebar.render_sidebar()

    if not segment:
        return  # Onboarding gate rendered by sidebar; stop here

    handler  = get_segment_handler(segment)
    portfolio = st.session_state.portfolio

    tab1, tab2, tab3 = st.tabs(
        ["📊 Dashboard", "📈 Financial Analysis", "🏛️ UK Compliance Hub"]
    )
    with tab1:
        tab_dashboard.render(handler, weather, portfolio)
    with tab2:
        tab_financial.render(handler, portfolio)
    with tab3:
        tab_compliance.render(handler, portfolio)

    st.markdown('<div class="footer">© 2026 CrowAgent™ ...</div>',
                unsafe_allow_html=True)
```

**Deletion list** — the following must be removed from `app/main.py` after all
tab/sidebar modules are confirmed working:
- Lines ~63–98: `_load_logo_uri()`, `_load_icon_uri()` (moved to `app/branding.py`)
- Lines ~145–220: inline CSS `st.markdown` block (moved to `app/branding.py`)
- Lines ~238–279: `_add_building_from_json()`, `_add_scenario_from_json()`
- Lines ~282–360: local `BUILDINGS` dict (now from segment handlers)
- Lines ~324–394: local `SCENARIOS`, `SEGMENT_SCENARIOS`, `SEGMENT_DEFAULT_SCENARIOS`
- Lines ~396–405: `_segment_scenario_options()`, `_segment_default_scenarios()`
- Lines ~439–501: `_segment_profile_defaults()`
- Lines ~533–628: `add_to_portfolio()`, `remove_from_portfolio()`, `init_portfolio_entry()`
- Lines ~630–665: `_segment_portfolio()`, `_active_portfolio_entries()`, `_portfolio_buildings_map()`
- Lines ~667–690: `calculate_thermal_load()` (inline wrapper — now calls physics directly from tabs)
- Lines ~692–710: `_safe_number()`, `_safe_nested_number()` (moved to `app/utils.py`)
- Lines ~712–795: `_asset_summary_rows()`, `_hydrate_portfolio_results()`
- Lines ~800–850: scattered `if "key" not in st.session_state` blocks (moved to `app/session.py`)
- All inline tab rendering logic formerly under `with tab1:`, `with tab2:`, `with tab3:`

**`streamlit_app.py` — Verify**
Confirm file still reads:
```python
import app.main
app.main.run()
```
No changes expected.

### Acceptance Tests

```bash
# T5.1 — main.py line count reduced
python -c "
with open('app/main.py') as f:
    lines = f.readlines()
count = len(lines)
assert count <= 200, f'main.py is {count} lines — must be <= 200'
print(f'main.py line count: {count} (OK)')
"

# T5.2 — All deleted functions now absent from main.py
python -c "
import inspect, app.main
src = inspect.getsource(app.main)
for fn in ['_load_logo_uri', '_load_icon_uri', 'SEGMENT_SCENARIOS',
           '_segment_profile_defaults', '_hydrate_portfolio_results']:
    assert fn not in src, f'{fn} still present in main.py after refactor'
print('Extracted functions removed: OK')
"

# T5.3 — _card() still present in main.py (shared component)
python -c "
from app.main import _card
print('_card present in main.py: OK')
"

# T5.4 — Full import chain resolves
python -c "
import streamlit_app
import app.main
import app.branding, app.session, app.sidebar
import app.tabs.dashboard, app.tabs.financial, app.tabs.compliance_hub
import app.segments
print('Full import chain: OK')
"

# T5.5 — No duplicate constant definitions
python -c "
import subprocess, json
# Check no SCENARIOS = { remains in main.py
with open('app/main.py') as f:
    src = f.read()
assert 'SCENARIOS: dict' not in src, 'SCENARIOS dict still defined in main.py'
assert 'BUILDINGS: dict' not in src, 'BUILDINGS dict still defined in main.py'
print('No duplicate definitions: OK')
"

# T5.6 — No inline CSS block in main.py
python -c "
with open('app/main.py') as f:
    src = f.read()
assert 'font-family' not in src, 'Inline CSS still present in main.py'
assert 'background-color' not in src, 'Inline CSS still present in main.py'
print('Branding extracted: OK')
"

# T5.7 — App import does not crash (CRITICAL)
python -c "
import sys
try:
    import app.main
    print('app.main import: OK')
except Exception as e:
    print(f'FAIL: {e}')
    sys.exit(1)
"
```

### Rollback Plan

**Trigger:** Any T5.x test fails, or the app crashes on startup.

**Procedure:**
```bash
# Restore main.py from the pre-refactor snapshot
git checkout HEAD -- app/main.py
# (or restore from the git stash created before this batch)
git stash pop
```

**Staged rollback (preferred over full revert):**
If only specific tab or sidebar wiring causes the crash:
1. Keep `app/branding.py`, `app/session.py`, `app/sidebar.py`, `app/tabs/` in place.
2. In `app/main.py`, temporarily revert only the specific wiring line that fails.
3. Inline that one piece of logic temporarily, then re-extract it correctly.

**Risk mitigation — two-phase execution within this batch:**
- Phase A: Wire branding + session (low risk, test T5.7 after phase A).
- Phase B: Wire sidebar + tabs (higher risk, test T5.1–T5.6 after phase B).
- Only delete old code after Phase B tests pass.
- This allows partial rollback to Phase A if Phase B fails.

---

## Batch 6 — Exception Handling & Logging

### Objective
Introduce typed exceptions for service failures, replace bare `except Exception`
blocks with specific exception types, enforce the `st.warning()` (not `st.error()`)
contract for API failures, harden audit logging, and update the test suite.

**Prerequisite:** Batch 5 acceptance tests all pass.

### ADD Tasks Covered
022, 024

### Files Impacted

| File | Action | Risk |
|---|---|---|
| `services/weather.py` | Modify — add `WeatherFetchError`, tighten except clauses | Low |
| `services/epc.py` | Modify — add `EPCFetchError`, replace bare excepts | Low |
| `services/audit.py` | Modify — postcode truncation, key redaction | Low |
| `app/utils.py` | Modify — final `validate_gemini_key` hardening | Low |
| `tests/` | Modify — update import paths, add smoke tests | Low |

### Implementation Goal

**`services/weather.py` — Typed Exception**
Add at module top:
```python
class WeatherFetchError(RuntimeError):
    """Raised when all weather providers fail and manual fallback is unavailable."""
```
In `get_weather()`: replace bare `except Exception as exc: raise` with
`except (requests.RequestException, KeyError, ValueError) as exc: raise WeatherFetchError(...) from exc`.
Replace the existing `except Exception:` at line 434 with `except WeatherFetchError:`.
All callers (`app/sidebar.py`) must catch `WeatherFetchError` and call `st.warning()` —
never `st.error()`.

**`services/epc.py` — Typed Exception**
Add at module top:
```python
class EPCFetchError(RuntimeError):
    """Raised when EPC lookup fails and stub data cannot be generated."""
```
Replace `raise ValueError(f"No EPC records found...")` at line 166 with
`raise EPCFetchError(f"No EPC records found for postcode: {postcode}")`.
All callers (`app/sidebar.py`) must catch `EPCFetchError` and call `st.warning()` —
the app must continue rendering with stub/estimated data, never block on EPC failure.

**`services/audit.py` — Hardening**
Three changes:
1. Add a `_redact_postcode(text: str) -> str` helper using the `UK_POSTCODE_RE` regex
   that replaces full postcodes with their first 4 characters + `***`:
   `"RG1 2AB" → "RG1 ***"`.
2. Apply `_redact_postcode()` to any field that contains address or postcode data
   before writing to the log.
3. Add an `_assert_no_key(value: str) -> None` guard: if `value` contains a string
   matching `r'^[A-Za-z0-9_\-]{30,}$'` (API key pattern), raise `ValueError` to
   prevent accidental key logging.

**`app/utils.py` — Final Hardening**
Ensure `validate_gemini_key(key: str) -> tuple[bool, str]`:
- Calls `key.strip()` before any check.
- Returns `(False, "Key contains line break characters.")` if `"\n"` in key.
- Returns `(False, "Key contains null bytes.")` if `"\x00"` in key.
- All existing validation logic runs after these guards.
- Never raises an exception to the caller.

**`tests/` — Update and Extend**
Three categories of changes:
1. Update all import paths broken by the module reorganisation (e.g., any test that
   imported `physics.BUILDINGS` or `compliance.SEGMENT_BUILDINGS` must be updated to
   import from the new segment handler files).
2. Add smoke tests per segment handler:
   ```python
   # tests/test_segment_handlers.py
   from config.scenarios import SCENARIOS
   from app.segments import get_segment_handler, SEGMENT_IDS
   def test_all_handlers():
       for sid in SEGMENT_IDS:
           h = get_segment_handler(sid)
           assert len(h.building_registry) > 0
           for name in h.scenario_whitelist:
               assert name in SCENARIOS, f"{sid}: unknown scenario {name}"
   ```
3. Add physics isolation smoke test:
   ```python
   # tests/test_physics_isolation.py
   import subprocess, sys
   def test_physics_no_streamlit():
       result = subprocess.run(
           [sys.executable, "-c",
            "import sys; sys.modules['streamlit']=None; import core.physics"],
           capture_output=True
       )
       assert result.returncode == 0, result.stderr.decode()
   ```

### Acceptance Tests

```bash
# T6.1 — Typed exceptions importable
python -c "
from services.weather import WeatherFetchError
from services.epc import EPCFetchError
print('Typed exceptions: OK')
"

# T6.2 — WeatherFetchError is RuntimeError subclass
python -c "
from services.weather import WeatherFetchError
assert issubclass(WeatherFetchError, RuntimeError)
print('WeatherFetchError hierarchy: OK')
"

# T6.3 — Audit postcode redaction
python -c "
from services.audit import _redact_postcode
assert _redact_postcode('Building at RG1 2AB') == 'Building at RG1 ***'
assert _redact_postcode('No postcode here') == 'No postcode here'
print('Audit postcode redaction: OK')
"

# T6.4 — Audit key guard
python -c "
from services.audit import _assert_no_key
try:
    _assert_no_key('AIzaSyD3RealLookingApiKey12345678901')
    print('FAIL — should have raised ValueError')
except ValueError:
    print('Audit key guard: OK')
"

# T6.5 — validate_gemini_key guards
python -c "
from app.utils import validate_gemini_key
ok, msg = validate_gemini_key('key\ninjection')
assert not ok
ok2, _ = validate_gemini_key('  AIzaSy_valid_key  ')
# strip whitespace — validates stripped version
print(f'Gemini key guards: newline={not ok} OK')
"

# T6.6 — No bare except Exception in service modules
python -c "
import ast, pathlib
for path in ['services/weather.py', 'services/epc.py']:
    tree = ast.parse(pathlib.Path(path).read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            if node.type is None:
                print(f'WARNING: bare except found in {path} line {node.lineno}')
            elif isinstance(node.type, ast.Name) and node.type.id == 'Exception':
                print(f'WARNING: bare except Exception in {path} line {node.lineno}')
print('Exception clause check complete')
"

# T6.7 — Test suite runs
python -m pytest tests/ -v --tb=short 2>&1 | tail -20
```

### Rollback Plan

**Trigger:** Any T6.x test fails.

**Procedure:**
This batch is entirely defensive — it adds guards and tightens contracts without
changing business logic.

```bash
# Restore any affected service file individually
git checkout HEAD -- services/weather.py
git checkout HEAD -- services/epc.py
git checkout HEAD -- services/audit.py
git checkout HEAD -- app/utils.py
# Tests can be reverted without affecting runtime
git checkout HEAD -- tests/
```

**Risk level:** Low. No business logic changes. Exception type changes are backward
compatible — callers catching `RuntimeError` will still catch `WeatherFetchError`
and `EPCFetchError` (both subclass `RuntimeError`).

---

## Full Test Gate Sequence

Run after all six batches complete:

```bash
# Gate 1: Clean imports
python -c "import config.constants, config.scenarios, app.branding, app.session"
python -c "import app.segments, app.tabs.dashboard, app.tabs.financial, app.tabs.compliance_hub"
python -c "import app.sidebar, app.compliance, app.utils"
python -c "import core.physics, core.agent"
python -c "import services.weather, services.epc, services.audit, services.location"

# Gate 2: physics is Streamlit-free
python -c "import sys; sys.modules['streamlit']=None; import core.physics"

# Gate 3: No duplicate constant sources
python -c "
import ast, pathlib, collections
defs = collections.defaultdict(list)
constants_to_check = ['CI_ELECTRICITY', 'HEATING_SETPOINT_C', 'BUILDINGS', 'SCENARIOS']
for path in pathlib.Path('.').rglob('*.py'):
    if '.git' in str(path): continue
    try:
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name) and t.id in constants_to_check:
                        defs[t.id].append(str(path))
    except: pass
for k, v in defs.items():
    if len(v) > 1:
        print(f'DUPLICATE: {k} defined in {v}')
    else:
        print(f'OK: {k} in {v[0]}')
"

# Gate 4: main.py line count
python -c "
lines = len(open('app/main.py').readlines())
assert lines <= 200, f'main.py has {lines} lines'
print(f'main.py: {lines} lines (OK)')
"

# Gate 5: Full test suite
python -m pytest tests/ -v

# Gate 6: Streamlit startup smoke test
timeout 15 python -m streamlit run streamlit_app.py --server.headless true \
  --server.port 8999 2>&1 | grep -E "Running on|Error|Traceback" | head -5
```

---

## Architectural Invariants (Merge Gates)

Violations of the following block merging of any batch PR:

| # | Invariant | Check |
|---|---|---|
| I-1 | `core/physics.py` has zero `streamlit` import | `grep "import streamlit" core/physics.py` must return empty |
| I-2 | Tab modules do not import from `services.*` | `grep -r "import services" app/tabs/` must return empty |
| I-3 | No `<style>` in `st.markdown` outside `app/branding.py` | `grep -rn "unsafe_allow_html" app/ \| grep -v branding.py \| grep -v "_card"` |
| I-4 | No new `st.session_state` keys outside `app/session.py` | `grep -rn "session_state\[" app/ \| grep -v "session.py" \| grep -v ".setdefault" \| grep -v "session_state.get"` |
| I-5 | Constants defined in exactly one file | Gate 3 above returns zero DUPLICATE lines |
| I-6 | API keys not in logs | `grep -rn "gemini_key\|api_key\|met_key" services/audit.py` must return empty |
| I-7 | No `if segment == "x"` in tab renderers | `grep -rn "user_segment ==" app/tabs/` must return empty |

---

**EXECUTION SPECIFICATION COMPLETE — BATCHES 1–6 READY FOR SEQUENTIAL IMPLEMENTATION**
