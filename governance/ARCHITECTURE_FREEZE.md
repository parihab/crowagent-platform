# ARCHITECTURE FREEZE — ENFORCEMENT DIRECTIVE

This document defines the immutable architecture of this platform.

The following are NON-NEGOTIABLE:

- Python
- Streamlit
- Plotly
- Open-Meteo API
- Met Office DataPoint
- Google Gemini Flash
- PINN Thermal Model
- Streamlit Community Cloud
- Zero infrastructure cost
- Four mandatory segments
- Three mandatory tabs per segment
- Branding on every page
- Persistent About & Contact section

No implementation may:
- Change folder structure
- Introduce new external services
- Alter segment isolation logic
- Remove mandatory components

Any deviation must be explicitly rejected.

# CrowAgent™ Platform — Architecture Decision Document (ADD)
**Version:** 1.0.0
**Date:** 2026-02-28
**Status:** FREEZE CANDIDATE
**Author:** Principal Software Architect
**Scope:** Full structural redesign — no stack changes, no feature removal

---

## Non-Negotiable Stack (Preserved)
- Python · Streamlit · Plotly · Open-Meteo API · Met Office DataPoint
- Google Gemini Flash · PINN Thermal Model · Streamlit Community Cloud
- Zero infrastructure cost

## Mandatory Segments (All Preserved)
1. University / HE
2. Commercial Landlord
3. SMB Industrial
4. Individual Self-Build

## Mandatory Tabs (All Preserved)
- 📊 Dashboard · 📈 Financial Analysis · 🏛️ UK Compliance Hub

---

# 1. Target Folder Architecture

```
crowagent-platform/
│
├── streamlit_app.py                    # Entry point — 2 lines, unchanged
├── requirements.txt                    # Unchanged
│
├── .streamlit/
│   └── config.toml                     # Unchanged
│
├── assets/
│   ├── CrowAgent_Logo_Horizontal_Dark.svg
│   └── CrowAgent_Icon_Square.svg       # Unchanged
│
├── config/
│   ├── __init__.py                     # NEW
│   ├── constants.py                    # NEW — all shared physical + financial constants
│   └── scenarios.py                    # NEW — SCENARIOS dict + per-segment scenario whitelists
│
├── app/
│   ├── __init__.py                     # Unchanged
│   ├── main.py                         # REFACTORED — thin orchestrator only (~120 lines)
│   ├── branding.py                     # NEW — CSS injection, font loading, logo URI resolver
│   ├── session.py                      # NEW — all st.session_state key initialisation
│   ├── sidebar.py                      # NEW — full sidebar rendering (API keys, segment gate,
│   │                                   #         location, portfolio controls)
│   ├── compliance.py                   # MODIFIED — remove SEGMENT_BUILDINGS; keep all
│   │                                   #            compliance calculation functions
│   ├── utils.py                        # Unchanged
│   └── visualization_3d.py             # Unchanged
│   │
│   ├── tabs/
│   │   ├── __init__.py                 # NEW
│   │   ├── dashboard.py                # NEW — 📊 Dashboard tab renderer
│   │   ├── financial.py                # NEW — 📈 Financial Analysis tab renderer
│   │   └── compliance_hub.py           # NEW — 🏛️ UK Compliance Hub tab renderer
│   │
│   └── segments/
│       ├── __init__.py                 # NEW — exports get_segment_handler()
│       ├── base.py                     # NEW — SegmentHandler abstract base class
│       ├── university_he.py            # NEW — University/HE buildings + segment logic
│       ├── commercial_landlord.py      # NEW — Commercial Landlord buildings + segment logic
│       ├── smb_industrial.py           # NEW — SMB Industrial buildings + segment logic
│       └── individual_selfbuild.py     # NEW — Individual Self-Build buildings + segment logic
│
├── core/
│   ├── __init__.py                     # Unchanged
│   ├── physics.py                      # REFACTORED — pure calculation engine; building
│   │                                   #   registry removed; no UI imports
│   └── agent.py                        # REFACTORED — tool definitions extracted to
│                                       #   separate dict; SYSTEM_PROMPT references config
│
└── services/
    ├── __init__.py                     # Unchanged
    ├── weather.py                      # Unchanged (already well-abstracted)
    ├── epc.py                          # Unchanged
    ├── location.py                     # Unchanged
    └── audit.py                        # Unchanged
```

---

# 2. Module Responsibility Map

