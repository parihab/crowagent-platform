"""
Renders the sidebar for the CrowAgent™ platform.

Handles:
- Styled onboarding gate with logo + segment cards
- Logo + active segment display in sidebar
- Scenario multiselect with URL sync
- Portfolio management with EPC band display
- Location: city dropdown + custom coordinates + browser geolocation
- Live weather widget (full detail: wind, humidity, feels-like, pulse dot)
- API Keys: Gemini (with live validation) + OWM + Met Office (with test buttons)
- Config audit/change log
- Data sources citation list
- Branded sidebar footer
"""
from __future__ import annotations
import uuid
import streamlit as st

import core.agent
import services.weather as weather_service
import services.audit as audit
import services.location as loc
import services.epc as epc_service
from app.branding import get_logo_uri
from app.segments import get_segment_handler, SEGMENT_IDS, SEGMENT_LABELS
from app.utils import validate_gemini_key
from config.scenarios import SCENARIOS, SEGMENT_DEFAULT_SCENARIOS

MAX_PORTFOLIO_SIZE = 10


# ─────────────────────────────────────────────────────────────────────────────
# PORTFOLIO HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def init_portfolio_entry(postcode: str, segment: str, epc_data: dict | None = None) -> dict:
    """Creates a new portfolio entry with full schema."""
    epc_data = epc_data or {}
    return {
        "id": str(uuid.uuid4()),
        "postcode": postcode,
        "segment": segment,
        "display_name": epc_data.get("address", postcode),
        "epc_band": epc_data.get("current-energy-rating", "N/A"),
        "epc_rating": epc_data.get("current-energy-rating", "N/A"),
        "floor_area_m2": float(epc_data.get("total-floor-area", 1000.0)),
        "building_data": {
            "floor_area_m2": float(epc_data.get("total-floor-area", 1000.0)),
            "height_m": 3.5,
            "glazing_ratio": 0.30,
            "u_value_wall": 1.8,
            "u_value_roof": 2.0,
            "u_value_glazing": 2.8,
            "baseline_energy_mwh": float(epc_data.get("total-floor-area", 1000.0)) * 0.15,
            "occupancy_hours": 3500,
            "built_year": epc_data.get("construction-age-band", "2000"),
            "description": f"{postcode} — {segment} building",
            "building_type": segment,
        },
        "baseline_results": {},
        "combined_results": {},
        "results": {},
    }


def add_to_portfolio(postcode: str, segment: str):
    """Fetches EPC data and adds a new building to the portfolio."""
    if len(st.session_state.portfolio) >= MAX_PORTFOLIO_SIZE:
        st.error(f"Portfolio is full ({MAX_PORTFOLIO_SIZE} assets maximum).")
        return
    with st.spinner(f"Fetching EPC data for {postcode}…"):
        try:
            epc_data = epc_service.fetch_epc_data(postcode)
            st.success(f"Found EPC data for {epc_data.get('address', postcode)}")
        except Exception:
            epc_data = None
    new_entry = init_portfolio_entry(postcode, segment, epc_data)
    st.session_state.portfolio.append(new_entry)
    st.toast(f"Added '{new_entry['display_name']}' to portfolio.")


def remove_from_portfolio(entry_id: str):
    """Removes a building from the portfolio by its ID."""
    st.session_state.portfolio = [p for p in st.session_state.portfolio if p.get("id") != entry_id]
    st.session_state.active_analysis_ids = [
        i for i in st.session_state.active_analysis_ids if i != entry_id
    ]
    st.toast("Removed building from portfolio.")


# ─────────────────────────────────────────────────────────────────────────────
# URL QUERY PARAM SYNC
# ─────────────────────────────────────────────────────────────────────────────

def _update_query_params():
    params: dict[str, str] = {}
    if st.session_state.get("user_segment"):
        params["segment"] = st.session_state.user_segment
    _sel = st.session_state.get("selected_scenario_names", [])
    if _sel:
        params["scenarios"] = ",".join(_sel)
    if st.session_state.get("wx_city"):
        params["city"] = st.session_state.wx_city
    params["lat"] = str(round(st.session_state.get("wx_lat", 51.4543), 4))
    params["lon"] = str(round(st.session_state.get("wx_lon", -0.9781), 4))
    st.query_params.clear()
    st.query_params.update(params)


