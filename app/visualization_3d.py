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

import math
import requests
from typing import Dict, List

import overpy
import pandas as pd
import streamlit as st

try:
    import pydeck as pdk
    _PYDECK_AVAILABLE = True
except ImportError:
    _PYDECK_AVAILABLE = False

# ── Fictional Greenfield University — building offsets from city centre ───────
# Expressed as (north_m, east_m) so the campus auto-relocates to whatever
# city the user has selected; positions are ~100-200 m apart (campus-scale).
_BUILDING_OFFSETS: dict[str, tuple[float, float]] = {
    "Greenfield Library":       (  60,  -130),   # NW of centre
    "Greenfield Arts Building": ( 170,   110),   # NE of centre
    "Greenfield Science Block": (-150,    70),   # SE of centre
}

# Fallback/default centre (Reading, Berkshire) — overridden at runtime.
_DEFAULT_LAT = 51.4543
_DEFAULT_LON = -0.9781

# ── Basemap styles — CARTO free tier, no API key needed ──────────────────────
# Positron = light / Google Maps-like (used for 3D Energy Map)
# Dark Matter = dark (used for 4D Carbon Timeline for contrast)
_MAP_STYLE_LIGHT = "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
_MAP_STYLE_DARK  = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"

# ── UK monthly average temperatures °C — Reading, Berkshire (Met Office) ─────
_MONTHLY_TEMPS: dict[int, float] = {
    1: 5.0, 2: 5.2, 3: 7.6,  4: 10.3, 5: 13.8, 6: 16.9,
    7: 19.7, 8: 19.2, 9: 15.9, 10: 12.0, 11: 8.1, 12: 5.8,
}
_MONTH_NAMES: List[str] = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

# ── Seasonal energy model constants ──────────────────────────────────────────
# ~60% of UK campus energy is heating-related (HESA 2022-23 sector data).
# The remaining 40% (lighting, equipment, hot water) is roughly flat year-round.
# Heating load scales with heating degree days vs. the annual average.
_HEATING_FRACTION = 0.60
_UK_ANNUAL_AVG_TEMP_C = 11.0   # °C — UK annual mean (Met Office 1991–2020)
_SETPOINT_C = 21.0             # Part L heating set-point

# ── Emissions & cost constants ────────────────────────────────────────────────
_CI               = 0.20482   # kgCO₂e/kWh  (BEIS 2023 grid intensity)
_ELEC_GBP_PER_KWH = 0.28      # £/kWh        (HESA 2022-23 HE sector average)

# ── Building display icons ────────────────────────────────────────────────────
_BUILDING_ICONS: dict[str, str] = {
    "Greenfield Library":       "📚",
    "Greenfield Arts Building": "🎨",
    "Greenfield Science Block": "🔬",
}


def _get_map_center() -> tuple[float, float, str]:
    """Return (lat, lon, location_name) from session state.

    Falls back to Reading, Berkshire when running outside Streamlit (e.g. tests).
    """
    lat  = st.session_state.get("wx_lat",  _DEFAULT_LAT)
    lon  = st.session_state.get("wx_lon",  _DEFAULT_LON)
    name = st.session_state.get("wx_location_name", "Reading, Berkshire, UK")
    return float(lat), float(lon), str(name)


def _building_coords(center_lat: float, center_lon: float) -> dict[str, dict]:
    """Compute absolute lat/lon for each fictional campus building.

    Offsets in ``_BUILDING_OFFSETS`` (metres) are converted to degrees
    at the given centre, so the campus relocates with the selected location.
    """
    cos_lat = math.cos(math.radians(center_lat))
    result: dict[str, dict] = {}
    for bname, (north_m, east_m) in _BUILDING_OFFSETS.items():
        result[bname] = {
            "lat": center_lat + north_m / 111_000.0,
            "lon": center_lon + east_m / (111_000.0 * cos_lat),
        }
    return result


def _synthetic_polygon(lat: float, lon: float, size_m: float = 38.0) -> list[list[float]]:
    """Return a closed square polygon ([[lon,lat], …]) centred at (lat, lon).

    Used as a fallback when no OSM footprint can be matched to a campus building.
    """
    cos_lat = math.cos(math.radians(lat))
    d_lat   = size_m / 111_000.0
    d_lon   = size_m / (111_000.0 * cos_lat)
    return [
        [lon - d_lon, lat - d_lat],
        [lon + d_lon, lat - d_lat],
        [lon + d_lon, lat + d_lat],
        [lon - d_lon, lat + d_lat],
        [lon - d_lon, lat - d_lat],   # close ring
    ]


def _osm_centroid(polygon: list[list[float]]) -> tuple[float, float]:
    """Return (lat, lon) centroid of a [[lon,lat], …] polygon ring."""
    lons = [p[0] for p in polygon]
    lats = [p[1] for p in polygon]
    return sum(lats) / len(lats), sum(lons) / len(lons)