| File | Sole Responsibility | Must NOT Contain |
|---|---|---|
| `streamlit_app.py` | Import and call `app.main.run()` | Any logic |
| `config/constants.py` | Physical constants (CI factors, tariffs, U-value targets, SAP thresholds) | UI, API calls, Streamlit |
| `config/scenarios.py` | `SCENARIOS` dict; `SEGMENT_SCENARIOS` whitelist; `SEGMENT_DEFAULT_SCENARIOS` | Building templates, UI |
| `app/branding.py` | CSS string, font URLs, logo/icon URI resolution, `inject_branding()` call | Session state, tabs, physics |
| `app/session.py` | One `init_session()` function that writes all default `st.session_state` keys exactly once | Rendering, API calls |
| `app/sidebar.py` | `render_sidebar()` — segment gate, API key inputs, location picker, portfolio controls | Tab content, physics |
| `app/tabs/dashboard.py` | `render(segment_handler, weather, portfolio)` — KPI cards, 3D view, thermal chart | Financial logic, compliance |
| `app/tabs/financial.py` | `render(segment_handler, portfolio)` — ROI table, payback chart, NPV inputs | Compliance, weather calls |
| `app/tabs/compliance_hub.py` | `render(segment_handler, portfolio)` — EPC/MEES, Part L, SECR outputs | Financial logic, physics engine |
| `app/segments/base.py` | `SegmentHandler` ABC with `building_registry`, `scenario_whitelist`, `compliance_checks`, `display_label` | Streamlit rendering |
| `app/segments/university_he.py` | `UniversityHEHandler` — Greenfield buildings, HE-specific scenarios, CRC/DECchecks | SMB/residential logic |
| `app/segments/commercial_landlord.py` | `CommercialLandlordHandler` — office/retail/industrial templates, MEES focus | HE/industrial logic |
| `app/segments/smb_industrial.py` | `SMBIndustrialHandler` — manufacturer/logistics templates, SECR Scope 1&2 focus | Residential logic |
| `app/segments/individual_selfbuild.py` | `IndividualSelfBuildHandler` — residential templates, Part L / FHS focus | Commercial logic |
| `core/physics.py` | `calculate_thermal_load(building, scenario, weather)` pure function; `_model_heating_demand_mwh()`; validation helpers | Building registry, SCENARIOS dict, UI |
| `core/agent.py` | Gemini Flash HTTP loop, tool dispatch, `SYSTEM_PROMPT`, `run_agent_turn()` | Session state, Streamlit widgets |
| `app/compliance.py` | All compliance calculation functions: `estimate_epc_rating()`, `mees_gap_analysis()`, `secr_carbon_baseline()`, `part_l_check()` | Building templates, UI rendering |
| `services/weather.py` | Weather provider fallback chain, `get_weather()`, `@st.cache_data` decorators | Physics, compliance |
| `services/epc.py` | EPC API calls + stub fallback, `fetch_epc_data()`, `search_addresses()` | Physics, UI |

---

# 3. Segment Isolation Design

## Session State Strategy

All segment-scoped state lives under namespaced keys. `app/session.py` owns the complete initialisation contract:

```
# Keys initialised in app/session.py — init_session()
st.session_state.user_segment          = None        # Gate key — None triggers onboarding
st.session_state.portfolio             = []          # List[dict] — ALL segments combined
st.session_state.active_analysis_ids   = []          # Selected asset IDs for current view
st.session_state.chat_history          = []          # AI Advisor display messages
st.session_state.agent_history         = []          # Gemini internal tool-use turns
st.session_state.gemini_key            = ""
st.session_state.gemini_key_valid      = False
st.session_state.energy_tariff_gbp_per_kwh = 0.28   # User-overridable
st.session_state.weather_provider      = "open_meteo"
st.session_state.building_names        = {}          # postcode → display name cache
st.session_state.selected_scenario_names = []
st.session_state.onboarding_complete   = False
```

**Rule:** No module outside `app/session.py` may write a new top-level key to `st.session_state` without first defining it here. Reading is unrestricted.

## Segment Gate

`app/main.py` checks `st.session_state.user_segment` before rendering any tabs:

```
Segment == None  →  render_onboarding_gate()  (full-screen selection, no tabs)
Segment == value →  render_sidebar() + render_tabs()
```

The gate must be rendered from `app/sidebar.py`. Once selected, segment is persisted to URL query param `?segment=<id>` for F5 durability.

## Dynamic Rendering Logic

Each tab renderer receives a `segment_handler: SegmentHandler` instance resolved by:

```python
# app/segments/__init__.py
def get_segment_handler(segment_id: str) -> SegmentHandler:
    _REGISTRY = {
        "university_he":          UniversityHEHandler,
        "smb_landlord":           CommercialLandlordHandler,
        "smb_industrial":         SMBIndustrialHandler,
        "individual_selfbuild":   IndividualSelfBuildHandler,
    }
    cls = _REGISTRY.get(segment_id)
    if cls is None:
        raise ValueError(f"Unknown segment: {segment_id!r}")
    return cls()
```

Tab renderers call `segment_handler.building_registry` to get available buildings and `segment_handler.scenario_whitelist` to get available scenarios. No `if segment == "x"` branching is permitted inside tab files.

## Portfolio Isolation

`_segment_portfolio()` filters `st.session_state.portfolio` by `entry["segment"] == st.session_state.user_segment`. Cross-segment data is retained in session (not deleted on switch) but never rendered in a different segment's view.

