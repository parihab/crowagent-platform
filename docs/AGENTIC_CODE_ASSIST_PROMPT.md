# CrowAgent™ Platform — Agentic Code Assist Prompt
**Version:** 2.1.0
**Date:** 2026-03-01
**Target Assistants:** Claude Code, Gemini Code Assist, OpenAI Codex, GitHub Copilot Workspace
**Repository:** `parihab/crowagent-platform` · branch `claude/improve-code-assist-prompt-ESFlg`

---

## EXECUTOR RULES — READ BEFORE ANY ACTION

These rules are NON-NEGOTIABLE and apply to every agentic AI code assistant executing this prompt.
Violating any rule is grounds to halt and report rather than proceed.

### R-01 · NO DUPLICATION
Before creating any file, function, constant, or class:
1. Search the codebase using `grep -r "function_name\|ClassName\|CONSTANT_NAME" --include="*.py"`.
2. If it already exists anywhere, **import it — do not redefine it**.
3. The authoritative locations are: `config/constants.py` (all physics/financial constants), `config/scenarios.py` (all scenario dicts), `app/branding.py` (all CSS), `app/session.py` (all session state keys).
4. If a constant or function is duplicated across multiple files today, consolidate it to its authoritative location and update all imports — do not leave the duplicate in place.

### R-02 · NO SESSION BREAKS
- Every `st.session_state` key must be pre-declared in `app/session.py:init_session()` using `st.session_state.setdefault(key, default)`.
- No module outside `app/session.py` may write a new top-level `st.session_state` key that was not declared there.
- Never call `st.session_state.clear()`, `st.session_state.pop()`, or reassign the entire `portfolio` list during a normal render cycle. Portfolio resets happen only on explicit user action via a confirmed button press.
- Segment switches must preserve the cross-segment portfolio; filtering is done at render time via `_segment_portfolio()`.
- Never trigger `st.rerun()` inside a loop — it causes infinite reruns and breaks the session.

### R-03 · USAGE EFFICIENCY
- Read each file **once** per execution pass. Cache the contents and reuse — do not re-read the same file multiple times.
- Group all changes to a single file into one atomic write/edit operation — do not make multiple passes over the same file.
- Prefer targeted `Edit` operations (find + replace) over full file rewrites unless more than 40% of the file is changing.
- Do not call external APIs (Gemini, Weather, EPC) during code generation — stub calls are sufficient for testing.
- Use the wave execution order from `governance/ARCHITECTURE_FREEZE.md §10` when applying multi-file changes to avoid circular dependency issues.

### R-04 · ARCHITECTURE FREEZE — DO NOT CHANGE
The following are immutable. Do not alter folder structure, stack, or segment isolation:
- Folder layout: `app/`, `core/`, `services/`, `config/`, `assets/`
- Stack: Python 3.11+, Streamlit, Plotly, PyDeck, Open-Meteo, Met Office, Gemini 1.5 Pro
- Four segments: `university_he`, `smb_landlord`, `smb_industrial`, `individual_selfbuild`
- Three mandatory tabs: Dashboard, Financial Analysis, UK Compliance Hub
- Entry point: `streamlit_app.py` → `app.main.run()` only

### R-05 · SECURITY — NON-NEGOTIABLE
See full rules in §SECURITY below. Summary:
- API keys: session state only, never `os.environ`, never logs, never query params.
- `unsafe_allow_html=True`: only in `app/branding.py` and `_card()` in `app/main.py`.
- All `requests.get()` calls must include `timeout=8`.
- Postcode inputs must pass through `app/utils._extract_uk_postcode()` before any API call.
- User-supplied strings rendered in HTML must be `html.escape()`-d.

### R-06 · PURE CORE INVARIANT
`core/physics.py` must remain 100% Streamlit-free. Run `python -c "import core.physics"` without
`streamlit` installed to verify. This is a hard gate — if this import fails, the change is invalid.

### R-07 · STOP CONDITIONS
Halt and report (do not attempt a fix) if:
- Circular imports are detected between `core/` and `app/` modules.
- An API key appears in a log string, `st.write()`, query param, or error message.
- `core/physics.py` requires a Streamlit import to function.
- A tab renderer contains segment-specific `if segment == "x"` branching.

---

## CODEBASE CONTEXT MAP

Use this map to locate code without exhaustive file reads.