def _assign_osm_polygons(
    building_rows: list[dict],
    osm_rows: list[dict],
) -> list[dict]:
    """Match each campus building to its nearest unassigned OSM polygon.

    Each row in *building_rows* must have ``lat`` and ``lon`` keys.
    A ``polygon`` key ([[lon,lat],…]) is added to each row in-place and
    the augmented list is returned.  Unmatched buildings fall back to a
    synthetic square polygon so the app never crashes on empty OSM data.
    """
    used: set[int] = set()
    result: list[dict] = []

    for row in building_rows:
        b_lat, b_lon = row["lat"], row["lon"]
        best_i, best_dist = None, float("inf")

        for i, osm in enumerate(osm_rows):
            if i in used:
                continue
            c_lat, c_lon = _osm_centroid(osm["polygon"])
            dist = math.hypot(c_lat - b_lat, c_lon - b_lon)
            if dist < best_dist:
                best_dist, best_i = dist, i

        if best_i is not None:
            used.add(best_i)
            polygon  = osm_rows[best_i]["polygon"]
            height_m = osm_rows[best_i].get("height_m", 12.0)
        else:
            polygon  = _synthetic_polygon(b_lat, b_lon)
            height_m = 12.0

        result.append({**row, "polygon": polygon, "height_m": height_m})

    return result


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

def _compute_all_buildings(
    scenario_name: str,
    weather: dict,
    center_lat: float,
    center_lon: float,
) -> list[dict]:
    """
    Run the physics engine for all campus buildings under *scenario_name*.

    Returns row-dicts suitable for pydeck's PolygonLayer.  Physical heights
    (``elevation``) start at a campus default and are later overridden by the
    real OSM footprint height once polygon assignment has run.

    Each row includes both baseline and scenario energy/carbon figures so the
    tooltip can show the full comparison in one hover card.
    """
    from core.physics import BUILDINGS, SCENARIOS, calculate_thermal_load

    scenario_cfg = SCENARIOS.get(scenario_name)
    if scenario_cfg is None:
        return []

    bcoords = _building_coords(center_lat, center_lon)
    rows: list[dict] = []

    for bname, bdata in BUILDINGS.items():
        coords = bcoords.get(bname)
        if coords is None:
            continue
        try:
            res = calculate_thermal_load(bdata, scenario_cfg, weather)
        except Exception:
            continue

        payback = res.get("payback_years")
        cost_k  = round(res["scenario_energy_mwh"] * 1000 * _ELEC_GBP_PER_KWH / 1000, 1)

        rows.append({
            # Identity
            "name":                 bname,
            "building_type":        bdata.get("building_type", "University Building"),
            "lat":                  coords["lat"],
            "lon":                  coords["lon"],
            # Scenario comparison — shown in tooltip
            "scenario":             scenario_name,
            "baseline_energy_mwh":  round(res["baseline_energy_mwh"], 1),
            "energy_mwh":           round(res["scenario_energy_mwh"], 1),
            "energy_saving_pct":    round(res["energy_saving_pct"], 1),
            "baseline_carbon_t":    round(res["baseline_carbon_t"], 1),
            "carbon_t":             round(res["scenario_carbon_t"], 1),
            "carbon_saving_t":      round(res["carbon_saving_t"], 1),
            "cost_k":               cost_k,
            "payback_years":        f"{payback:.1f}" if payback else "N/A",
            # Visual defaults — elevation replaced by OSM height after matching
            "fill_color":           [0, 194, 168, 210],   # platform teal
            "elevation":            12.0,                  # overridden by OSM
        })

    return rows


# ─────────────────────────────────────────────────────────────────────────────
# DECK BUILDER
# ─────────────────────────────────────────────────────────────────────────────

_TOOLTIP_HTML = """
<div style='background:rgba(5,20,40,0.97);color:#E0EAF0;
            padding:14px 16px;border-radius:10px;
            font-family:Nunito Sans,sans-serif;
            border-left:4px solid #00C2A8;min-width:248px;
            box-shadow:0 6px 24px rgba(0,0,0,0.55);'>
  <!-- ── Header ── -->
  <div style='font-weight:700;color:#00C2A8;font-size:0.92rem;
              letter-spacing:0.02em;margin-bottom:2px;'>{name}</div>
  <div style='font-size:0.73rem;color:#5A9EC8;font-style:italic;
              margin-bottom:8px;'>{building_type} &nbsp;·&nbsp; {scenario}</div>

  <!-- ── Energy ── -->
  <div style='font-size:0.69rem;text-transform:uppercase;letter-spacing:0.06em;
              color:#8FBCCE;margin-bottom:3px;'>⚡ Energy Performance</div>
  <div style='font-size:0.79rem;line-height:1.85;margin-bottom:6px;'>
    Baseline:&nbsp;<strong>{baseline_energy_mwh}</strong> MWh/yr<br/>
    Scenario:&nbsp;<strong>{energy_mwh}</strong> MWh/yr<br/>
    <span style='color:#00C2A8;'>Saving: ↓ <strong>{energy_saving_pct}%</strong></span>
  </div>

  <div style='height:1px;background:rgba(255,255,255,0.08);margin:6px 0;'></div>

  <!-- ── Carbon ── -->
  <div style='font-size:0.69rem;text-transform:uppercase;letter-spacing:0.06em;
              color:#8FBCCE;margin-bottom:3px;'>🌍 Carbon Emissions</div>
  <div style='font-size:0.79rem;line-height:1.85;margin-bottom:6px;'>
    Baseline:&nbsp;<strong>{baseline_carbon_t}</strong> t CO₂e/yr<br/>
    Scenario:&nbsp;<strong>{carbon_t}</strong> t CO₂e/yr<br/>
    <span style='color:#00C2A8;'>Saved: ↓ <strong>{carbon_saving_t}</strong> t</span>
  </div>

  <div style='height:1px;background:rgba(255,255,255,0.08);margin:6px 0;'></div>

  <!-- ── Finance ── -->
  <div style='font-size:0.78rem;line-height:1.7;'>
    💷 Energy cost: <strong>£{cost_k}k/yr</strong>
    &nbsp;·&nbsp; ⏱ Payback: <strong>{payback_years}</strong> yrs
  </div>
  <div style='font-size:0.66rem;color:#3A5A70;margin-top:8px;'>
    Click a building card below for full analysis ↓
  </div>
</div>"""