---

# 4. Service Layer Abstraction Design

## Design Pattern: Thin Adapters over Existing Services

All three external APIs (Open-Meteo, Met Office, Gemini) are already behind function-level abstractions in `services/`. The required change is to enforce that **no tab, segment, or main module imports from `services/` directly**. All service calls route through typed gateway functions.

## Weather Gateway — `services/weather.py` (Unchanged API)

`get_weather(lat, lon, name, provider, met_key, owm_key)` is the sole public entry point.
Tab renderers call it once at the top of `app/main.py:run()` and pass the result dict downward as a parameter. No tab module imports `services.weather`.

**Contract (existing, preserved):**
```python
WeatherDict = {
    "temperature_c":     float,
    "apparent_temp_c":   float,
    "wind_speed_mph":    float,
    "humidity_pct":      float,
    "description":       str,
    "provider":          str,
    "fetched_utc":       str,
    "location_name":     str,
}
```

## EPC Gateway — `services/epc.py` (Unchanged API)

`fetch_epc_data(postcode, api_key, api_url, timeout_s)` returns a dict or raises. Called only from `app/sidebar.py` during portfolio add. Result is stored in the portfolio entry dict, not re-fetched per render.

## Gemini Gateway — `core/agent.py` (Unchanged API)

`run_agent_turn(user_message, history, gemini_key, building_registry, scenario_registry)` is the sole public function. The compliance hub tab does **not** call Gemini directly — only the AI Advisor panel in the sidebar calls `run_agent_turn`. This prevents uncontrolled token spend from tab renders.

## Met Office DataPoint

Accessed exclusively via `services/weather.py:_fetch_met_office()`. No direct `requests.get` to DataPoint URLs outside this function.

## Offline / Fallback Guarantee

Each gateway function must return a valid typed dict or raise a typed exception (`WeatherFetchError`, `EPCFetchError`). Callers handle exceptions and surface `st.warning()` — never `st.error()` that blocks render.

---

# 5. Simulation Engine Encapsulation Strategy

## PINN Isolation Pattern

`core/physics.py` must be a **pure Python module** — zero Streamlit imports, zero `st.*` calls. It is the single source of truth for the thermal model.

### Inputs (typed dict, validated on entry):
```python
BuildingDict = {
    "floor_area_m2":       float,   # > 0
    "height_m":            float,   # > 0
    "glazing_ratio":       float,   # 0 < x < 1
    "u_value_wall":        float,   # W/m²K, 0.05–6.0
    "u_value_roof":        float,
    "u_value_glazing":     float,
    "baseline_energy_mwh": float,
    "occupancy_hours":     float,   # 0–8760
}
ScenarioDict = {
    "u_wall_factor":          float,   # 0 < x ≤ 1.0
    "u_roof_factor":          float,
    "u_glazing_factor":       float,
    "solar_gain_reduction":   float,
    "infiltration_reduction": float,
    "renewable_kwh":          float,
    "install_cost_gbp":       float,
}
WeatherDict = {
    "temperature_c": float,   # –30 to +50
}
```

### Output (typed dict, immutable):
```python
ResultDict = {
    "annual_energy_mwh":   float,
    "energy_saving_mwh":   float,
    "carbon_saving_tco2":  float,
    "cost_saving_gbp":     float,
    "simple_payback_yrs":  float | None,
    "roi_10yr_gbp":        float,
    "peak_thermal_kw":     float,
}
```

### What must be removed from `core/physics.py`:
- `BUILDINGS` dict (university hardcoded templates) → move to `app/segments/university_he.py`
- `SCENARIOS` dict (intervention registry) → move to `config/scenarios.py`

### What must stay in `core/physics.py`:
- All physical constants (grid carbon intensity, heating set-point, solar irradiance, etc.)
- `_validate_model_inputs(building, scenario, weather)` — raises `ValueError` on bad data
- `_model_heating_demand_mwh(...)` — internal calculation
- `calculate_thermal_load(building, scenario, weather, tariff_gbp_kwh)` — public entry

### Agent Tool Binding

`core/agent.py` resolves building data at tool-call time from its `building_registry` parameter (passed in at call time, not imported at module level). This decouples the agent from any single segment's building set.

```python
# core/agent.py — tool dispatch pattern
def _tool_run_scenario(args, building_registry, scenario_registry, tariff):
    building  = building_registry[args["building_name"]]
    scenario  = scenario_registry[args["scenario_name"]]
    weather   = {"temperature_c": args.get("temperature_c", 10.0)}
    return physics.calculate_thermal_load(building, scenario, weather, tariff)
```

---

# 6. UI Layout System

## Component Architecture for Streamlit

### Execution Flow (app/main.py — ~120 lines)