```
crowagent-platform/
│
├── streamlit_app.py              # 2 lines — imports app.main, calls run()
├── requirements.txt              # streamlit≥1.35, plotly≥5.18, pandas≥2.0,
│                                 # numpy≥1.24, requests≥2.31, pydeck≥0.8
│
├── config/
│   ├── constants.py              # ALL physics & financial constants:
│   │                             #   CI_ELECTRICITY=0.20482 kgCO₂e/kWh (BEIS 2023)
│   │                             #   ELEC_COST_PER_KWH=0.28 £/kWh (HESA 2022-23)
│   │                             #   HEATING_SETPOINT_C=21, HEATING_HOURS_PER_YEAR=5800
│   │                             #   BASE_ACH=0.5, SOLAR_IRRADIANCE_KWH_M2_YEAR=1000
│   │                             #   PART_L_2021_U_WALL/ROOF/GLAZING (residential)
│   │                             #   PART_L_2021_ND_* (non-domestic)
│   │                             #   FHS_MAX_PRIMARY_ENERGY=45 kWh/m²/yr
│   │                             #   EPC_BANDS dict, MEES targets
│   └── scenarios.py              # SCENARIOS dict (5 scenarios), SEGMENT_SCENARIOS,
│                                 # SEGMENT_DEFAULT_SCENARIOS — single source of truth
│
├── app/
│   ├── main.py                   # Thin orchestrator ~120 lines. Contains _card() helper.
│   │                             # st.set_page_config(**branding.PAGE_CONFIG) at module level.
│   │                             # run() calls: inject_branding, init_session,
│   │                             #   _resolve_query_params, render_sidebar, get_segment_handler,
│   │                             #   tab1/tab2/tab3 = st.tabs([...]), footer
│   ├── branding.py               # CROWAGENT_CSS str, inject_branding(), get_logo_uri(),
│   │                             # get_icon_uri(), PAGE_CONFIG dict.
│   │                             # Colours: Primary=#00C2A8, Navy=#071A2F, BG=#F0F4F8
│   │                             # Fonts: Rajdhani (headers/KPIs), Nunito Sans (body)
│   │                             # ONLY place where unsafe_allow_html CSS is injected.
│   ├── session.py                # init_session() — idempotent setdefault() for ALL keys.
│   │                             # _get_secret(key) — reads st.secrets then os.environ.
│   │                             # Canonical session keys (do not invent new ones):
│   │                             #   user_segment, portfolio, active_analysis_ids,
│   │                             #   chat_history, agent_history, gemini_key,
│   │                             #   gemini_key_valid, energy_tariff_gbp_per_kwh,
│   │                             #   weather_provider, building_names,
│   │                             #   selected_scenario_names, onboarding_complete,
│   │                             #   discount_rate, analysis_period_years,
│   │                             #   weather_location, manual_temp_override
│   ├── sidebar.py                # render_sidebar() → (segment_id|None, weather_dict, location)
│   │                             # _render_segment_gate() — 4-card onboarding screen
│   │                             # _render_scenario_selector(), _render_portfolio_controls()
│   │                             # _render_weather_widget(), _render_api_keys_content()
│   │                             # add_to_portfolio(), _add_demo_building()
│   │                             # render_ai_advisor(), render_settings_tab()
│   ├── compliance.py             # Pure calculation functions (NO building templates):
│   │                             #   estimate_epc_rating(), mees_gap_analysis(),
│   │                             #   secr_carbon_baseline(), part_l_check(),
│   │                             #   validate_energy_kwh(), validate_floor_area(),
│   │                             #   validate_u_value(), _band_from_sap()
│   ├── utils.py                  # validate_gemini_key(), _extract_uk_postcode(),
│   │                             # _safe_number(), _safe_nested_number(), show_congratulations()
│   ├── visualization_3d.py       # PyDeck 3D campus map — do not modify unless directed
│   │
│   ├── tabs/
│   │   ├── dashboard.py          # render(handler, weather, portfolio) — KPIs, 3D map,
│   │   │                         #   thermal chart, weather widget, portfolio table
│   │   ├── financial.py          # render(handler, portfolio) — ROI table, NPV, payback chart,
│   │   │                         #   budget optimiser, CSV export
│   │   └── compliance_hub.py     # render(handler, portfolio) — gated by handler.compliance_checks
│   │                             #   panels: epc_mees, part_l, fhs, secr
│   │
│   └── segments/
│       ├── __init__.py           # get_segment_handler(segment_id) — lazy importlib loading
│       │                         # SEGMENT_IDS list, SEGMENT_LABELS dict
│       ├── base.py               # SegmentHandler ABC — segment_id, display_label,
│       │                         #   building_registry, scenario_whitelist,
│       │                         #   default_scenarios, compliance_checks, get_building()
│       ├── university_he.py      # UniversityHEHandler — 3 buildings (Greenfield Library,
│       │                         #   Arts Building, Science Block), compliance: [secr]
│       ├── commercial_landlord.py# CommercialLandlordHandler — 2 buildings (Retail Unit 1,
│       │                         #   Office Block A), compliance: [epc_mees, part_l]
│       ├── smb_industrial.py     # SMBIndustrialHandler — 1 building (Warehouse Unit 4),
│       │                         #   compliance: [secr, part_l]
│       └── individual_selfbuild.py # IndividualSelfBuildHandler — 1 building (Detached House),
│                                 #   compliance: [part_l, fhs]
│
├── core/
│   ├── physics.py                # PURE PYTHON — zero Streamlit imports.
│   │                             # calculate_thermal_load(building, scenario, weather,
│   │                             #   tariff_gbp_kwh=0.28) → ResultDict
│   │                             # LRU cache (512 entries) on calculate_thermal_load.
│   │                             # _validate_model_inputs(), _model_heating_demand_mwh()
│   │                             # Uses functools.lru_cache NOT st.cache_data
│   ├── agent.py                  # run_agent_turn(user_message, history, gemini_key,
│   │                             #   building_registry, scenario_registry) → (reply, new_history)
│   │                             # AGENT_TOOLS list, SYSTEM_PROMPT str, MAX_AGENT_LOOPS=10
│   │                             # Gemini endpoint: generativelanguage.googleapis.com/v1
│   │                             # Model: gemini-1.5-pro
│   │                             # Zero Streamlit imports.
│   └── about.py                  # About & Contact tab static content
│
└── services/
    ├── weather.py                # get_weather(lat, lon, name, provider, met_key, owm_key)
    │                             # → WeatherDict. Cache TTL=3600s. 3 providers:
    │                             #   open_meteo (primary, no key), met_office, openweathermap
    │                             # Custom exception: WeatherFetchError
    ├── epc.py                    # fetch_epc_data(postcode, api_key, ...) → dict | raises EPCFetchError
    │                             # search_addresses(postcode, api_key) → list[dict]
    │                             # Cache TTL=86400s. Fallback stub when no key.
    ├── location.py               # 60-city database, nearest_city(), browser geolocation component
    └── audit.py                  # log_event() — session-only, max 50 entries, redacts postcodes/keys
```