def _build_deck(
    rows: list[dict],
    center_lat: float = _DEFAULT_LAT,
    center_lon: float = _DEFAULT_LON,
    osm_rows: list[dict] | None = None,
    selected_building: str | None = None,
    tooltip_html: str = _TOOLTIP_HTML,
    map_style: str = _MAP_STYLE_LIGHT,
) -> "pdk.Deck":
    """Assemble a Google Maps-style 3D pydeck Deck.

    Layers (bottom → top)
    ─────────────────────
    1. PolygonLayer — real OSM surrounding buildings (grey, actual heights)
    2. PolygonLayer — campus buildings (teal/gold, actual OSM heights, pickable)
    3. ScatterplotLayer — location pin (blue dot)

    Campus building ``elevation`` is the real physical height from the matched
    OSM polygon (or 12 m default).  Energy/carbon are carried only in the row
    metadata for the hover tooltip — they do NOT drive height or colour.
    """
    import copy

    display_rows = copy.deepcopy(rows)
    for row in display_rows:
        if "polygon" not in row:
            row["polygon"] = _synthetic_polygon(row["lat"], row["lon"])
        # Gold highlight for the selected building; teal for all others
        if selected_building and row["name"] == selected_building:
            row["fill_color"] = [255, 215, 0, 230]
        else:
            row["fill_color"] = row.get("fill_color", [0, 194, 168, 210])

    # OSM surrounding buildings — neutral grey tones on light basemap
    osm_fill = [195, 205, 220, 70]
    osm_line = [148, 158, 175, 160]

    layers: list = []

    # 1 — Real OSM surroundings (actual building heights, not interactive)
    surround_rows: list[dict] = []
    if osm_rows:
        campus_polys = {tuple(map(tuple, r["polygon"])) for r in display_rows}
        for osm in osm_rows:
            if tuple(map(tuple, osm["polygon"])) not in campus_polys:
                surround_rows.append(osm)

    if surround_rows:
        layers.append(pdk.Layer(
            "PolygonLayer",
            data=pd.DataFrame(surround_rows),
            get_polygon="polygon",
            get_elevation="height_m",
            elevation_scale=1,
            extruded=True,
            get_fill_color=osm_fill,
            get_line_color=osm_line,
            line_width_min_pixels=1,
            pickable=False,
            wireframe=False,
        ))

    # 2 — Campus buildings (real footprint, actual height, rich tooltip)
    layers.append(pdk.Layer(
        "PolygonLayer",
        data=pd.DataFrame(display_rows),
        get_polygon="polygon",
        get_elevation="elevation",   # physical height in metres (from OSM)
        elevation_scale=1,
        extruded=True,
        get_fill_color="fill_color",
        get_line_color=[255, 255, 255, 200],
        line_width_min_pixels=2,
        pickable=True,
        auto_highlight=True,
        highlight_color=[255, 215, 0, 80],
        wireframe=False,
    ))

    # 3 — Location pin
    layers.append(pdk.Layer(
        "ScatterplotLayer",
        data=pd.DataFrame([{"lat": center_lat, "lon": center_lon}]),
        get_position="[lon, lat]",
        get_radius=10,
        get_fill_color=[30, 144, 255, 240],
        get_line_color=[255, 255, 255, 255],
        stroked=True,
        line_width_min_pixels=2,
        pickable=False,
    ))

    return pdk.Deck(
        layers=layers,
        initial_view_state=pdk.ViewState(
            latitude=center_lat,
            longitude=center_lon,
            zoom=16,
            pitch=55,
            bearing=-5,
        ),
        tooltip={"html": tooltip_html,
                 "style": {"backgroundColor": "transparent", "border": "none"}},
        map_style=map_style,
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

def _get_polygon_cache_key(center_lat: float, center_lon: float) -> str:
    return f"viz3d_polygons_{center_lat:.4f}_{center_lon:.4f}"


def _render_3d_map(
    scenario_name: str,
    weather: dict,
    center_lat: float,
    center_lon: float,
    osm_rows: list[dict] | None = None,
    selected_building: str | None = None,
) -> None:
    """Render the Google Maps-style 3D digital twin on a light CARTO basemap.

    Campus buildings are shown as real PolygonLayer extrusions at their actual
    physical heights (from OSM).  Sustainability data lives only in the hover
    tooltip — height and colour convey identity, not energy magnitude.

    Polygon assignment (nearest-OSM matching) is cached in session_state per
    location so scenario changes and building selections do not re-hit OSM.
    """
    rows = _compute_all_buildings(scenario_name, weather, center_lat, center_lon)
    if not rows:
        st.info("No building data available for the selected scenario.")
        return

    # Assign / recall OSM polygon footprints (cached per location)
    cache_key = _get_polygon_cache_key(center_lat, center_lon)
    if cache_key not in st.session_state:
        st.session_state[cache_key] = _assign_osm_polygons(rows, osm_rows or [])

    cached   = st.session_state[cache_key]
    poly_map = {r["name"]: (r["polygon"], r.get("height_m", 12.0)) for r in cached}

    for row in rows:
        polygon, height_m = poly_map.get(
            row["name"],
            (_synthetic_polygon(row["lat"], row["lon"]), 12.0),
        )
        row["polygon"]   = polygon
        row["elevation"] = height_m   # real physical height, not energy

    try:
        deck = _build_deck(
            rows, center_lat, center_lon,
            osm_rows=osm_rows,
            selected_building=selected_building,
            map_style=_MAP_STYLE_LIGHT,
        )
        st.pydeck_chart(deck, use_container_width=True)
    except Exception as exc:
        st.warning(f"3D map could not render ({exc}). Showing 2D fallback.")
        _render_2d_fallback(rows)


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC ENTRY POINT — called from app/main.py Dashboard tab
# ─────────────────────────────────────────────────────────────────────────────

def render_campus_3d_map(selected_scenario_names: list[str], weather: dict) -> None:
    """
    Google Maps-style 3D campus digital twin shown on the Dashboard tab.

    Layout
    ──────
    [location search bar]
    [scenario selector]
    [hint text — hover / select prompt]
    [pydeck map — real OSM surroundings (grey) + campus buildings (teal/gold) + pin]
    [legend + attribution]
    [building selector cards — 3 columns]
    [Google Maps-style info panel — shown only when a building is selected]

    Campus buildings are shown as realistic PolygonLayer extrusions at their
    actual physical heights from OSM.  Energy & carbon data appear only in
    the hover tooltip — height and colour express building identity, not data.
    """
    if not _PYDECK_AVAILABLE:
        st.warning(
            "3D visualisation requires **pydeck**. "
            "Run `pip install pydeck>=0.8.0` and restart the app.",
            icon="🗺️",
        )
        return

    # ── Session-state init ────────────────────────────────────────────────────
    if "viz3d_selected_building" not in st.session_state:
        st.session_state.viz3d_selected_building = None

    selected_building: str | None = st.session_state.viz3d_selected_building

    # ── Real selected location ────────────────────────────────────────────────
    center_lat, center_lon, location_label = _get_map_center()

    # ── Section header ────────────────────────────────────────────────────────
    st.markdown(
        f"<div class='sec-hdr'>🗺️ 3D Campus Digital Twin"
        f"<span style='font-size:0.72rem;color:#5A7A90;font-weight:400;"
        f"margin-left:12px;'>📍 {location_label}</span></div>",
        unsafe_allow_html=True,
    )

    # ── Postcode / location search ────────────────────────────────────────────
    src_col, btn_col = st.columns([5, 1])
    with src_col:
        search_query = st.text_input(
            "Search location",
            placeholder="Enter postcode or place name — e.g. SW1A 1AA, Edinburgh, Tokyo…",
            key="viz3d_location_search",
            label_visibility="collapsed",
        )
    with btn_col:
        search_clicked = st.button("🔍 Search", key="viz3d_search_btn",
                                   use_container_width=True)

    if search_clicked and search_query.strip():
        with st.spinner(f"Searching for '{search_query}'…"):
            geo = geocode_location(search_query.strip())
        if geo:
            new_lat, new_lon, display_name = geo
            if (round(new_lat, 4), round(new_lon, 4)) != (round(center_lat, 4),
                                                           round(center_lon, 4)):
                # Drop stale polygon cache for the previous location
                st.session_state.pop(
                    _get_polygon_cache_key(center_lat, center_lon), None
                )
                st.session_state.wx_lat           = new_lat
                st.session_state.wx_lon           = new_lon
                st.session_state.wx_location_name = display_name
                st.session_state.viz3d_selected_building = None
                st.rerun()
        else:
            st.warning(f"Location '{search_query}' not found — try a different postcode or name.")

    # ── Scenario selector ─────────────────────────────────────────────────────
    scenario_for_map = st.selectbox(
        "Scenario for map tooltip",
        selected_scenario_names,
        key="viz3d_scenario",
        label_visibility="collapsed",
    )

    # ── Location-change cache invalidation ────────────────────────────────────
    prev_loc = st.session_state.get("viz3d_last_location")
    cur_loc  = (round(center_lat, 4), round(center_lon, 4))
    if prev_loc != cur_loc:
        st.session_state.pop(_get_polygon_cache_key(*(prev_loc or cur_loc)), None)
        st.session_state["viz3d_last_location"] = cur_loc

    # ── Fetch real surrounding buildings from OSM ─────────────────────────────
    with st.spinner(f"Loading buildings around {location_label}…"):
        osm_rows = fetch_osm_buildings(center_lat, center_lon, radius_m=600)

    # ── Hover/selection hint ──────────────────────────────────────────────────
    if selected_building:
        hint = (f"<b style='color:#FFD700;'>Gold</b> = "
                f"{selected_building.replace('Greenfield ', '')} "
                "&nbsp;·&nbsp; Hover any teal building for energy &amp; carbon data "
                "&nbsp;·&nbsp; Click a card below to switch")
    else:
        hint = ("👇 <b style='color:#00C2A8;'>Select a campus building below</b> "
                "for a full analysis &nbsp;·&nbsp; "
                "Hover the <b style='color:#00C2A8;'>teal buildings</b> for a quick tooltip")

    st.markdown(
        f"<div style='font-size:0.75rem;color:#8FBCCE;margin-bottom:4px;'>"
        f"{hint}</div>",
        unsafe_allow_html=True,
    )

    # ── Render 3D map ─────────────────────────────────────────────────────────
    _render_3d_map(
        scenario_for_map, weather,
        center_lat, center_lon,
        osm_rows=osm_rows,
        selected_building=selected_building,
    )

    # ── Legend + attribution ──────────────────────────────────────────────────
    st.markdown(
        """<div style='display:flex;gap:18px;align-items:center;flex-wrap:wrap;
                       font-size:0.74rem;color:#8FBCCE;margin-top:5px;'>
  <span style='display:flex;align-items:center;gap:5px;'>
    <span style='display:inline-block;width:12px;height:12px;
                 background:#00C2A8;border-radius:2px;'></span>Campus building
  </span>
  <span style='display:flex;align-items:center;gap:5px;'>
    <span style='display:inline-block;width:12px;height:12px;
                 background:#FFD700;border-radius:2px;'></span>Selected building
  </span>
  <span style='display:flex;align-items:center;gap:5px;'>
    <span style='display:inline-block;width:12px;height:12px;
                 background:#C3CDD8;border-radius:2px;'></span>OSM surroundings
  </span>
  <span style='display:flex;align-items:center;gap:5px;'>
    <span style='display:inline-block;width:10px;height:10px;border-radius:50%;
                 background:#1E90FF;'></span>Location pin
  </span>
  <span style='font-size:0.70rem;color:#3A5A70;margin-left:auto;'>
    Heights: real OSM data &nbsp;·&nbsp;
    Tiles: © CARTO Positron &nbsp;·&nbsp;
    Buildings: © OpenStreetMap contributors &nbsp;·&nbsp;
    WebGL · Drag to rotate · Scroll to zoom
  </span>
</div>""",
        unsafe_allow_html=True,
    )

    # ── Building selector cards ───────────────────────────────────────────────
    st.markdown(
        "<div style='margin-top:14px;margin-bottom:6px;font-size:0.82rem;"
        "color:#8FBCCE;font-weight:600;'>🏢 Campus buildings — click to explore:</div>",
        unsafe_allow_html=True,
    )

    building_names = list(_BUILDING_OFFSETS.keys())
    card_cols = st.columns(len(building_names))

    for col, bname in zip(card_cols, building_names):
        icon   = _BUILDING_ICONS.get(bname, "🏢")
        short  = bname.replace("Greenfield ", "")
        is_sel = (selected_building == bname)
        border = "#FFD700" if is_sel else "#1A3A5C"
        bg     = "#0D2640" if is_sel else "#071A2F"
        label  = f"{'✓ ' if is_sel else ''}{short}"

        with col:
            st.markdown(
                f"""<div style='background:{bg};border:2px solid {border};
                               border-radius:8px;padding:10px 12px;
                               text-align:center;margin-bottom:6px;'>
  <div style='font-size:1.4rem;'>{icon}</div>
  <div style='font-size:0.78rem;font-weight:600;color:#E0EAF0;margin:4px 0 2px;'>{short}</div>
  <div style='font-size:0.68rem;color:#5A7A90;'>Greenfield Campus</div>
</div>""",
                unsafe_allow_html=True,
            )
            if st.button(label, key=f"viz3d_card_{bname}",
                         use_container_width=True,
                         type="primary" if is_sel else "secondary"):
                st.session_state.viz3d_selected_building = None if is_sel else bname
                st.rerun()

    # ── Google Maps-style info panel ──────────────────────────────────────────
    if selected_building:
        st.markdown(
            "<hr style='border-color:#1A3A5C;margin:12px 0 0;'/>",
            unsafe_allow_html=True,
        )
        _render_building_info_panel(selected_building, selected_scenario_names, weather)


# ─────────────────────────────────────────────────────────────────────────────
# GOOGLE MAPS-STYLE BUILDING INFO PANEL
# Shown below the map when a building is selected via the card buttons.
# ─────────────────────────────────────────────────────────────────────────────

def _render_building_info_panel(
    building_name: str,
    selected_scenario_names: list[str],
    weather: dict,
) -> None:
    """Render a Google Maps-style info card for the selected campus building.

    Structure
    ─────────
    Header card  — name, address, building type & quick specs
    KPI strip    — 4 metrics: energy, carbon, cost, grid intensity
    Tabs         — 📋 Overview | 📅 Seasonal Energy | ⚡ Scenarios
    """
    from core.physics import BUILDINGS, SCENARIOS, calculate_thermal_load

    bdata  = BUILDINGS.get(building_name)
    if bdata is None:
        return
    _, _, location_label = _get_map_center()

    icon = _BUILDING_ICONS.get(building_name, "🏢")

    # ── Header card ───────────────────────────────────────────────────────────
    st.markdown(
        f"""<div style='background:linear-gradient(135deg,#071A2F 0%,#0D2640 100%);
                        border-left:4px solid #FFD700;border-radius:8px;
                        padding:14px 18px;margin:10px 0 8px;'>
  <div style='font-size:1.05rem;font-weight:700;color:#FFD700;'>
    {icon} {building_name}
  </div>
  <div style='font-size:0.76rem;color:#8FBCCE;margin-top:3px;'>
    📍 Greenfield Campus · {location_label}
  </div>
  <div style='font-size:0.74rem;color:#5A7A90;margin-top:2px;'>
    {bdata.get("building_type","University building")} &nbsp;·&nbsp;
    {bdata.get("floor_area_m2", 0):,} m² floor area &nbsp;·&nbsp;
    Built {bdata.get("built_year","pre-1990")} &nbsp;·&nbsp;
    {bdata.get("occupancy_hours", 0):,} occupied hrs/yr
  </div>
</div>""",
        unsafe_allow_html=True,
    )

    # ── Baseline KPI strip ────────────────────────────────────────────────────
    bl_sc = SCENARIOS.get("Baseline (No Intervention)")
    if bl_sc:
        try:
            bl        = calculate_thermal_load(bdata, bl_sc, weather)
            bl_energy = bl["scenario_energy_mwh"]
            bl_carbon = bl["scenario_carbon_t"]
        except Exception:
            bl_energy = float(bdata.get("baseline_energy_mwh", 0))
            bl_carbon = round(bl_energy * 1000 * _CI / 1000, 1)
    else:
        bl_energy = float(bdata.get("baseline_energy_mwh", 0))
        bl_carbon = round(bl_energy * 1000 * _CI / 1000, 1)

    bl_cost_k = round(bl_energy * 1000 * _ELEC_GBP_PER_KWH / 1000, 1)

    k1, k2, k3, k4 = st.columns(4)
    for col, label, value, unit, colour in [
        (k1, "Annual Energy",    f"{bl_energy:,.0f}",   "MWh/yr",    "#00C2A8"),
        (k2, "Carbon Emissions", f"{bl_carbon:,.1f}",   "t CO₂e/yr", "#FFA500"),
        (k3, "Energy Cost",      f"£{bl_cost_k:,.0f}k", "/yr",       "#5AC8FA"),
        (k4, "Grid Intensity",   f"{_CI*1000:.0f}",     "gCO₂e/kWh", "#8FBCCE"),
    ]:
        with col:
            st.markdown(
                f"""<div style='background:#0D2640;border-radius:6px;
                               padding:10px 12px;border-top:3px solid {colour};
                               text-align:center;margin-bottom:6px;'>
  <div style='font-size:0.68rem;color:#5A7A90;margin-bottom:2px;'>{label}</div>
  <div style='font-size:1.05rem;font-weight:700;color:{colour};'>{value}</div>
  <div style='font-size:0.66rem;color:#5A7A90;'>{unit}</div>
</div>""",
                unsafe_allow_html=True,
            )

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab_ov, tab_seas, tab_sc = st.tabs(
        ["📋  Overview", "📅  Seasonal Energy", "⚡  Scenario Comparison"]
    )
    with tab_ov:
        _info_tab_overview(bdata, selected_scenario_names, weather)
    with tab_seas:
        _info_tab_seasonal(bdata)
    with tab_sc:
        _info_tab_scenarios(bdata, selected_scenario_names, weather)


def _info_tab_overview(bdata: dict, scenario_names: list[str], weather: dict) -> None:
    """Building specs + scenario comparison bar chart."""
    from core.physics import SCENARIOS, calculate_thermal_load
    import plotly.graph_objects as go

    spec_l, spec_r = st.columns(2)
    with spec_l:
        st.markdown(
            f"""<div style='font-size:0.78rem;color:#CBD8E6;line-height:2.0;margin-top:6px;'>
  <b style='color:#00C2A8;'>Wall U-value:</b> {bdata.get("u_value_wall","N/A")} W/m²K<br/>
  <b style='color:#00C2A8;'>Roof U-value:</b> {bdata.get("u_value_roof","N/A")} W/m²K<br/>
  <b style='color:#00C2A8;'>Glazing U-value:</b> {bdata.get("u_value_glazing","N/A")} W/m²K<br/>
  <b style='color:#00C2A8;'>Glazing ratio:</b> {int(bdata.get("glazing_ratio",0)*100)}%
</div>""",
            unsafe_allow_html=True,
        )
    with spec_r:
        temp = weather.get("temperature_2m", "N/A")
        wind = weather.get("wind_speed_10m", "N/A")
        st.markdown(
            f"""<div style='font-size:0.78rem;color:#CBD8E6;line-height:2.0;margin-top:6px;'>
  <b style='color:#00C2A8;'>Floor area:</b> {bdata.get("floor_area_m2",0):,} m²<br/>
  <b style='color:#00C2A8;'>Live weather:</b> {temp}°C · wind {wind} m/s<br/>
  <b style='color:#00C2A8;'>Baseline energy:</b> {bdata.get("baseline_energy_mwh","N/A")} MWh/yr<br/>
  <b style='color:#00C2A8;'>Grid carbon:</b> {_CI*1000:.0f} gCO₂e/kWh (BEIS 2023)
</div>""",
            unsafe_allow_html=True,
        )

    if not scenario_names:
        st.caption("Select scenarios in the sidebar to see a comparison chart.")
        return

    sc_rows: list[dict] = []
    for sn in scenario_names:
        sc = SCENARIOS.get(sn)
        if sc is None:
            continue
        try:
            res = calculate_thermal_load(bdata, sc, weather)
            sc_rows.append({
                "label":  sn.replace(" (No Intervention)", "").replace(" (All Interventions)", ""),
                "energy": res["scenario_energy_mwh"],
                "carbon": res["scenario_carbon_t"],
                "colour": sc.get("colour", "#00C2A8"),
            })
        except Exception:
            pass

    if sc_rows:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name="Energy (MWh/yr)", x=[r["label"] for r in sc_rows],
            y=[r["energy"] for r in sc_rows],
            marker_color=[r["colour"] for r in sc_rows], opacity=0.85,
            text=[f"{r['energy']:.0f}" for r in sc_rows], textposition="outside",
        ))
        fig.add_trace(go.Bar(
            name="Carbon (t CO₂e)", x=[r["label"] for r in sc_rows],
            y=[r["carbon"] for r in sc_rows],
            marker_color=[r["colour"] for r in sc_rows], opacity=0.45,
            text=[f"{r['carbon']:.1f}" for r in sc_rows], textposition="outside",
        ))
        fig.update_layout(
            barmode="group", height=220,
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Nunito Sans", size=10, color="#CBD8E6"),
            margin=dict(t=10, b=5, l=0, r=0),
            yaxis=dict(gridcolor="#1A3A5C"),
            legend=dict(orientation="h", y=-0.28, font=dict(size=9)),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _info_tab_seasonal(bdata: dict) -> None:
    """Monthly energy bar chart + monthly cost grid."""
    import plotly.graph_objects as go

    baseline = float(bdata.get("baseline_energy_mwh", 100.0))
    months   = list(range(1, 13))
    energies = [round(_seasonal_energy_mwh(baseline, _MONTHLY_TEMPS[m]), 1) for m in months]
    carbons  = [round(e * 1000 * _CI / 1000, 1)               for e in energies]
    costs    = [round(e * 1000 * _ELEC_GBP_PER_KWH / 1000, 2) for e in energies]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[_MONTH_NAMES[m - 1][:3] for m in months],
        y=energies, name="Energy (MWh)",
        marker_color="#00C2A8", opacity=0.85,
    ))
    fig.add_trace(go.Scatter(
        x=[_MONTH_NAMES[m - 1][:3] for m in months],
        y=carbons, name="Carbon (t CO₂e)",
        mode="lines+markers",
        line=dict(color="#FFA500", width=2),
        marker=dict(size=5),
        yaxis="y2",
    ))
    fig.update_layout(
        height=230,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Nunito Sans", size=10, color="#CBD8E6"),
        margin=dict(t=5, b=5, l=0, r=0),
        yaxis=dict(title="MWh", gridcolor="#1A3A5C"),
        yaxis2=dict(title="t CO₂e", overlaying="y", side="right",
                    gridcolor="rgba(0,0,0,0)"),
        legend=dict(orientation="h", y=-0.28, font=dict(size=9)),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # Monthly cost grid — two rows of 6
    for row_months in [months[:6], months[6:]]:
        cols = st.columns(6)
        for col, m in zip(cols, row_months):
            with col:
                st.metric(
                    label=_MONTH_NAMES[m - 1][:3],
                    value=f"£{costs[m - 1]:.1f}k",
                    delta=f"{energies[m - 1]:.0f} MWh",
                )
    st.caption("Monthly energy via HDD model · Met Office 1991–2020 normals (Reading)")


def _info_tab_scenarios(
    bdata: dict, scenario_names: list[str], weather: dict
) -> None:
    """Scenario comparison dataframe with energy, carbon, saving, cost, payback."""
    from core.physics import SCENARIOS, calculate_thermal_load

    if not scenario_names:
        st.info("Select one or more scenarios in the sidebar to compare.")
        return

    rows: list[dict] = []
    for sn in scenario_names:
        sc = SCENARIOS.get(sn)
        if sc is None:
            continue
        try:
            res    = calculate_thermal_load(bdata, sc, weather)
            cost_k = round(res["scenario_energy_mwh"] * 1000 * _ELEC_GBP_PER_KWH / 1000, 1)
            payback = res.get("payback_years")
            rows.append({
                "Scenario":           sn.replace(" (No Intervention)", "")
                                        .replace(" (All Interventions)", ""),
                "Energy (MWh/yr)":    f"{res['scenario_energy_mwh']:,.1f}",
                "Carbon (t CO₂e/yr)": f"{res['scenario_carbon_t']:,.1f}",
                "Energy Saving":      f"↓ {res['energy_saving_pct']:.1f}%",
                "Carbon Saved (t)":   f"{res['carbon_saving_t']:,.1f}",
                "Cost (£k/yr)":       f"£{cost_k:,.1f}k",
                "Payback (yrs)":      f"{payback:.1f}" if payback else "N/A",
            })
        except Exception:
            pass

    if rows:
        st.dataframe(
            pd.DataFrame(rows),
            hide_index=True,
            use_container_width=True,
        )
        st.caption(
            "Costs at £0.28/kWh (HESA 2022-23). "
            "Payback = install cost ÷ annual saving. Indicative only."
        )
    else:
        st.info("No scenario data could be computed for this building.")


# ─────────────────────────────────────────────────────────────────────────────
# GEOCODING + OSM BUILDING FOOTPRINTS
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def geocode_location(query: str) -> tuple[float, float, str] | None:
    """Resolve a postcode or place name to ``(lat, lon, display_name)``.

    Uses the OSM Nominatim API — free, no API key required.
    Results are cached for 1 hour to avoid hammering the free service.
    Returns ``None`` on timeout, empty result, or any network error.
    """
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": query, "format": "json", "limit": 1},
            headers={"User-Agent": "CrowAgent-Platform/2.0 (sustainability-ai)"},
            timeout=6,
        )
        resp.raise_for_status()
        data = resp.json()
        if data:
            return (
                float(data[0]["lat"]),
                float(data[0]["lon"]),
                data[0].get("display_name", query),
            )
    except Exception:
        pass
    return None


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_osm_buildings(lat: float, lon: float, radius_m: int = 700) -> List[Dict]:
    """Fetch real OSM building footprints via the Overpass API.

    Returns a list of dicts with keys ``polygon`` ([lon, lat] pairs),
    ``height_m``, and ``name``.  Returns ``[]`` on any network/parse failure.
    """
    d_lat = radius_m / 111_000.0
    d_lon = radius_m / (111_000.0 * math.cos(math.radians(lat)))
    bbox  = (lat - d_lat, lon - d_lon, lat + d_lat, lon + d_lon)
    query = (
        f"way[building]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});"
        "(._;>;); out body;"
    )
    try:
        result = overpy.Overpass().query(query)
        rows: List[Dict] = []
        for way in result.ways:
            coords = [[float(n.lon), float(n.lat)] for n in way.nodes]
            if len(coords) < 3:
                continue
            h = 10.0
            if "height" in way.tags:
                try:
                    h = float(way.tags["height"].rstrip("m "))
                except Exception:
                    pass
            elif "building:levels" in way.tags:
                try:
                    h = float(way.tags["building:levels"]) * 3.5
                except Exception:
                    pass
            rows.append({"polygon": coords, "height_m": h,
                          "name": way.tags.get("name", "")})
        return rows
    except Exception:
        return []