```
run()
  │
  ├── branding.inject_branding()          # CSS + fonts — once per session
  │
  ├── session.init_session()              # st.session_state defaults — idempotent
  │
  ├── _resolve_query_params()             # F5 persistence — reads ?segment= ?scenarios=
  │
  ├── sidebar.render_sidebar()            # Returns: segment, weather, location
  │     ├── _render_segment_gate()        # If segment is None → full-screen gate, return early
  │     ├── _render_api_keys()
  │     ├── _render_location_picker()
  │     ├── _render_portfolio_controls()
  │     └── _render_ai_advisor_panel()
  │
  ├── [Guard: if not segment → stop]      # No tabs rendered until segment selected
  │
  ├── handler = get_segment_handler(segment)
  │
  ├── tab1, tab2, tab3 = st.tabs([...])
  │     ├── tab1 → tabs.dashboard.render(handler, weather, portfolio)
  │     ├── tab2 → tabs.financial.render(handler, portfolio)
  │     └── tab3 → tabs.compliance_hub.render(handler, portfolio)
  │
  └── [Footer — single st.markdown call]
```

### Tab Component Contracts

**`app/tabs/dashboard.py:render(handler, weather, portfolio)`**
- KPI metric row: 4 `_card()` widgets (Energy Saved, Carbon Saved, Cost Saved, Payback)
- 3D building visualisation (calls `app/visualization_3d.py`)
- Thermal load bar chart (Plotly, scenario comparison)
- Weather widget (current conditions from `weather` dict)
- Portfolio summary table (`st.dataframe`)

**`app/tabs/financial.py:render(handler, portfolio)`**
- ROI comparison table (all scenarios × all active buildings)
- NPV slider inputs (discount rate, analysis period)
- Payback waterfall chart (Plotly)
- Budget optimiser widget (calls `core/agent.py:find_best_for_budget` logic directly)
- Export button (CSV download, `st.download_button`)

**`app/tabs/compliance_hub.py:render(handler, portfolio)`**
- Segment-specific compliance panels gated by `handler.compliance_checks` list:
  - `"epc_mees"` → EPC band gauge + MEES 2028/2030 gap
  - `"part_l"` → U-value comparison table vs Part L 2021 targets
  - `"fhs"` → Future Homes Standard primary energy check
  - `"secr"` → Scope 1 & 2 carbon baseline + SECR narrative
- Each panel calls a function from `app/compliance.py` — no compliance logic inline

### Component Reuse Rules
- `_card()` lives in `app/main.py` and is imported by all tab modules
- `_safe_number()` and `_safe_nested_number()` move to `app/utils.py`
- No tab module renders a `st.sidebar.*` widget
- No sidebar module renders a main-area widget

---

# 7. Global Branding Enforcement Mechanism

## Module: `app/branding.py`

Single responsibility: produce and inject all visual identity tokens. Called exactly once per app run, at the top of `run()`, before any widget is rendered.

### Contents:

**`CROWAGENT_CSS: str`** — Complete CSS string (currently inline in `main.py` lines ~145–220). Contains:
- Google Fonts import (`Rajdhani`, `Nunito Sans`)
- Background colour (`#F0F4F8`)
- Sidebar dark theme (`#071A2F` background, `#CBD8E6` text, `#00C2A8` headings)
- KPI card styles (`.kpi-card`, `.kpi-value`, accent classes)
- Tab override styles
- Button override styles
- Footer style

**`_load_asset_uri(filename: str) -> str`** — resolves the asset path across four candidate locations (same logic as current `_load_logo_uri` / `_load_icon_uri`), returns base64 data URI. Raises no exceptions — returns `""` on failure and logs a warning via `st.warning()`.

**`inject_branding() -> None`** — calls `st.markdown(CROWAGENT_CSS, unsafe_allow_html=True)` once.

**`get_logo_uri() -> str`** — cached via `@st.cache_resource` to prevent re-reading SVG on every rerun.

**`get_icon_uri() -> str`** — same pattern.

**`PAGE_CONFIG: dict`** — all kwargs for `st.set_page_config()`. Called in `main.py` at module level (must remain at module level per Streamlit constraint).

### Enforcement Rule:
No `st.markdown()` call containing `<style>` tags is permitted outside `app/branding.py`. CSS written inline in tab or sidebar modules is a merge-blocking violation.

---

# 8. Performance Strategy

## Caching

| Layer | Mechanism | TTL | Scope |
|---|---|---|---|
| Weather data | `@st.cache_data(ttl=3600)` | 1 hour | Per (lat, lon, provider) |
| Logo/icon SVG | `@st.cache_resource` | Session | Process-wide |
| EPC lookup | `@st.cache_data(ttl=86400)` | 24 hours | Per postcode |
| `calculate_thermal_load` | `@st.cache_data(ttl=None)` | Permanent | Per (building_hash, scenario_hash, temp) |
| Gemini responses | No cache | — | Chat history in session_state |