---

## TYPED CONTRACTS (DO NOT CHANGE SIGNATURES)

### `core/physics.py`

```python
# Input types
BuildingDict = TypedDict('BuildingDict', {
    'floor_area_m2':       float,   # > 0
    'height_m':            float,   # > 0
    'glazing_ratio':       float,   # 0 < x < 1
    'u_value_wall':        float,   # W/m²K, 0.05–6.0
    'u_value_roof':        float,
    'u_value_glazing':     float,
    'baseline_energy_mwh': float,
    'occupancy_hours':     float,   # 0–8760
})

ScenarioDict = TypedDict('ScenarioDict', {
    'u_wall_factor':          float,   # 0 < x ≤ 1.0
    'u_roof_factor':          float,
    'u_glazing_factor':       float,
    'solar_gain_reduction':   float,
    'infiltration_reduction': float,
    'renewable_kwh':          float,
    'install_cost_gbp':       float,
})

WeatherDict = TypedDict('WeatherDict', {
    'temperature_c': float,  # –30 to +50
})

# Output type
ResultDict = TypedDict('ResultDict', {
    'annual_energy_mwh':   float,
    'energy_saving_mwh':   float,
    'carbon_saving_tco2':  float,
    'cost_saving_gbp':     float,
    'simple_payback_yrs':  float | None,
    'roi_10yr_gbp':        float,
    'peak_thermal_kw':     float,
})

def calculate_thermal_load(
    building: BuildingDict,
    scenario: ScenarioDict,
    weather: WeatherDict,
    tariff_gbp_kwh: float = 0.28,
) -> ResultDict: ...
```

### `core/agent.py`

```python
def run_agent_turn(
    user_message: str,
    history: list[dict],        # Gemini-format content turns
    gemini_key: str,
    building_registry: dict[str, BuildingDict],
    scenario_registry: dict[str, ScenarioDict],
) -> tuple[str, list[dict]]:   # (reply_text, updated_history)
    ...
```

### `services/weather.py`

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