def _segment_default_scenarios(segment: str | None) -> list[str]:
    defaults = SEGMENT_DEFAULT_SCENARIOS.get(segment or "", [])
    return [s for s in defaults if s in SCENARIOS] or list(SCENARIOS.keys())[:2]


# ─────────────────────────────────────────────────────────────────────────────
# ONBOARDING GATE
# ─────────────────────────────────────────────────────────────────────────────

def _render_segment_gate() -> None:
    logo_uri = get_logo_uri()
    _logo_html = (
        f"<img src='{logo_uri}' width='220' style='max-width:100%;height:auto;"
        "display:inline-block;margin-bottom:10px;' alt='CrowAgent\u2122 Logo'/>"
        if logo_uri
        else "<div style='font-family:Rajdhani,sans-serif;font-size:2rem;font-weight:700;"
             "color:#00C2A8;margin-bottom:10px;'>CrowAgent\u2122</div>"
    )
    st.markdown(
        f"<div style='text-align:center;margin-top:40px;'>"
        f"{_logo_html}"
        f"<h1 style='color:#071A2F;margin-bottom:8px;'>Welcome to CrowAgent\u2122 Platform</h1>"
        f"<p style='color:#5A7A90;font-size:1.05rem;margin:0 auto 8px auto;max-width:820px;'>"
        f"CrowAgent\u2122 is a sustainability decision-intelligence workspace for UK built-environment "
        f"stakeholders. Retrofit scenario modelling, financial insights, AI recommendations, "
        f"and UK compliance guidance.</p>"
        f"<p style='color:#7A93A7;font-size:0.8rem;margin:0 auto 28px auto;max-width:920px;line-height:1.45;'>"
        f"Prototype notice: outputs are indicative and for decision support only. "
        f"\u00a9 2026 CrowAgent\u2122. All rights reserved.</p></div>",
        unsafe_allow_html=True,
    )

    segments_ui = [
        ("university_he",        "University / HE",       "\U0001f393", "Campus estate managers"),
        ("smb_landlord",         "Commercial Landlord",   "\U0001f3e2", "MEES compliance focused"),
        ("smb_industrial",       "SMB Industrial",        "\U0001f3ed", "SECR / Carbon baselining"),
        ("individual_selfbuild", "Individual Self-Build", "\U0001f3e0", "Part L / FHS compliance"),
    ]
    cols = st.columns(4)
    for (seg_id, label, icon, desc), col in zip(segments_ui, cols):
        with col:
            st.markdown(
                f"<div style='background:#ffffff;border-radius:8px;border:1px solid #E0EBF4;"
                f"padding:20px;text-align:center;height:180px;"
                f"box-shadow:0 4px 6px rgba(0,0,0,0.05);'>"
                f"<div style='font-size:2.5rem;margin-bottom:10px;'>{icon}</div>"
                f"<div style='font-family:Rajdhani,sans-serif;font-weight:700;font-size:1.1rem;"
                f"color:#071A2F;'>{label}</div>"
                f"<div style='font-size:0.8rem;color:#5A7A90;margin-top:5px;'>{desc}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
            if st.button(f"Select {label}", key=f"btn_gate_{seg_id}", use_container_width=True):
                st.session_state.user_segment = seg_id
                st.session_state.selected_scenario_names = _segment_default_scenarios(seg_id)
                st.query_params["segment"] = seg_id
                st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR SECTIONS
# ─────────────────────────────────────────────────────────────────────────────

def _render_sidebar_logo(segment: str):
    logo_uri = get_logo_uri()
    if logo_uri:
        st.markdown(
            f"<div style='padding:10px 0 4px;text-align:center;'>"
            f"<img src='{logo_uri}' width='200' style='max-width:100%;height:auto;"
            f"display:inline-block;' alt='CrowAgent\u2122 Logo'/></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div style='font-family:Rajdhani,sans-serif;font-size:1.3rem;font-weight:700;"
            "color:#00C2A8;padding:10px 0 4px;'>\U0001f33f CrowAgent\u2122</div>",
            unsafe_allow_html=True,
        )
    st.markdown(
        "<div style='font-size:0.82rem;color:#8FBCCE;margin-bottom:8px;'>"
        "Sustainability AI Decision Intelligence Platform</div>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    st.markdown("<div class='sb-section'>\U0001f464 Active Segment</div>", unsafe_allow_html=True)
    _seg_icons = {
        "university_he": "\U0001f393", "smb_landlord": "\U0001f3e2",
        "smb_industrial": "\U0001f3ed", "individual_selfbuild": "\U0001f3e0",
    }
    _seg_descs = {
        "university_he": "Campus estate manager — energy & carbon",
        "smb_landlord": "Commercial landlord — MEES compliance",
        "smb_industrial": "Industrial SMB — SECR / carbon reporting",
        "individual_selfbuild": "Self-build — Part L / FHS compliance",
    }
    _icon = _seg_icons.get(segment, "\U0001f464")
    _label = SEGMENT_LABELS.get(segment, segment)
    _desc = _seg_descs.get(segment, "")
    st.markdown(
        f"<div style='font-size:0.9rem;color:#00C2A8;font-weight:600;margin-bottom:4px;'>"
        f"{_icon} {_label}</div>"
        f"<div style='font-size:0.74rem;color:#8FBCCE;line-height:1.5;margin-bottom:10px;'>"
        f"{_desc}</div>",
        unsafe_allow_html=True,
    )
    if st.button("Change Segment / Reset", key="btn_reset_segment"):
        st.session_state.user_segment = None
        st.session_state.pop("selected_scenario_names", None)
        st.query_params.clear()
        st.rerun()


def _render_scenario_selector(segment: str):
    st.markdown("<div class='sb-section'>\U0001f9ea Scenarios</div>", unsafe_allow_html=True)
    _all_opts = list(SCENARIOS.keys())
    _defaults = _segment_default_scenarios(segment)
    _current = [s for s in st.session_state.get("selected_scenario_names", _defaults) if s in SCENARIOS] or _defaults

    _chosen = st.multiselect(
        "Scenario selection",
        options=_all_opts,
        default=_current,
        key="selected_scenario_names",
        format_func=lambda k: f"{SCENARIOS[k].get('icon','?')} {SCENARIOS[k].get('display_name', k)}",
        help="Choose one or more intervention scenarios for calculations.",
    )
    if not _chosen:
        st.session_state.selected_scenario_names = _defaults
    _update_query_params()


def _render_portfolio_controls(segment: str):
    st.markdown("<div class='sb-section'>\U0001f3e2 Asset Portfolio</div>", unsafe_allow_html=True)
    _count = len(st.session_state.portfolio)
    st.markdown(
        f"<div style='font-size:0.75rem;color:#8FBCCE;'>{_count} / {MAX_PORTFOLIO_SIZE} Assets Loaded</div>",
        unsafe_allow_html=True,
    )
    with st.form(key="add_portfolio_form", clear_on_submit=True):
        new_postcode = st.text_input("Add UK Postcode", placeholder="e.g. SW1A 1AA")
        if st.form_submit_button("\u2795 Add Asset", use_container_width=True) and new_postcode:
            add_to_portfolio(new_postcode.strip().upper(), segment)
            st.rerun()

    if st.session_state.portfolio:
        seg_portfolio = [p for p in st.session_state.portfolio if p.get("segment") == segment]
        st.multiselect(
            "Active Buildings for Analysis",
            options=[p["id"] for p in seg_portfolio],
            format_func=lambda pid: next((p["display_name"] for p in seg_portfolio if p["id"] == pid), pid),
            key="active_analysis_ids",
        )
        for p_item in st.session_state.portfolio:
            col_id, col_btn = st.columns([4, 1])
            with col_id:
                epc = p_item.get("epc_band", "N/A")
                st.markdown(
                    f"<div style='font-size:0.8rem;color:#CBD8E6;padding-top:5px;'>"
                    f"{p_item['postcode']} (EPC: {epc})</div>",
                    unsafe_allow_html=True,
                )
            with col_btn:
                if st.button("\u274c", key=f"del_{p_item['id']}", help="Remove asset"):
                    remove_from_portfolio(p_item["id"])
                    st.rerun()
    else:
        st.markdown(
            "<div style='font-size:0.8rem;color:#5A7A90;font-style:italic;'>"
            "Portfolio empty. Add a postcode above.</div>",
            unsafe_allow_html=True,
        )


def _render_location():
    st.markdown("<div class='sb-section'>\U0001f4cd Location</div>", unsafe_allow_html=True)
    _city_list = loc.city_options()
    _wx_city = st.session_state.get("wx_city", "Reading, Berkshire")
    _city_idx = _city_list.index(_wx_city) if _wx_city in _city_list else 0
    _sel_city = st.selectbox("City / Region", _city_list, index=_city_idx, label_visibility="collapsed")
    if _sel_city != st.session_state.get("wx_city"):
        _meta = loc.city_meta(_sel_city)
        st.session_state.wx_city = _sel_city
        st.session_state.wx_lat = _meta["lat"]
        st.session_state.wx_lon = _meta["lon"]
        st.session_state.wx_location_name = f"{_sel_city}, {_meta.get('country','UK')}"
        st.session_state.force_weather_refresh = True
        audit.log_event("LOCATION_CHANGED", f"City set to '{_sel_city}'")
        _update_query_params()

    with st.expander("\u2699 Custom coordinates", expanded=False):
        _col_lat, _col_lon = st.columns(2)
        with _col_lat:
            _clat = st.number_input("Latitude", value=float(st.session_state.get("wx_lat", 51.4543)),
                                    min_value=-90.0, max_value=90.0, format="%.4f", step=0.0001)
        with _col_lon:
            _clon = st.number_input("Longitude", value=float(st.session_state.get("wx_lon", -0.9781)),
                                    min_value=-180.0, max_value=180.0, format="%.4f", step=0.0001)
        if st.button("Apply coordinates", key="apply_coords", use_container_width=True):
            st.session_state.wx_lat = _clat
            st.session_state.wx_lon = _clon
            st.session_state.wx_location_name = f"Custom site ({_clat:.4f}, {_clon:.4f})"
            st.session_state.force_weather_refresh = True
            audit.log_event("LOCATION_CUSTOM", f"Custom: {_clat:.4f}, {_clon:.4f}")
            _update_query_params()
        st.markdown(
            "<div style='font-size:0.73rem;color:#8FBCCE;margin-top:4px;'>"
            "Or use browser geolocation (HTTPS only):</div>",
            unsafe_allow_html=True,
        )

    _geo = loc.render_geo_detect()
    if _geo and isinstance(_geo, dict):
        try:
            _lat = float(_geo.get("lat"))
            _lon = float(_geo.get("lon"))
            _resolved = loc.nearest_city(_lat, _lon)
            st.session_state.wx_city = _resolved
            st.session_state.wx_lat = _lat
            st.session_state.wx_lon = _lon
            _country = loc.CITIES.get(_resolved, {}).get("country", "UK")
            st.session_state.wx_location_name = f"{_resolved}, {_country}"
            st.session_state.force_weather_refresh = True
            audit.log_event("LOCATION_AUTO", f"Browser \u2192 '{_resolved}'")
            _update_query_params()
        except Exception:
            pass


def _render_weather() -> dict:
    st.markdown("<div class='sb-section'>\U0001f324 Live Weather</div>", unsafe_allow_html=True)
    if st.button("\u21bb Refresh Weather", key="wx_refresh", use_container_width=True):
        st.session_state.force_weather_refresh = True

    manual_t = st.slider(
        "Manual temperature override (\u00b0C)", -10.0, 35.0,
        float(st.session_state.get("manual_temp", 10.5)), 0.5,
        key="_manual_temp_slider",
    )
    st.session_state.manual_temp = manual_t

    with st.spinner("Checking weather\u2026"):
        try:
            weather = weather_service.get_weather(
                lat=st.session_state.get("wx_lat", 51.4543),
                lon=st.session_state.get("wx_lon", -0.9781),
                location_name=st.session_state.get("wx_location_name", "Reading, Berkshire, UK"),
                provider=st.session_state.get("wx_provider", "open_meteo"),
                met_office_key=st.session_state.get("met_office_key") or None,
                openweathermap_key=st.session_state.get("owm_key") or None,
                enable_fallback=st.session_state.get("wx_enable_fallback", True),
                manual_temp_c=manual_t,
                force_refresh=st.session_state.get("force_weather_refresh", False),
            )
        except Exception as exc:
            st.warning(f"Could not fetch weather: {exc}")
            weather = {
                "temperature_c": manual_t, "condition": "Manual override",
                "condition_icon": "\U0001f321", "wind_speed_mph": 0,
                "wind_dir_deg": 0, "humidity_pct": 0, "feels_like_c": manual_t,
                "is_live": False, "source": "Manual override", "fetched_utc": "",
                "location_name": st.session_state.get("wx_location_name", "Unknown"),
            }
    st.session_state.force_weather_refresh = False

    if weather.get("is_live"):
        try:
            mins_ago = weather_service.minutes_since_fetch(weather.get("fetched_utc", ""))
        except Exception:
            mins_ago = "?"
        s_class, s_dot, s_text = "sp sp-live", "<span class='pulse-dot'></span>", f"Live \u00b7 {mins_ago}m ago"
    else:
        s_class, s_dot, s_text = "sp sp-manual", "\u25cb", "Manual override"

    try:
        wdir_lbl = weather_service.wind_compass(weather.get("wind_dir_deg", 0))
    except Exception:
        wdir_lbl = "N"

    st.markdown(
        f"<div class='wx-widget'>"
        f"<div style='display:flex;justify-content:space-between;align-items:flex-start;'>"
        f"<div><div style='font-size:1.4rem;line-height:1;'>{weather.get('condition_icon','\U0001f321')}</div>"
        f"<div class='wx-temp'>{weather.get('temperature_c','?')}\u00b0C</div>"
        f"<div class='wx-desc'>{weather.get('condition','')}</div></div>"
        f"<div style='text-align:right;'><div style='font-size:0.76rem;color:#8FBCCE;'>"
        f"{weather.get('location_name','')}</div></div></div>"
        f"<div class='wx-row'>\U0001f4a8 {weather.get('wind_speed_mph',0)} mph {wdir_lbl} &nbsp;|&nbsp;"
        f"\U0001f4a7 {weather.get('humidity_pct',0)}% &nbsp;|&nbsp;"
        f"\U0001f321 {weather.get('feels_like_c','?')}\u00b0C feels like</div>"
        f"<div style='margin-top:6px;'><span class='{s_class}'>{s_dot} {s_text}</span></div>"
        f"</div>",
        unsafe_allow_html=True,
    )
    st.caption(f"\U0001f4e1 {weather.get('source','Open-Meteo')}")
    return weather


def _render_api_keys():
    with st.expander("\U0001f511 API Keys & Weather Config", expanded=False):
        st.markdown(
            "<div style='background:#FFF3CD;border:1px solid #FFD89B;border-radius:6px;padding:10px;'>"
            "<div style='font-size:0.75rem;color:#664D03;font-weight:700;margin-bottom:6px;'>"
            "\U0001f512 Security Notice</div>"
            "<div style='font-size:0.78rem;color:#664D03;line-height:1.5;'>"
            "\u2022 Keys exist in your session only (cleared on browser close)<br/>"
            "\u2022 Your keys are <strong>never</strong> stored on the server<br/>"
            "\u2022 Each user enters their own key independently<br/>"
            "\u2022 Use unique, disposable API keys if sharing this link"
            "</div></div>",
            unsafe_allow_html=True,
        )
        st.markdown("")
        st.markdown(
            "<div style='font-size:0.78rem;color:#8FBCCE;font-weight:700;"
            "letter-spacing:0.5px;margin:8px 0 4px;'>WEATHER PROVIDER</div>",
            unsafe_allow_html=True,
        )
        _plabels = {
            "open_meteo": "Open-Meteo (free, no key)",
            "openweathermap": "OpenWeatherMap (key required)",
            "met_office": "Met Office DataPoint (UK, key required)",
        }
        _pkeys = list(_plabels.keys())
        _cur = st.session_state.get("wx_provider", "open_meteo")
        _sel_prov = st.selectbox(
            "Weather provider", _pkeys, index=_pkeys.index(_cur) if _cur in _pkeys else 0,
            format_func=lambda k: _plabels[k], label_visibility="collapsed",
        )
        if _sel_prov != st.session_state.get("wx_provider"):
            _prev = st.session_state.get("wx_provider", "open_meteo")
            st.session_state.wx_provider = _sel_prov
            st.session_state.force_weather_refresh = True
            audit.log_event("PROVIDER_CHANGED", f"{_plabels[_prev]} \u2192 {_plabels[_sel_prov]}")

        _fb = st.checkbox("Fall back to Open-Meteo if primary fails",
                          value=st.session_state.get("wx_enable_fallback", True))
        if _fb != st.session_state.get("wx_enable_fallback"):
            st.session_state.wx_enable_fallback = _fb

        st.markdown("---")
        _show_owm = st.checkbox("Show OWM key", key="show_owm_key", value=False)
        _owm_val = st.session_state.get("owm_key", "")
        _owm_key = st.text_input(
            "OpenWeatherMap API key",
            type="default" if _show_owm else "password",
            placeholder="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            value=_owm_val,
            help="Free at openweathermap.org/api",
        )
        if _owm_key != _owm_val:
            st.session_state.owm_key = _owm_key
            audit.log_event("KEY_UPDATED", "OWM key " + ("updated" if _owm_val else "added"))
        if st.session_state.get("owm_key"):
            if st.button("Test OWM key", key="test_owm_key", use_container_width=True):
                try:
                    _ok, _msg = weather_service.test_openweathermap_key(
                        st.session_state.owm_key,
                        st.session_state.get("wx_lat", 51.4543),
                        st.session_state.get("wx_lon", -0.9781),
                    )
                    st.markdown(
                        f"<div class='{'val-ok' if _ok else 'val-err'}'>"
                        f"{'&#10003;' if _ok else '&#10007;'} {_msg}</div>",
                        unsafe_allow_html=True,
                    )
                except Exception as exc:
                    st.markdown(f"<div class='val-err'>&#10007; {exc}</div>", unsafe_allow_html=True)

        st.markdown("---")
        _show_mo = st.checkbox("Show Met Office key", key="show_mo_key", value=False)
        _mo_val = st.session_state.get("met_office_key", "")
        _mo_key = st.text_input(
            "Met Office DataPoint key",
            type="default" if _show_mo else "password",
            value=_mo_val,
            help="Free at metoffice.gov.uk/services/data/datapoint",
        )
        if _mo_key != _mo_val:
            st.session_state.met_office_key = _mo_key
            audit.log_event("KEY_UPDATED", "Met Office key " + ("updated" if _mo_val else "added"))
        if st.session_state.get("met_office_key"):
            if st.button("Test Met Office key", key="test_mo_key", use_container_width=True):
                try:
                    _ok, _msg = weather_service.test_met_office_key(st.session_state.met_office_key)
                    st.markdown(
                        f"<div class='{'val-ok' if _ok else 'val-err'}'>"
                        f"{'&#10003;' if _ok else '&#10007;'} {_msg}</div>",
                        unsafe_allow_html=True,
                    )
                except Exception as exc:
                    st.markdown(f"<div class='val-err'>&#10007; {exc}</div>", unsafe_allow_html=True)

        st.markdown("---")
        _show_gm = st.checkbox("Show Gemini key", key="show_gm_key", value=False)
        _gm_val = st.session_state.get("gemini_key", "")
        _gm_key = st.text_input(
            "Gemini API key (for AI Advisor)",
            type="default" if _show_gm else "password",
            placeholder="AIzaSy\u2026 (starts with 'AIza')",
            value=_gm_val,
            help="Get key at aistudio.google.com",
        )
        if _gm_key != _gm_val:
            st.session_state.gemini_key = _gm_key
        if st.session_state.get("gemini_key"):
            if not st.session_state.gemini_key.startswith("AIza"):
                st.markdown(
                    "<div class='val-warn'>\u26a0 Gemini key should start with 'AIza'</div>",
                    unsafe_allow_html=True,
                )
            else:
                try:
                    valid, message, warn = validate_gemini_key(st.session_state.gemini_key)
                    st.markdown(message, unsafe_allow_html=True)
                    st.session_state.gemini_key_valid = valid or warn
                except Exception:
                    pass


def _render_audit_log():
    try:
        _log_entries = audit.get_log(n=5)
    except Exception:
        return
    if not _log_entries:
        return
    with st.expander("\U0001f50d Config Change Log", expanded=False):
        st.markdown(
            "<div style='font-size:0.72rem;color:#8FBCCE;margin-bottom:4px;'>"
            "In-session only \u2014 cleared on browser close.</div>",
            unsafe_allow_html=True,
        )
        for _e in _log_entries:
            st.markdown(
                f"<div style='font-size:0.72rem;line-height:1.5;"
                f"border-left:2px solid #1A3A5C;padding-left:6px;margin-bottom:4px;'>"
                f"<span style='color:#00C2A8;'>{_e.get('action','')}</span><br/>"
                f"<span style='color:#CBD8E6;'>{_e.get('details','')}</span><br/>"
                f"<span style='color:#5A7A90;font-size:0.68rem;'>{_e.get('ts','')}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )


def _render_data_sources_and_footer():
    st.markdown("<div class='sb-section'>\U0001f4da Data Sources</div>", unsafe_allow_html=True)
    for src in [
        "Open-Meteo (weather, default)",
        "Met Office DataPoint (UK, optional)",
        "OpenWeatherMap (global, optional)",
        "GeoNames (city dataset, CC-BY)",
        "BEIS GHG Factors 2023",
        "HESA Estates Stats 2022-23",
        "CIBSE Guide A",
        "PVGIS (EC JRC)",
        "Raissi et al. (2019)",
    ]:
        st.caption(f"\u00b7 {src}")
    st.markdown("---")
    logo_uri = get_logo_uri()
    _footer_logo = (
        f"<img src='{logo_uri}' height='28' style='vertical-align:middle;"
        "display:inline-block;height:28px;width:auto;' alt='CrowAgent\u2122 Logo'/>"
        if logo_uri
        else "<span style='font-family:Rajdhani,sans-serif;font-size:1.1rem;font-weight:700;"
             "color:#00C2A8;'>CrowAgent\u2122</span>"
    )
    st.markdown(
        f"<div class='ent-footer'>{_footer_logo}"
        f"<div style='font-size:0.76rem;color:#9ABDD0;line-height:1.6;margin-top:8px;'>"
        f"\u00a9 2026 Aparajita Parihar<br/>CrowAgent\u2122 \u00b7 All rights reserved<br/>"
        f"v2.0.0 \u00b7 Prototype</div></div>",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# MAIN RENDER ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def render_sidebar() -> tuple[str | None, dict, str]:
    """
    Renders the full sidebar. Returns (segment_id, weather_dict, location_name).
    If no segment selected, renders the onboarding gate and returns (None, {}, "").
    """
    segment = st.session_state.get("user_segment")
    if not segment:
        _render_segment_gate()
        return None, {}, ""

    weather: dict = {}
    with st.sidebar:
        _render_sidebar_logo(segment)
        _render_scenario_selector(segment)
        st.markdown("---")
        _render_portfolio_controls(segment)
        st.markdown("---")
        _render_location()
        st.markdown("---")
        weather = _render_weather()
        st.markdown("---")
        _render_api_keys()
        st.markdown("---")
        _render_audit_log()
        _render_data_sources_and_footer()

    location = st.session_state.get("wx_location_name", "Reading, Berkshire, UK")
    return segment, weather, location