**`calculate_thermal_load` cache key:** hash of `(json.dumps(building, sort_keys=True), json.dumps(scenario, sort_keys=True), round(weather["temperature_c"], 1))`. This eliminates redundant PINN calls when the user re-selects the same building/scenario combination.

## Lazy Loading

- Tab content is not computed until the user clicks the tab. Wrap all computation inside the `with tab:` block — no pre-computation in `run()`.
- `app/segments/*.py` files are imported lazily inside `get_segment_handler()` using `importlib.import_module()` — this avoids loading all four segment modules on every cold start.
- The 3D visualisation (`app/visualization_3d.py`) is imported inside `tabs/dashboard.py`, not at `main.py` module level.

## Cold Start Mitigation (Streamlit Community Cloud)

Streamlit Community Cloud hibernates instances after inactivity. Mitigation:

1. **`@st.cache_resource` for heavy imports** — NumPy, Pandas, Plotly graph_objects are pre-imported at module level in `main.py` only (they are unavoidable). `core/physics.py` imports NumPy once; the result is cached.
2. **`requirements.txt` pin all versions** — prevents slow dependency resolution on cold wake.
3. **Asset pre-load** — `get_logo_uri()` and `get_icon_uri()` decorated with `@st.cache_resource` so SVG files are read from disk only once per server lifetime.
4. **No blocking I/O at module load** — weather, EPC, and location calls must not execute at module-import time. All are function-scoped.
5. **Minimal sidebar API calls** — Met Office / OWM key validation (`test_met_office_key`, `test_openweathermap_key`) are called on explicit button press only, not on every sidebar render.

## Bundle Size

- No additional PyPI packages beyond `requirements.txt`.
- Plotly figures use `go.Figure()` with explicit traces — no `px.*` shorthand that imports the full express module.

---

# 9. Security Hardening Blueprint

## API Key Handling

**Current risk:** `st.session_state.gemini_key` is stored as plaintext string in session state — acceptable for Streamlit (server-side memory, not persisted). No change required.

**Rule:** No API key may appear in:
- Streamlit query params (`st.query_params`)
- `st.write()` / `st.text()` output
- Log statements (audit.py must redact keys)
- Git history (`.env.example` must use placeholder values only)

**`app/utils.py:validate_gemini_key(key)`** must:
1. Strip whitespace before validation
2. Reject strings containing newline characters (log injection prevention)
3. Return `(bool, str)` — never raise exceptions to the UI

## Input Validation Boundaries

All user-supplied values entering physics calculations must pass through `compliance.py` validators (`validate_energy_kwh`, `validate_floor_area`, `validate_u_value`) before reaching `core/physics.py`. `physics.py:_validate_model_inputs()` is the last-line guard — not the first.

**Postcode inputs:** `_extract_uk_postcode()` in `main.py` already applies the UK postcode regex. Move this function to `app/utils.py`. Never pass raw postcode strings to EPC API without this sanitisation.

## External HTTP Calls

All `requests.get()` calls must specify `timeout=8` (seconds). No call may omit timeout. This is already enforced in `services/weather.py` and `services/epc.py` — enforce during code review of any new service function.

## Content Security

- `unsafe_allow_html=True` is used only in `app/branding.py` (CSS injection) and `app/main.py` (`_card()` KPI widget). No other module may use this flag.
- User-provided building names (from postcode lookup) must be HTML-escaped before insertion into any `st.markdown(..., unsafe_allow_html=True)` string.

## Secrets Management

Production secrets (`GEMINI_API_KEY`, `MET_OFFICE_KEY`, etc.) are read via Streamlit Secrets (`st.secrets`) with `.env` fallback for local development. `_get_secret()` in `main.py` already implements this pattern — it must be the only secrets access point. Move `_get_secret()` to `app/session.py`.

## Audit Logging

`services/audit.py` must log: segment selection, portfolio add/remove, AI Advisor query (query text only — no key, no result). No PII (postcode counts as PII — log only the first 4 characters for zone-level analytics).

---

# 10. Refactor Task Breakdown

Tasks are ordered by dependency. Each task is atomic and independently reviewable.

---

### TASK 001
**File:** `config/__init__.py`
**Change type:** Create
**Instruction:** Create empty `__init__.py` to establish the `config` package. No contents.
**Dependencies:** None

---

### TASK 002
**File:** `config/constants.py`
**Change type:** Create
**Instruction:** Extract all physical and financial constants currently duplicated across `core/physics.py`, `app/compliance.py`, and `app/main.py` into a single authoritative source. Must include: `CI_ELECTRICITY`, `CI_GAS`, `CI_OIL`, `CI_LPG`, `ELEC_COST_PER_KWH`, `GAS_COST_PER_KWH`, `HEATING_SETPOINT_C`, `HEATING_HOURS_PER_YEAR`, `BASE_ACH`, `SOLAR_IRRADIANCE_KWH_M2_YEAR`, `PART_L_2021_U_WALL`, `PART_L_2021_U_ROOF`, `PART_L_2021_U_GLAZING`, `PART_L_2021_ND_*`, `FHS_MAX_PRIMARY_ENERGY`, `EPC_BANDS`, `MEES_CURRENT_MIN_BAND`, `MEES_2028_TARGET_BAND`. After creating, update all source files to import from `config.constants` and delete local copies.
**Dependencies:** TASK 001