def get_weather(
    lat: float, lon: float, name: str,
    provider: str,
    met_key: str = "",
    owm_key: str = "",
) -> WeatherDict:  ...          # raises WeatherFetchError on all-provider failure
```

### `app/sidebar.py`

```python
def render_sidebar() -> tuple[str | None, dict, str]:
    ...  # returns (segment_id | None, weather_dict, location_name)
```

### `app/tabs/*.py`

```python
# dashboard.py
def render(handler: SegmentHandler, weather: dict, portfolio: list[dict]) -> None: ...

# financial.py
def render(handler: SegmentHandler, portfolio: list[dict]) -> None: ...

# compliance_hub.py
def render(handler: SegmentHandler, portfolio: list[dict]) -> None: ...
```

---

## SECURITY SPECIFICATION

### S-01 · API Key Lifecycle
```
User input (st.text_input type="password")
  → st.session_state.gemini_key  (session memory only)
  → passed as function argument to run_agent_turn()
  → included in HTTP Authorization header
  → NEVER written to: os.environ, st.query_params, logs, st.write(), error messages
```

Validation before use:
```python
# app/utils.py — validate_gemini_key() contract
def validate_gemini_key(key: str) -> tuple[bool, str]:
    key = key.strip()
    if '\n' in key or '\r' in key:          # log injection prevention
        return False, "Key contains illegal characters"
    if not key.startswith("AIza"):
        return False, "Key must start with 'AIza'"
    if len(key) != 39:
        return False, f"Expected 39 chars, got {len(key)}"
    return True, "Valid format"
```

### S-02 · HTML Injection Prevention
Any user-controlled string rendered via `unsafe_allow_html=True` must be escaped:
```python
import html
safe_name = html.escape(building_name)
st.markdown(f'<div class="kpi-card">{safe_name}</div>', unsafe_allow_html=True)
```
Locations requiring this: `_card()` in `app/main.py`, any building name/postcode in sidebar markdown.

### S-03 · HTTP Request Hardening
Every `requests.get()` and `requests.post()` call must:
```python
response = requests.get(
    url,
    headers=headers,
    params=params,
    timeout=8,          # MANDATORY — never omit
)
response.raise_for_status()   # raises HTTPError on 4xx/5xx
```
Wrap in specific exception handlers:
```python
except requests.exceptions.Timeout:
    raise WeatherFetchError("Request timed out after 8s")
except requests.exceptions.HTTPError as e:
    raise WeatherFetchError(f"HTTP {e.response.status_code}")
except requests.exceptions.RequestException as e:
    raise WeatherFetchError(f"Network error: {type(e).__name__}")
```

### S-04 · Postcode Sanitisation
Postcode inputs must always pass through the validator before any downstream use:
```python
# app/utils.py
import re
_UK_POSTCODE_RE = re.compile(
    r'\b([A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2})\b', re.IGNORECASE
)
def _extract_uk_postcode(text: str) -> str:
    m = _UK_POSTCODE_RE.search(text.strip())
    if not m:
        raise ValueError(f"No valid UK postcode found in: {text!r}")
    return m.group(1).upper().replace(' ', '')
```

### S-05 · Secret Resolution Priority
```python
# app/session.py — _get_secret() canonical implementation
def _get_secret(key: str, default: str = "") -> str:
    try:
        return st.secrets[key]           # 1. Streamlit Secrets (production)
    except (KeyError, FileNotFoundError):
        pass
    return os.environ.get(key, default)  # 2. Environment variable (local dev)
    # NOTE: .env files are loaded by python-dotenv at startup, not here
```

### S-06 · Audit Log Redaction
```python
# services/audit.py — redaction rules
def _redact(value: str) -> str:
    # Redact API keys (starts with AIza or contains 32+ char alphanumeric runs)
    value = re.sub(r'AIza[A-Za-z0-9_-]{35}', '[GEMINI_KEY_REDACTED]', value)
    # Redact full UK postcodes — keep only the outward code (first 3-4 chars)
    value = re.sub(
        r'\b([A-Z]{1,2}\d[A-Z\d]?)\s*\d[A-Z]{2}\b',
        lambda m: m.group(1) + 'XXX', value, flags=re.IGNORECASE
    )
    return value
```

---

## API SPECIFICATION & KNOWN ISSUES

### Gemini API — `core/agent.py`

**Correct endpoint (v1, not v1beta):**
```
https://generativelanguage.googleapis.com/v1/models/gemini-1.5-pro:generateContent
```

**Authentication:**
```python
headers = {
    "Content-Type": "application/json",
    "x-goog-api-key": gemini_key,   # Header-based auth — NOT query param
}
```

**Known issue: do not pass API key as query param `?key=`** — this causes the key to appear in server logs. Always use the header.

**Request body structure:**
```python
payload = {
    "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
    "contents": history,
    "tools": [{"function_declarations": AGENT_TOOLS}],
    "tool_config": {"function_calling_config": {"mode": "AUTO"}},
    "generationConfig": {
        "temperature": 0.2,
        "maxOutputTokens": 2048,
    },
}
```

**Tool-use loop guard:**
```python
MAX_AGENT_LOOPS = 10  # hard cap — prevents runaway billing
loop_count = 0
while loop_count < MAX_AGENT_LOOPS:
    loop_count += 1
    response = _call_gemini(payload, gemini_key)
    # ... process function calls
    if no_more_function_calls:
        break
```

**Error handling:**
```python
except requests.exceptions.Timeout:
    return "The AI Advisor timed out. Please try again.", history
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 429:
        return "API quota exceeded. Please wait a moment.", history
    if e.response.status_code == 403:
        return "Invalid or expired Gemini API key.", history
    return f"API error ({e.response.status_code}). Please retry.", history
```

### Weather API — `services/weather.py`

**Open-Meteo (primary — no key required):**
```
GET https://api.open-meteo.com/v1/forecast
  ?latitude={lat}&longitude={lon}
  &current=temperature_2m,apparent_temperature,wind_speed_10m,relative_humidity_2m,weather_code
  &wind_speed_unit=mph
  &forecast_days=1
  &timezone=auto
timeout=8
```

**Met Office DataPoint (optional key):**
```
GET https://data.hub.api.metoffice.gov.uk/sitespecific/v0/point/hourly
  ?latitude={lat}&longitude={lon}
  &includeLocationName=true
headers: {"apikey": met_key}
timeout=8
```

**OpenWeatherMap (optional key):**
```
GET https://api.openweathermap.org/data/2.5/weather
  ?lat={lat}&lon={lon}&appid={owm_key}&units=metric
timeout=8
```

**Fallback chain:**
```
1. User-selected provider
2. Open-Meteo (always available, no key)
3. Manual temperature override from session state
4. Default: 10°C (UK annual mean)
```

### EPC API — `services/epc.py`

**Endpoint:**
```
GET https://epc.opendatacommunities.org/api/v1/domestic/search
  ?postcode={postcode}&size=5
headers: {
    "Accept": "application/json",
    "Authorization": f"Basic {base64(email:key)}",
}
timeout=8
```

**Stub response (when no key provided):**
```python
_EPC_STUB = {
    "floor_area_m2": 150.0,
    "height_m": 3.0,
    "glazing_ratio": 0.25,
    "u_value_wall": 1.5,
    "u_value_roof": 0.8,
    "u_value_glazing": 2.8,
    "baseline_energy_mwh": 85.0,
    "occupancy_hours": 2200.0,
    "epc_band": "D",
    "source": "stub",
}
```

**Known issue: non-domestic endpoint requires separate URL:**
```
Domestic:     https://epc.opendatacommunities.org/api/v1/domestic/search
Non-domestic: https://epc.opendatacommunities.org/api/v1/non-domestic/search
```
The segment handler's `segment_id` determines which endpoint to call.

---

## BRANDING ENFORCEMENT

### Colour Tokens (defined in `app/branding.py:CROWAGENT_CSS`)
| Token | Hex | Usage |
|---|---|---|
| `--ca-teal` | `#00C2A8` | Primary actions, active states, sidebar headings |
| `--ca-navy` | `#071A2F` | Sidebar background, dark backgrounds |
| `--ca-bg` | `#F0F4F8` | Main area background |
| `--ca-green` | `#1DB87A` | Positive indicators, savings |
| `--ca-gold` | `#F0B429` | Warnings, moderate risk |
| `--ca-red` | `#E84C4C` | Errors, high risk, non-compliance |

### Typography
- **Headers & KPI values:** `font-family: 'Rajdhani', sans-serif; font-weight: 600`
- **Body copy:** `font-family: 'Nunito Sans', sans-serif; font-weight: 400`
- **Google Fonts import** (in CSS only, not repeated per-component):
  ```css
  @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;600;700&family=Nunito+Sans:wght@400;600&display=swap');
  ```

### Violations that must be fixed
- Any `<style>` block in a tab renderer, segment module, or sidebar module → move to `app/branding.py`
- Any hardcoded colour hex not matching the palette above → replace with CSS variable
- Any `st.write()` used for headings where `st.header()` / `st.subheader()` is appropriate → replace
- Any missing `use_container_width=True` on `st.plotly_chart()` or `st.dataframe()` → add it

---

## SEGMENT CONTENT STANDARDS

Each segment must use its exact terminology. Wrong terminology is a content bug.

| Segment | Portfolio Term | Building Term | Compliance Focus |
|---|---|---|---|
| `university_he` | Campus Estate | Building / Block | SECR, TCFD |
| `smb_landlord` | Property Portfolio | Unit / Premises | MEES, EPC Band |
| `smb_industrial` | Facility Portfolio | Site / Facility | SECR Scope 1&2 |
| `individual_selfbuild` | My Property | Dwelling | Part L 2021, FHS |

**Segment gate card copy (exact text):**
- University HE: "Campus Decarbonisation & SECR Reporting"
- Commercial Landlord: "MEES Compliance & EPC Portfolio Management"
- SMB Industrial: "Scope 1 & 2 Carbon Baseline — SECR"
- Individual Self-Build: "Part L 2021 & Future Homes Standard"

---

## EXECUTION PHASES

Execute all phases sequentially. Do not skip a phase. Confirm each phase is stable
(app imports without error) before proceeding to the next.

### PHASE 1 — PRE-FLIGHT AUDIT (read-only, no changes)
1. Run: `python -c "import app.main"` — confirm no ImportError.
2. Run: `python -c "import core.physics"` — confirm no Streamlit import.
3. Search for duplicated constants: `grep -rn "CI_ELECTRICITY\|ELEC_COST\|HEATING_SETPOINT" --include="*.py"` — all hits must be in `config/constants.py` only.
4. Search for inline CSS: `grep -rn "unsafe_allow_html" --include="*.py"` — all hits must be in `app/branding.py` or `_card()` in `app/main.py`.
5. Search for API keys in logs: `grep -rn "gemini_key\|api_key" services/audit.py` — confirm redaction is applied.
6. Report findings as a structured diagnostic. Do not proceed to Phase 2 until report is complete.

### PHASE 2 — FOUNDATION (config/, app/session.py, app/branding.py, app/utils.py)
Apply only if Phase 1 audit identified gaps. Check each file before editing.
- `config/constants.py`: consolidate all physics/financial constants. Remove duplicates from source files.
- `config/scenarios.py`: single `SCENARIOS` dict. Remove duplicates elsewhere.
- `app/session.py`: ensure `init_session()` covers all keys. Move `_get_secret()` here if not present.
- `app/branding.py`: move all `<style>` blocks here. Verify font import is exactly once.
- `app/utils.py`: add newline-rejection to `validate_gemini_key()`. Confirm `_extract_uk_postcode()` is here.

### PHASE 3 — SEGMENT ISOLATION (app/segments/)
- Verify each `*Handler` class extends `SegmentHandler` and implements all abstract properties.
- Verify `building_registry` buildings match the segment's domain (no cross-segment data).
- Verify `compliance_checks` matches the table in §SEGMENT CONTENT STANDARDS.
- Verify `get_segment_handler()` uses lazy `importlib.import_module()` loading.
- Fix any missing or incorrect `display_label` values.

### PHASE 4 — CORE ENGINE (core/physics.py, core/agent.py)
- `core/physics.py`: verify `functools.lru_cache` (not `st.cache_data`) is used. Verify zero Streamlit imports. Verify `ResultDict` keys match the contract in §TYPED CONTRACTS.
- `core/agent.py`: verify Gemini endpoint is `v1` (not `v1beta`). Verify API key is in header (not query param). Verify `MAX_AGENT_LOOPS = 10` guard. Verify `run_agent_turn()` accepts `building_registry` and `scenario_registry` as explicit params. Add 429/403/timeout error handling per §API SPECIFICATION.

### PHASE 5 — SERVICE LAYER (services/)
- `services/weather.py`: verify 3-provider fallback chain. Verify all `requests.get()` calls have `timeout=8`. Verify `WeatherFetchError` is raised (not caught silently). Verify `@st.cache_data(ttl=3600)` is applied.
- `services/epc.py`: verify domestic vs non-domestic endpoint routing. Verify stub is returned (not crash) when no API key. Verify `@st.cache_data(ttl=86400)`. Verify `EPCFetchError` typed exception.
- `services/audit.py`: verify postcode redaction truncates to outward code only. Verify no key values logged.

### PHASE 6 — UI LAYER (app/tabs/, app/sidebar.py)
- Each tab's `render()` function must match the signature in §TYPED CONTRACTS.
- No tab module may import from `services.*` directly — all service data arrives via function parameters.
- No tab may contain `if segment == "x"` branching — use `handler.compliance_checks`.
- `app/sidebar.py`: verify `render_sidebar()` signature. Verify `_render_segment_gate()` renders only 4 cards. Verify portfolio add flow calls `_extract_uk_postcode()` before EPC fetch.
- Add `use_container_width=True` to all `st.plotly_chart()` and `st.dataframe()` calls that are missing it.

### PHASE 7 — ACCESSIBILITY & POLISH
- Replace any KPI values rendered as raw HTML with `st.metric()` where accessible (or ensure ARIA labels on HTML versions).
- Verify font size is ≥ 14px for body copy in the CSS.
- Verify sidebar text colour has ≥ 4.5:1 contrast against `#071A2F` (navy) background.
- Verify all `st.spinner("...")` messages use active-verb language: "Fetching weather data…", "Running physics model…", "Consulting AI Advisor…".
- Replace `st.error()` for recoverable API failures with `st.warning()` to avoid blocking the render.
- Add empty-state messages to all tables and charts when portfolio is empty:
  ```python
  if not portfolio:
      st.info("Portfolio is empty. Add a building in the sidebar to begin analysis.")
      return
  ```

### PHASE 8 — END-TO-END VALIDATION
Simulate in order (use manual trace if live execution is not available):
1. App load → `init_session()` → no `KeyError` in `st.session_state`.
2. Segment gate → select `university_he` → segment stored, tabs appear.
3. Add demo building → `_add_demo_building()` → portfolio has 1 entry.
4. Dashboard tab → `render(handler, weather, portfolio)` → KPIs computed, chart renders.
5. Financial tab → ROI table populated → payback chart renders → CSV export available.
6. Compliance tab → SECR panel visible (university_he) → no MEES/Part L panels.
7. AI Advisor → send query → Gemini tool loop runs → reply rendered in chat.
8. Segment switch → `smb_landlord` selected → university portfolio not shown → MEES/EPC panels visible.
9. Verify: no `st.session_state` `KeyError`, no crashed render, no console traceback.

### PHASE 9 — COMMIT & PUSH
After all phases pass:
```bash
git add -p   # stage only changed files
git commit -m "refactor: harden CrowAgent platform — security, API, session, branding

- Fix Gemini endpoint to v1, move key to header auth
- Add timeout=8 to all requests, typed exception handling
- Consolidate constants to config/, remove duplicates
- Enforce session state contract via init_session()
- Add HTML escaping for user-supplied strings in unsafe_allow_html
- Add postcode redaction in audit log
- Validate gemini key strips whitespace, rejects newlines
- Add empty-state guards to all tab renderers
- Fix use_container_width=True on all charts/dataframes"

git push -u origin claude/improve-code-assist-prompt-ESFlg
```

---

## MERGE-BLOCKING VIOLATIONS

Any of the following automatically invalidates the change. Do not merge until resolved.

| # | Violation | Check Command |
|---|---|---|
| V-01 | `core/physics.py` imports `streamlit` | `python -c "import core.physics"` without streamlit installed |
| V-02 | Tab module imports from `services.*` | `grep -rn "from services\|import services" app/tabs/` |
| V-03 | `unsafe_allow_html` with `<style>` outside `app/branding.py` | `grep -rn "unsafe_allow_html" --include="*.py" \| grep -v "branding.py\|main.py"` |
| V-04 | New `st.session_state` key not in `app/session.py:init_session()` | Manual review of `init_session()` |
| V-05 | Physical constant defined in more than one file | `grep -rn "CI_ELECTRICITY\|ELEC_COST_PER_KWH" --include="*.py"` |
| V-06 | API key in log, query param, or `st.write()` | `grep -rn "gemini_key\|api_key" --include="*.py" \| grep -v "session_state\|st.text_input\|validate"` |
| V-07 | `if segment == "x"` inside a tab renderer | `grep -rn 'segment ==' app/tabs/` |
| V-08 | `requests.get()` without `timeout=` | `grep -rn "requests.get\|requests.post" --include="*.py" \| grep -v "timeout"` |
| V-09 | User string in `unsafe_allow_html` block without `html.escape()` | Manual review of `_card()` and sidebar markdown |
| V-10 | `st.session_state.clear()` in render path | `grep -rn "session_state.clear\|session_state.pop" --include="*.py"` |

---

## REFERENCE: FIVE SCENARIOS (config/scenarios.py)

```python
SCENARIOS = {
    "Baseline (No Intervention)": {
        "u_wall_factor": 1.0, "u_roof_factor": 1.0, "u_glazing_factor": 1.0,
        "solar_gain_reduction": 0.0, "infiltration_reduction": 0.0,
        "renewable_kwh": 0.0, "install_cost_gbp": 0.0,
    },
    "Fabric Upgrade (Insulation)": {
        "u_wall_factor": 0.6, "u_roof_factor": 0.5, "u_glazing_factor": 1.0,
        "solar_gain_reduction": 0.0, "infiltration_reduction": 0.0,
        "renewable_kwh": 0.0, "install_cost_gbp": 25000.0,
    },
    "Glazing Upgrade": {
        "u_wall_factor": 1.0, "u_roof_factor": 1.0, "u_glazing_factor": 0.4,
        "solar_gain_reduction": 0.0, "infiltration_reduction": 0.1,
        "renewable_kwh": 0.0, "install_cost_gbp": 15000.0,
    },
    "Renewables (Solar PV)": {
        "u_wall_factor": 1.0, "u_roof_factor": 1.0, "u_glazing_factor": 1.0,
        "solar_gain_reduction": 0.0, "infiltration_reduction": 0.0,
        "renewable_kwh": 5000.0, "install_cost_gbp": 8000.0,
    },
    "Deep Retrofit (All Measures)": {
        "u_wall_factor": 0.5, "u_roof_factor": 0.4, "u_glazing_factor": 0.4,
        "solar_gain_reduction": 0.1, "infiltration_reduction": 0.2,
        "renewable_kwh": 5000.0, "install_cost_gbp": 48000.0,
    },
}
```

---

## REFERENCE: PHYSICS MODEL EQUATIONS

The PINN thermal model (Raissi et al., 2019) uses the following equations.
Do not alter these — they are the scientific foundation of the platform.

```
# Envelope area decomposition
A_wall    = 2 × (√floor_area + √floor_area) × height × (1 − glazing_ratio)
A_glazing = 2 × (√floor_area + √floor_area) × height × glazing_ratio
A_roof    = floor_area

# Delta-T (heating season)
ΔT = HEATING_SETPOINT_C − weather_temperature_c

# Transmission losses [Wh/yr]
Q_transmission = (
    U_wall    × A_wall    +
    U_glazing × A_glazing +
    U_roof    × A_roof
) × ΔT × HEATING_HOURS_PER_YEAR

# Infiltration losses [Wh/yr]
Volume = floor_area × height
Q_infiltration = 0.33 × ACH × Volume × ΔT × HEATING_HOURS_PER_YEAR

# Solar gains [Wh/yr]
Q_solar = SOLAR_IRRADIANCE_KWH_M2_YEAR × 1000 × A_glazing × (1 − solar_gain_reduction) × η_solar

# Net heating demand [MWh/yr]
Q_net = (Q_transmission + Q_infiltration − Q_solar) / 1e6

# Apply scenario modifications (factors multiply U-values, then recalculate)
# renewable_kwh offsets net demand after PINN calculation
```

---

## DO NOT TOUCH (STABLE MODULES)

Unless a Phase 1 audit specifically identifies a defect in these files, do not modify them:
- `services/location.py` — geolocation component is stable
- `app/visualization_3d.py` — PyDeck map is stable
- `core/about.py` — static content, no logic
- `assets/` — SVG files, no changes
- `.streamlit/config.toml` — server config, no changes
- `streamlit_app.py` — entry point, must remain 2 lines only
- `governance/ARCHITECTURE_FREEZE.md` — authoritative reference document

---

## FINAL STABILITY GATE

Before declaring the task complete, confirm all of the following:

- [ ] `python -c "import app.main"` exits with code 0
- [ ] `python -c "import core.physics"` exits with code 0 (no streamlit)
- [ ] V-01 through V-10 checks all pass
- [ ] All 4 segments render their correct terminology and compliance panels
- [ ] Gemini tool loop uses `v1` endpoint with header-based auth
- [ ] All `requests.*` calls have `timeout=8`
- [ ] Audit log redacts postcodes and API keys
- [ ] Portfolio empty-state messages render in all 3 tabs
- [ ] `use_container_width=True` on all charts and dataframes
- [ ] No `<style>` blocks outside `app/branding.py`
- [ ] Branch `claude/improve-code-assist-prompt-ESFlg` pushed successfully

**Platform Status:** Production-ready enterprise prototype
**Copyright:** © 2026 Aparajita Parihar · CrowAgent™ Unregistered TM
**Physics Reference:** PINN (Raissi et al., 2019) doi:10.1016/j.jcp.2018.10.045
