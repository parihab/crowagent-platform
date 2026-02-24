# ═══════════════════════════════════════════════════════════════════════════════
# CrowAgent™ Platform — 3D/4D Spatial Visualisation Module
# © 2026 Aparajita Parihar. All rights reserved.
#
# Zero-cost external services used:
#   pydeck (MIT licence)       — deck.gl Python bindings (pip install pydeck)
#   CARTO Basemaps (free tier) — MapLibre GL style, no API key required
#                                https://basemaps.cartocdn.com
#
# No Mapbox token, no Google Maps API, no paid tile services required.
# ═══════════════════════════════════════════════════════════════════════════════

from __future__ import annotations

import pandas as pd
import streamlit as st

try:
    import pydeck as pdk
    _PYDECK_AVAILABLE = True
except ImportError:
    _PYDECK_AVAILABLE = False

# ── Fictional Greenfield University campus coordinates (Reading, Berkshire) ──
# Buildings are placed ~150 m apart — realistic for a campus layout.
_BUILDING_COORDS: dict[str, dict[str, float]] = {
    "Greenfield Library":       {"lat": 51.4545, "lon": -0.9712},
    "Greenfield Arts Building": {"lat": 51.4558, "lon": -0.9695},
    "Greenfield Science Block": {"lat": 51.4533, "lon": -0.9730},
}

# ── Free basemap — CARTO Dark Matter (MapLibre GL compatible, no API key) ────
_MAP_STYLE = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"

# ── UK monthly average temperatures °C — Reading, Berkshire (Met Office) ─────
_MONTHLY_TEMPS: dict[int, float] = {
    1: 5.0, 2: 5.2, 3: 7.6,  4: 10.3, 5: 13.8, 6: 16.9,
    7: 19.7, 8: 19.2, 9: 15.9, 10: 12.0, 11: 8.1, 12: 5.8,
}
_MONTH_NAMES = {
    1: "January", 2: "February", 3: "March",    4: "April",
    5: "May",     6: "June",     7: "July",      8: "August",
    9: "September", 10: "October", 11: "November", 12: "December",
}

# ── Seasonal energy model constants ──────────────────────────────────────────
# ~60% of UK campus energy is heating-related (HESA 2022-23 sector data).
# The remaining 40% (lighting, equipment, hot water) is roughly flat year-round.
# Heating load scales with heating degree days vs. the annual average.
_HEATING_FRACTION = 0.60
_UK_ANNUAL_AVG_TEMP_C = 11.0   # °C — UK annual mean (Met Office 1991–2020)
_SETPOINT_C = 21.0             # Part L heating set-point


def _seasonal_energy_mwh(baseline_mwh: float, month_temp: float) -> float:
    """
    Scale annual baseline energy to a monthly-temperature-equivalent figure.
    Uses a simplified heating degree day (HDD) ratio:
      total = non_heating_base + heating_base × (HDD_month / HDD_annual_avg)
    """
    annual_hdd = max(0.0, _SETPOINT_C - _UK_ANNUAL_AVG_TEMP_C)
    month_hdd  = max(0.0, _SETPOINT_C - month_temp)
    hdd_factor = (month_hdd / annual_hdd) if annual_hdd > 0 else 1.0
    return ((1.0 - _HEATING_FRACTION) * baseline_mwh
            + _HEATING_FRACTION * baseline_mwh * hdd_factor)


# ─────────────────────────────────────────────────────────────────────────────
# COLOUR HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _carbon_to_rgba(carbon_t: float, min_c: float, max_c: float) -> list[int]:
    """
    Map a carbon value to an RGBA colour on a three-stop gradient:
      Low carbon  → teal  [0, 194, 168]
      Mid carbon  → amber [255, 165, 0]
      High carbon → red   [220, 50, 50]
    """
    ratio = (carbon_t - min_c) / (max_c - min_c) if max_c > min_c else 0.0
    ratio = max(0.0, min(1.0, ratio))

    if ratio < 0.5:
        t = ratio * 2.0
        r = int(t * 255)
        g = int(194 + t * (165 - 194))
        b = int(168 - t * 168)
    else:
        t = (ratio - 0.5) * 2.0
        r = int(255 - t * 35)
        g = int(165 - t * 115)
        b = int(t * 50)

    return [r, g, b, 210]