---

### TASK 003
**File:** `config/scenarios.py`
**Change type:** Create
**Instruction:** Move the `SCENARIOS` dict (currently in `core/physics.py`) and `SEGMENT_SCENARIOS` / `SEGMENT_DEFAULT_SCENARIOS` dicts (currently in `app/main.py` lines ~362–394) into this file. Export: `SCENARIOS: dict[str, dict]`, `SEGMENT_SCENARIOS: dict[str, list[str]]`, `SEGMENT_DEFAULT_SCENARIOS: dict[str, list[str]]`. After creating, update all importers and delete the source copies.
**Dependencies:** TASK 002

---

### TASK 004
**File:** `app/branding.py`
**Change type:** Create
**Instruction:** Move the full CSS string (currently `st.markdown("""<style>...""")` block in `app/main.py` ~lines 145–220) into `CROWAGENT_CSS: str`. Create `inject_branding() -> None` that calls `st.markdown(CROWAGENT_CSS, unsafe_allow_html=True)`. Create `_load_asset_uri(filename: str) -> str` consolidating the two existing `_load_logo_uri()` / `_load_icon_uri()` functions. Create `@st.cache_resource`-decorated `get_logo_uri() -> str` and `get_icon_uri() -> str`. Create `PAGE_CONFIG: dict` with all `st.set_page_config` kwargs. Delete `_load_logo_uri`, `_load_icon_uri`, `LOGO_URI`, `ICON_URI` from `app/main.py` and the inline CSS block.
**Dependencies:** TASK 001

---

### TASK 005
**File:** `app/session.py`
**Change type:** Create
**Instruction:** Create `init_session() -> None` — an idempotent function that sets every `st.session_state` key listed in Section 3 to its default value using `st.session_state.setdefault()` (never overwriting existing values). Move `_get_secret()` from `app/main.py` into this module. Move `MAX_CHAT_HISTORY` constant here. Delete all scattered `if "key" not in st.session_state` blocks from `app/main.py`.
**Dependencies:** TASK 002

---

### TASK 006
**File:** `app/segments/__init__.py`
**Change type:** Create
**Instruction:** Create `get_segment_handler(segment_id: str) -> SegmentHandler` using the registry dict pattern defined in Section 3. Use `importlib.import_module()` for lazy loading each segment module. Export: `get_segment_handler`, `SEGMENT_IDS: list[str]`, `SEGMENT_LABELS: dict[str, str]`.
**Dependencies:** TASK 001

---

### TASK 007
**File:** `app/segments/base.py`
**Change type:** Create
**Instruction:** Define `SegmentHandler` as an abstract base class (`abc.ABC`). Required abstract properties: `segment_id: str`, `display_label: str`, `building_registry: dict[str, dict]`, `scenario_whitelist: list[str]`, `default_scenarios: list[str]`, `compliance_checks: list[str]`. Required concrete method: `get_building(name: str) -> dict` (raises `KeyError` with helpful message if not found). No Streamlit imports permitted in this file.
**Dependencies:** TASK 001

---

### TASK 008
**File:** `app/segments/university_he.py`
**Change type:** Create
**Instruction:** Implement `UniversityHEHandler(SegmentHandler)`. Move the `BUILDINGS` dict from `core/physics.py` (Greenfield Library, Greenfield Arts Building, Greenfield Science Block) into `building_registry`. Set `scenario_whitelist` from `config.scenarios.SEGMENT_SCENARIOS["university_he"]`. Set `compliance_checks = ["epc_mees"]`. Add `segment_id = "university_he"` and `display_label = "🏛️ University / Higher Education"`.
**Dependencies:** TASK 007, TASK 003

---

### TASK 009
**File:** `app/segments/commercial_landlord.py`
**Change type:** Create
**Instruction:** Implement `CommercialLandlordHandler(SegmentHandler)`. Move the `smb_landlord` sub-dict from `SEGMENT_BUILDINGS` in `app/compliance.py` into `building_registry`. Set `scenario_whitelist` from `config.scenarios.SEGMENT_SCENARIOS["smb_landlord"]`. Set `compliance_checks = ["epc_mees", "part_l"]`. Add `segment_id = "smb_landlord"` and `display_label = "🏢 Commercial Landlord"`.
**Dependencies:** TASK 007, TASK 003

---