# ─────────────────────────────────────────────────────────────────────────────
# LEGACY PUBLIC API — backwards-compatible with existing tests
# ─────────────────────────────────────────────────────────────────────────────

def render_3d_energy_map(buildings_data: List[Dict]) -> None:
    """Render a pydeck ColumnLayer for an arbitrary list of building dicts.

    Expected keys: ``name``, ``lat``, ``lon``, ``energy_kwh``,
    ``carbon_tonnes``, ``scenario``.
    """
    if not buildings_data:
        st.info("No building data available to render.")
        return

    carbons = [b.get("carbon_tonnes", 0.0) for b in buildings_data]
    min_c   = min(carbons, default=0.0)
    max_c   = max(carbons, default=1.0)

    rows = [
        {
            "name":       b.get("name", ""),
            "lat":        b.get("lat", 0.0),
            "lon":        b.get("lon", 0.0),
            "energy_mwh": b.get("energy_kwh", 0.0) / 1000.0,
            "carbon_t":   b.get("carbon_tonnes", 0.0),
            "carbon_saving_t":   0.0,
            "energy_saving_pct": 0.0,
            "fill_color": _carbon_to_rgba(b.get("carbon_tonnes", 0.0), min_c, max_c),
            "elevation":  max(10.0, b.get("energy_kwh", 0.0) / 10.0),
        }
        for b in buildings_data
    ]

    if not _PYDECK_AVAILABLE:
        _render_2d_fallback(rows)
        return

    # Add synthetic polygon footprints for legacy callers that don't supply them
    for row in rows:
        if "polygon" not in row:
            row["polygon"] = _synthetic_polygon(row["lat"], row["lon"])
        if "scenario" not in row:
            row["scenario"] = ""

    center_lat = sum(r["lat"] for r in rows) / len(rows)
    center_lon = sum(r["lon"] for r in rows) / len(rows)

    try:
        st.pydeck_chart(
            _build_deck(rows, center_lat, center_lon),
            use_container_width=True,
        )
    except Exception as exc:
        st.warning(f"3D map failed: {exc}")
        _render_2d_fallback(rows)


def render_4d_carbon_timeline(
    buildings_data: List[Dict],
    scenarios_over_time: Dict[int, List[Dict]],
) -> None:
    """Render a month-by-month carbon intensity timeline using a pydeck map."""
    if not scenarios_over_time:
        st.info("No timeline data available.")
        return
    month = st.slider("Select Month", 1, 12, 1)
    st.markdown(f"**Carbon Intensity — {_MONTH_NAMES[month - 1]} 2025**")
    render_3d_energy_map(scenarios_over_time.get(month, []))