# ─────────────────────────────────────────────────────────────────────────────
# DATA HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _compute_all_buildings(scenario_name: str, weather: dict) -> list[dict]:
    """
    Run the physics engine for all 3 campus buildings under one scenario.
    Returns a list of row-dicts ready for pydeck, with fill_color and elevation
    already calculated.
    """
    from core.physics import BUILDINGS, SCENARIOS, calculate_thermal_load

    scenario_cfg = SCENARIOS.get(scenario_name)
    if scenario_cfg is None:
        return []

    rows: list[dict] = []
    carbon_values: list[float] = []

    for bname, bdata in BUILDINGS.items():
        coords = _BUILDING_COORDS.get(bname)
        if coords is None:
            continue
        try:
            res = calculate_thermal_load(bdata, scenario_cfg, weather)
        except Exception:
            continue

        rows.append({
            "name":              bname,
            "lat":               coords["lat"],
            "lon":               coords["lon"],
            "energy_mwh":        round(res["scenario_energy_mwh"], 1),
            "carbon_t":          round(res["scenario_carbon_t"], 1),
            "carbon_saving_t":   round(res["carbon_saving_t"], 1),
            "energy_saving_pct": round(res["energy_saving_pct"], 1),
        })
        carbon_values.append(res["scenario_carbon_t"])

    if not rows:
        return []

    min_c = min(carbon_values)
    max_c = max(carbon_values)

    for row in rows:
        row["fill_color"] = _carbon_to_rgba(row["carbon_t"], min_c, max_c)
        # Column height: proportional to energy (visual scale, not metres)
        row["elevation"] = max(20, row["energy_mwh"] * 0.5)

    return rows


# ─────────────────────────────────────────────────────────────────────────────
# DECK BUILDER
# ─────────────────────────────────────────────────────────────────────────────

_TOOLTIP_HTML = """
<div style='background:#071A2F;color:#E0EAF0;padding:10px 14px;
            border-radius:6px;font-family:Nunito Sans,sans-serif;
            border-left:3px solid #00C2A8;min-width:190px;'>
  <div style='font-weight:700;color:#00C2A8;margin-bottom:6px;
              font-size:0.88rem;'>{name}</div>
  <div style='font-size:0.80rem;line-height:1.9;'>
    ⚡ <strong>{energy_mwh}</strong> MWh/yr<br/>
    🌍 <strong>{carbon_t}</strong> t CO₂e/yr<br/>
    ↓ Carbon saved: <strong>{carbon_saving_t}</strong> t
    &nbsp;(<strong>{energy_saving_pct}%</strong>)
  </div>
</div>"""

_TOOLTIP_HTML_4D = """
<div style='background:#071A2F;color:#E0EAF0;padding:10px 14px;
            border-radius:6px;font-family:Nunito Sans,sans-serif;
            border-left:3px solid #00C2A8;min-width:190px;'>
  <div style='font-weight:700;color:#00C2A8;margin-bottom:6px;
              font-size:0.88rem;'>{name}</div>
  <div style='font-size:0.80rem;line-height:1.9;'>
    ⚡ <strong>{energy_mwh}</strong> MWh/yr (seasonal)<br/>
    🌍 <strong>{carbon_t}</strong> t CO₂e/yr
  </div>
</div>"""