### TASK 010
**File:** `app/segments/smb_industrial.py`
**Change type:** Create
**Instruction:** Implement `SMBIndustrialHandler(SegmentHandler)`. Move the `smb_industrial` sub-dict from `SEGMENT_BUILDINGS` in `app/compliance.py` into `building_registry`. Set `scenario_whitelist` from `config.scenarios.SEGMENT_SCENARIOS["smb_industrial"]`. Set `compliance_checks = ["secr", "part_l"]`. Add `segment_id = "smb_industrial"` and `display_label = "🏭 SMB Industrial"`.
**Dependencies:** TASK 007, TASK 003

---

### TASK 011
**File:** `app/segments/individual_selfbuild.py`
**Change type:** Create
**Instruction:** Implement `IndividualSelfBuildHandler(SegmentHandler)`. Move the `individual_selfbuild` sub-dict from `SEGMENT_BUILDINGS` in `app/compliance.py` into `building_registry`. Set `scenario_whitelist` from `config.scenarios.SEGMENT_SCENARIOS["individual_selfbuild"]`. Set `compliance_checks = ["part_l", "fhs"]`. Add `segment_id = "individual_selfbuild"` and `display_label = "🏠 Individual Self-Build"`.
**Dependencies:** TASK 007, TASK 003

---

### TASK 012
**File:** `core/physics.py`
**Change type:** Refactor
**Instruction:** Remove `BUILDINGS` dict entirely (moved in TASK 008). Remove `SCENARIOS` dict entirely (moved in TASK 003). Replace all local constant definitions with imports from `config.constants`. Verify `calculate_thermal_load(building, scenario, weather, tariff_gbp_kwh=0.28) -> dict` signature matches the ResultDict defined in Section 5. Add `@st.cache_data` decorator — **do not** import `streamlit` at module level; instead accept it as an optional argument or use `functools.lru_cache` with a hashable key tuple. The module must import-clean with `python -c "import core.physics"` and zero Streamlit dependency.
**Dependencies:** TASK 002, TASK 003

---

### TASK 013
**File:** `core/agent.py`
**Change type:** Refactor
**Instruction:** Extract the tool definitions list (currently hardcoded in the agent module) into a top-level `AGENT_TOOLS: list[dict]` constant. Update `run_agent_turn()` signature to accept `building_registry: dict` and `scenario_registry: dict` as explicit parameters — remove any hardcoded reference to `physics.BUILDINGS` or `physics.SCENARIOS`. Update `SYSTEM_PROMPT` to reference `config.constants` values rather than hardcoded numbers. Ensure the module has zero `streamlit` imports.
**Dependencies:** TASK 002, TASK 003, TASK 012

---

### TASK 014
**File:** `app/compliance.py`
**Change type:** Modify
**Instruction:** Remove `SEGMENT_BUILDINGS` dict entirely (building templates moved to TASK 009–011). Remove all local constant definitions that now live in `config/constants.py`; replace with `from config.constants import ...`. Keep all calculation functions unchanged: `estimate_epc_rating()`, `mees_gap_analysis()` (if separate), `secr_carbon_baseline()`, `part_l_check()`, `validate_energy_kwh()`, `validate_floor_area()`, `validate_u_value()`, `_band_from_sap()`. Keep `SEGMENT_META` dict if present.
**Dependencies:** TASK 002, TASK 009, TASK 010, TASK 011

---

### TASK 015
**File:** `app/utils.py`
**Change type:** Modify
**Instruction:** Move `_extract_uk_postcode(text: str) -> str` from `app/main.py` into this module. Move `_safe_number(value, default)` and `_safe_nested_number(container, *keys, default)` from `app/main.py` into this module. Update `validate_gemini_key()` to strip whitespace and reject strings containing `\n` before the existing validation logic.
**Dependencies:** None

---

### TASK 016
**File:** `app/tabs/__init__.py`
**Change type:** Create
**Instruction:** Create empty `__init__.py` to establish the `app.tabs` package. No contents.
**Dependencies:** TASK 001

---

### TASK 017
**File:** `app/tabs/dashboard.py`
**Change type:** Create
**Instruction:** Create `render(handler: SegmentHandler, weather: dict, portfolio: list[dict]) -> None`. Extract from `app/main.py` all rendering logic that currently executes under the "📊 Dashboard" tab: the four KPI `_card()` calls, the `st.plotly_chart` thermal load chart, the weather conditions widget, the portfolio summary `st.dataframe`, and the 3D building view call. The function must call `physics.calculate_thermal_load()` for each active portfolio entry. Import `_card` from `app.main` (temporary bridge — see TASK 020). Do not embed any compliance or financial calculations.
**Dependencies:** TASK 007, TASK 012, TASK 016

---

### TASK 018
**File:** `app/tabs/financial.py`
**Change type:** Create
**Instruction:** Create `render(handler: SegmentHandler, portfolio: list[dict]) -> None`. Extract from `app/main.py` all rendering logic for the "📈 Financial Analysis" tab: ROI comparison table, NPV slider inputs, payback waterfall Plotly chart, budget optimiser widget, and CSV export `st.download_button`. Discount rate and analysis period inputs must write to `st.session_state` keys (defined in session.py). No compliance calculations inline.
**Dependencies:** TASK 007, TASK 012, TASK 016

---

### TASK 019
**File:** `app/tabs/compliance_hub.py`
**Change type:** Create
**Instruction:** Create `render(handler: SegmentHandler, portfolio: list[dict]) -> None`. Extract from `app/main.py` all rendering logic for the "🏛️ UK Compliance Hub" tab. Use `handler.compliance_checks` to gate which panels are shown — do not use `if segment == "x"` branching. Each panel calls the corresponding `app.compliance` function and renders results with Plotly gauge / table widgets. Panels: `"epc_mees"` → EPC band + MEES gap; `"part_l"` → U-value table; `"fhs"` → primary energy check; `"secr"` → Scope 1&2 baseline.
**Dependencies:** TASK 007, TASK 014, TASK 016

---

### TASK 020
**File:** `app/sidebar.py`
**Change type:** Create
**Instruction:** Create `render_sidebar() -> tuple[str | None, dict, str]` returning `(segment_id, weather_dict, location_name)`. Extract from `app/main.py` the full sidebar block: segment gate (onboarding UI when `user_segment is None`), API key input widgets, location picker, weather provider selector, portfolio add/remove controls, and AI Advisor chat panel. The function writes to `st.session_state` only via keys defined in `app/session.py`. Calls `services.weather.get_weather()` and `services.epc.fetch_epc_data()`. Move `add_to_portfolio()`, `remove_from_portfolio()`, `init_portfolio_entry()` into this module.
**Dependencies:** TASK 005, TASK 006, TASK 007, TASK 013

---

### TASK 021
**File:** `app/main.py`
**Change type:** Refactor
**Instruction:** Reduce to a thin orchestrator of ~120 lines. Module-level: `st.set_page_config(**branding.PAGE_CONFIG)`. Define `run() -> None` containing: `branding.inject_branding()`, `session.init_session()`, `_resolve_query_params()`, `segment, weather, location = sidebar.render_sidebar()`, segment guard, `handler = get_segment_handler(segment)`, `tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "📈 Financial Analysis", "🏛️ UK Compliance Hub"])`, and the three `with tab` blocks calling the tab renderers. Move `_card()` to remain here (it is used by tab modules via import). Delete all functions moved to other modules in TASKS 005–020.
**Dependencies:** TASK 004, TASK 005, TASK 006, TASK 017, TASK 018, TASK 019, TASK 020

---

### TASK 022
**File:** `services/audit.py`
**Change type:** Modify
**Instruction:** Ensure log entries for postcode data truncate to the first 4 characters only (sector-level, not full postcode). Add redaction for any string matching `UK_POSTCODE_RE` in log payloads. Confirm API key values are never passed to log functions.
**Dependencies:** None

---

### TASK 023
**File:** `streamlit_app.py`
**Change type:** Modify
**Instruction:** Verify the entry point imports only `app.main` and calls `app.main.run()`. It must contain no logic, constants, or imports beyond this. Current file already does this — confirm no drift occurred during TASK 021.
**Dependencies:** TASK 021

---

### TASK 024 — Integration Verification
**File:** `tests/` (existing test suite)
**Change type:** Modify
**Instruction:** After all above tasks are complete, update import paths in existing tests to reflect moved modules. Add one smoke-test per new segment handler confirming `building_registry` is non-empty and `scenario_whitelist` contains only keys present in `config.scenarios.SCENARIOS`. Add one unit test confirming `core/physics.py` can be imported with zero Streamlit dependency (`python -c "import core.physics"` must succeed without `streamlit` installed).
**Dependencies:** TASK 003, TASK 008–011, TASK 012

---

## Dependency Execution Order (Recommended)

```
Wave 1 (no deps):     001, 004, 015, 022
Wave 2:               002, 005, 006, 016
Wave 3:               003, 007
Wave 4:               008, 009, 010, 011, 013, 014
Wave 5:               012, 017, 018, 019
Wave 6:               020
Wave 7:               021, 023
Wave 8 (verify):      024
```

---

## Architectural Invariants (Merge-Blocking Violations)

Any PR that violates the following must be rejected:

1. `core/physics.py` imports `streamlit` → **REJECT**
2. Any tab module (`app/tabs/*.py`) imports directly from `services.*` → **REJECT**
3. Any module outside `app/branding.py` uses `st.markdown(..., unsafe_allow_html=True)` with `<style>` content → **REJECT**
4. A new `st.session_state` key is created outside `app/session.py:init_session()` → **REJECT**
5. `BUILDINGS`, `SCENARIOS`, or physical constants are defined in more than one file → **REJECT**
6. An API key string is logged, written to query params, or passed to `st.write()` → **REJECT**
7. Any segment-specific `if segment == "x"` branch appears inside a tab renderer → **REJECT**

---

**ARCHITECTURE FREEZE COMPLETE – READY FOR CODEX EXECUTION**