def _build_deck(rows: list[dict], tooltip_html: str = _TOOLTIP_HTML) -> "pdk.Deck":
    """Assemble a pydeck Deck from pre-computed building rows."""
    df = pd.DataFrame(rows)

    column_layer = pdk.Layer(
        "ColumnLayer",
        data=df,
        get_position="[lon, lat]",
        get_elevation="elevation",
        elevation_scale=1,
        radius=45,
        get_fill_color="fill_color",
        pickable=True,
        auto_highlight=True,
        extruded=True,
        coverage=1,
    )

    view = pdk.ViewState(
        latitude=51.4545,
        longitude=-0.9712,
        zoom=15.5,
        pitch=50,
        bearing=-10,
    )

    return pdk.Deck(
        layers=[column_layer],
        initial_view_state=view,
        tooltip={"html": tooltip_html,
                 "style": {"backgroundColor": "transparent", "border": "none"}},
        map_style=_MAP_STYLE,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2D FALLBACK
# ─────────────────────────────────────────────────────────────────────────────

def _render_2d_fallback(rows: list[dict]) -> None:
    """Plotly bar chart shown when WebGL / pydeck is unavailable."""
    import plotly.graph_objects as go

    fig = go.Figure()
    for row in rows:
        r, g, b = row["fill_color"][:3]
        fig.add_trace(go.Bar(
            x=[row["name"].replace("Greenfield ", "")],
            y=[row["energy_mwh"]],
            name=row["name"],
            marker_color=f"rgba({r},{g},{b},0.85)",
            text=[f"{row['energy_mwh']:.0f} MWh"],
            textposition="outside",
        ))

    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Nunito Sans, sans-serif", size=11, color="#E0EAF0"),
        margin=dict(t=20, b=10, l=0, r=0),
        height=260,
        yaxis=dict(gridcolor="#1A3A5C", title="MWh/yr"),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.caption("2D fallback — 3D map requires a WebGL-capable browser (Chrome / Firefox)")


# ─────────────────────────────────────────────────────────────────────────────
# 3D MAP VIEW
# ─────────────────────────────────────────────────────────────────────────────

def _render_3d_map(scenario_name: str, weather: dict) -> None:
    """Render the static 3D column map for the selected scenario."""
    rows = _compute_all_buildings(scenario_name, weather)
    if not rows:
        st.info("No building data available for the selected scenario.")
        return

    try:
        deck = _build_deck(rows)
        st.pydeck_chart(deck, use_container_width=True)
    except Exception as exc:
        st.warning(f"3D map could not render ({exc}). Showing 2D fallback.")
        _render_2d_fallback(rows)


# ─────────────────────────────────────────────────────────────────────────────
# 4D TIMELINE VIEW
# ─────────────────────────────────────────────────────────────────────────────

def _render_4d_timeline(weather: dict) -> None:
    """
    4D mode: scrub through Jan–Dec with a time slider.
    Monthly energy/carbon is computed via the seasonal HDD model so that
    winter months show taller/redder columns than summer months, reflecting
    real UK heating demand patterns.
    """
    from core.physics import BUILDINGS

    _CI = 0.20482   # BEIS 2023 kgCO2e / kWh

    month = st.slider(
        "Month",
        min_value=1, max_value=12, value=1,
        help="Scrub Jan–Dec to see seasonal energy & carbon variation across the campus",
        key="viz3d_month_slider",
    )

    month_temp = _MONTHLY_TEMPS[month]
    rows: list[dict] = []
    carbon_values: list[float] = []

    for bname, bdata in BUILDINGS.items():
        coords = _BUILDING_COORDS.get(bname)
        if coords is None:
            continue

        energy_mwh = round(_seasonal_energy_mwh(bdata["baseline_energy_mwh"], month_temp), 1)
        carbon_t   = round(energy_mwh * 1000.0 * _CI / 1000.0, 1)

        rows.append({
            "name":              bname,
            "lat":               coords["lat"],
            "lon":               coords["lon"],
            "energy_mwh":        energy_mwh,
            "carbon_t":          carbon_t,
            "carbon_saving_t":   0.0,
            "energy_saving_pct": 0.0,
        })
        carbon_values.append(carbon_t)

    if not rows:
        return

    min_c = min(carbon_values)
    max_c = max(carbon_values) if max(carbon_values) > min_c else min_c + 1.0

    for row in rows:
        row["fill_color"] = _carbon_to_rgba(row["carbon_t"], min_c, max_c)
        row["elevation"]  = max(20, row["energy_mwh"] * 0.5)

    avg_carbon = sum(r["carbon_t"] for r in rows) / len(rows)
    st.markdown(
        f"<div style='font-size:0.82rem;color:#00C2A8;font-weight:600;"
        f"margin-bottom:6px;'>"
        f"📅 {_MONTH_NAMES[month]} — Campus avg. carbon: {avg_carbon:.1f} t CO₂e "
        f"&nbsp;·&nbsp; Outdoor temp: {month_temp}°C</div>",
        unsafe_allow_html=True,
    )

    try:
        deck = _build_deck(rows, tooltip_html=_TOOLTIP_HTML_4D)
        st.pydeck_chart(deck, use_container_width=True)
    except Exception as exc:
        st.warning(f"3D map could not render ({exc})")
        _render_2d_fallback(rows)


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC ENTRY POINT — called from app/main.py Dashboard tab
# ─────────────────────────────────────────────────────────────────────────────

def render_campus_3d_map(selected_scenario_names: list[str], weather: dict) -> None:
    """
    Renders the 3D/4D campus energy & carbon map section on the Dashboard tab.

    Shows all 3 Greenfield University buildings as interactive 3D columns:
      - Column height  = energy consumption (MWh/yr)
      - Column colour  = carbon intensity   (teal = low → red = high)

    Two modes:
      3D Energy Map       — static view for any selected scenario
      4D Carbon Timeline  — seasonal scrubber using UK monthly temperature norms

    Parameters
    ----------
    selected_scenario_names : list[str]
        Scenarios currently selected in the sidebar multiselect.
    weather : dict
        Live or manual weather data from services/weather.py.
    """
    if not _PYDECK_AVAILABLE:
        st.warning(
            "3D visualisation requires **pydeck**. "
            "Run `pip install pydeck>=0.8.0` and restart the app.",
            icon="🗺️",
        )
        return

    st.markdown(
        "<div class='sec-hdr'>🗺️ 3D Campus Energy & Carbon Map</div>",
        unsafe_allow_html=True,
    )

    # ── View mode + scenario selector ────────────────────────────────────────
    ctrl_l, ctrl_r = st.columns([3, 2])

    with ctrl_l:
        view_mode = st.radio(
            "Visualisation mode",
            ["3D Energy Map", "4D Carbon Timeline"],
            horizontal=True,
            label_visibility="collapsed",
            key="viz3d_mode",
        )

    with ctrl_r:
        if view_mode == "3D Energy Map":
            scenario_for_map = st.selectbox(
                "Scenario",
                selected_scenario_names,
                key="viz3d_scenario",
                label_visibility="collapsed",
            )
        else:
            st.markdown(
                "<div style='font-size:0.75rem;color:#5A7A90;padding-top:8px;'>"
                "Baseline · seasonal temperature profile</div>",
                unsafe_allow_html=True,
            )
            scenario_for_map = "Baseline (No Intervention)"

    # ── Render chosen mode ───────────────────────────────────────────────────
    if view_mode == "3D Energy Map":
        _render_3d_map(scenario_for_map, weather)
    else:
        _render_4d_timeline(weather)

    # ── Legend ───────────────────────────────────────────────────────────────
    st.markdown("""
<div style='display:flex;gap:20px;align-items:center;flex-wrap:wrap;
            font-size:0.74rem;color:#8FBCCE;margin-top:6px;'>
  <span style='display:flex;align-items:center;gap:5px;'>
    <span style='display:inline-block;width:12px;height:12px;
                 background:#00C2A8;border-radius:2px;'></span>Low carbon
  </span>
  <span style='display:flex;align-items:center;gap:5px;'>
    <span style='display:inline-block;width:12px;height:12px;
                 background:#FFA500;border-radius:2px;'></span>Medium
  </span>
  <span style='display:flex;align-items:center;gap:5px;'>
    <span style='display:inline-block;width:12px;height:12px;
                 background:#DC3232;border-radius:2px;'></span>High carbon
  </span>
  <span style='font-size:0.70rem;color:#3A5A70;margin-left:auto;'>
    Height = energy consumption &nbsp;·&nbsp;
    Tiles: © CARTO &nbsp;·&nbsp; Data: © OpenStreetMap contributors
  </span>
</div>
    """, unsafe_allow_html=True)

    st.markdown(
        "<div style='font-size:0.71rem;color:#3A5A70;margin-top:2px;'>"
        "WebGL required · Hover to inspect · Drag to rotate · Scroll to zoom · "
        "Zero-cost: pydeck MIT + CARTO free basemap · "
        "⚠️ Coordinates are illustrative — fictional Greenfield campus</div>",
        unsafe_allow_html=True,
    )
