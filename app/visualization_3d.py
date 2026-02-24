"""Zero‑cost 3D/4D spatial visualisation helpers for CrowAgent Platform.

External services used and cost/license information:

* **OpenFreeMap tiles**  — free, open‑source map style hosted by OpenStreetMap
  community; licence: CC‑BY‑SA (same as OSM data). No API key required.
* **OSM Nominatim geocoding** — free public API (Usage Policy: https://operations.osmfoundation.org/policies/nominatim/). Licence: ODbL.
* **OSM Overpass API** — free public query service; licence: ODbL.
* **Streamlit** — open-source (Apache 2.0).
* **pydeck (deck.gl bindings)** — open-source (BSD).
* **requests** — open-source (Apache 2.0).

All services invoked by this module are free to use for non‑commercial
purposes and do not require API tokens or paid subscriptions.  Map tiles,
geocoding, and OSM queries incur zero cost.
"""

from __future__ import annotations

import math
from typing import Dict, List

import pandas as pd
import pydeck as pdk
import requests
import streamlit as st

import overpy

# constants
_FREE_MAP_STYLE = "https://tiles.openfreemap.org/styles/liberty"
_MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _colour_from_carbon(carbon: float, min_c: float, max_c: float) -> List[int]:
    """Return RGB colour on a green<->red gradient based on carbon fraction."""
    frac = max(min((carbon - min_c) / (max_c - min_c) if max_c > min_c else 0.0, 1.0), 0.0)
    start = pd.np.array([0, 194, 168])
    end = pd.np.array([220, 50, 50])
    rgb = (start * (1 - frac) + end * frac).astype(int)
    return rgb.tolist()


# ---------------------------------------------------------------------------
# 3D / 4D rendering
# ---------------------------------------------------------------------------

def render_3d_energy_map(buildings_data: List[Dict]) -> None:
    """Render a pydeck ColumnLayer showing energy/carbon for each building.

    The provided list must include dictionaries with keys
    ``name``, ``lat``, ``lon``, ``energy_kwh``, ``carbon_tonnes`` and
    ``scenario``.  Height extrusion is proportional to ``energy_kwh``; colour
    gradient is based on ``carbon_tonnes``.
    """

    if not buildings_data:
        st.info("No building data available to render.")
        return

    carbons = [b.get("carbon_tonnes", 0.0) for b in buildings_data]
    min_c, max_c = min(carbons, default=0.0), max(carbons, default=1.0)

    for b in buildings_data:
        b["colour"] = _colour_from_carbon(b.get("carbon_tonnes", 0.0), min_c, max_c)
        b["height"] = float(b.get("energy_kwh", 0.0)) / 10.0

    df = pd.DataFrame(buildings_data)

    try:
        layer = pdk.Layer(
            "ColumnLayer",
            data=df,
            get_position="[lon, lat]",
            get_elevation="height",
            elevation_scale=1,
            extruded=True,
            get_fill_color="colour",
            pickable=True,
            auto_highlight=True,
        )
        view = pdk.ViewState(
            latitude=float(df["lat"].mean()),
            longitude=float(df["lon"].mean()),
            zoom=14,
            pitch=45,
        )
        st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view, map_style=_FREE_MAP_STYLE))

        st.markdown(
            """
            <div style='position:relative; padding:8px; background:#071A2F; color:#CBD8E6;'
                 >
              <strong>Carbon colour scale</strong><br/>
              <span style='background:rgb(0,194,168);padding:2px 8px;border-radius:3px;'>Low</span>
              &nbsp;→&nbsp;
              <span style='background:rgb(220,50,50);padding:2px 8px;border-radius:3px;'>High</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    except Exception as exc:  # pragma: no cover
        st.warning(f"3D map failed: {exc}")
        if buildings_data:
            df2 = pd.DataFrame(buildings_data)
            st.bar_chart(df2.set_index("name")["energy_kwh"])


def render_4d_carbon_timeline(buildings_data: List[Dict], scenarios_over_time: Dict[int, List[Dict]]) -> None:
    """Render carbon intensity month-by-month using a pydeck map."""

    if not scenarios_over_time:
        st.info("No timeline data available.")
        return

    month = st.slider("Select Month", 1, 12, 1)
    st.header(f"Carbon Intensity — Month: {_MONTH_NAMES[month-1]} 2025")

    data_for_month = scenarios_over_time.get(month, [])
    render_3d_energy_map(data_for_month)


@st.cache_data(ttl=3600)
def fetch_osm_buildings(lat: float, lon: float, radius_m: int = 500) -> List[Dict]:
    """Query Overpass API for building footprints around a point."""

    delta_lat = radius_m / 111000.0
    delta_lon = radius_m / (111000.0 * math.cos(math.radians(lat)))
    bbox = (lat - delta_lat, lon - delta_lon, lat + delta_lat, lon + delta_lon)
    query = (
        f"way[\"building\"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});"
        "(._;>;); out body;"
    )
    try:
        api = overpy.Overpass()
        result = api.query(query)
        buildings: List[Dict] = []
        for way in result.ways:
            if not way.nodes:
                continue
            n = way.nodes[0]
            h = None
            if "height" in way.tags:
                try:
                    h = float(way.tags["height"].rstrip("m"))
                except Exception:
                    h = None
            if h is None and "building:levels" in way.tags:
                try:
                    h = float(way.tags["building:levels"]) * 3.5
                except Exception:
                    h = None
            if h is None:
                h = 10.0
            buildings.append({
                "lat": float(n.lat),
                "lon": float(n.lon),
                "height_m": h,
                "osm_id": way.id,
            })
        return buildings
    except Exception:
        return []


def render_visualization_tab() -> None:
    """Top‑level Streamlit tab for 3D/4D visualisations."""

    st.markdown(
        "<div style='background:#071A2F; color:#CBD8E6; padding:10px;'>"
        "This tab uses WebGL; if your browser does not support it, please use "
        "Chrome or Firefox.</div>",
        unsafe_allow_html=True,
    )

    choice = st.selectbox(
        "Visualization",
        ["3D Energy Map", "4D Carbon Timeline", "OSM Real Buildings"],
        index=0,
        label_visibility="collapsed",
    )

    demo_buildings = [
        {"name": "Greenfield Library", "lat": 52.4862, "lon": -1.8904,
         "energy_kwh": 100000, "carbon_tonnes": 80, "scenario": "Baseline"},
        {"name": "Arts Building", "lat": 52.4870, "lon": -1.8890,
         "energy_kwh": 75000, "carbon_tonnes": 55, "scenario": "Baseline"},
        {"name": "Science Block", "lat": 52.4855, "lon": -1.8920,
         "energy_kwh": 125000, "carbon_tonnes": 90, "scenario": "Baseline"},
    ]

    if choice == "3D Energy Map":
        render_3d_energy_map(demo_buildings)

    elif choice == "4D Carbon Timeline":
        timeline: Dict[int, List[Dict]] = {}
        for m in range(1, 13):
            factor = 1.0 - 0.6 * ((m - 1) / 11)
            timeline[m] = [
                {**b, "carbon_tonnes": b["carbon_tonnes"] * factor}
                for b in demo_buildings
            ]
        render_4d_carbon_timeline(demo_buildings, timeline)

    else:  # OSM Real Buildings
        query = st.text_input("Enter UK postcode or place name")
        if query:
            try:
                resp = requests.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={"q": query, "format": "json"},
                    timeout=10,
                )
                resp.raise_for_status()
                data = resp.json()
                if data:
                    lat = float(data[0]["lat"])
                    lon = float(data[0]["lon"])
                    st.write(f"Location: {lat:.6f}, {lon:.6f}")
                    buildings = fetch_osm_buildings(lat, lon)
                    if buildings:
                        df = pd.DataFrame(buildings)
                        layer = pdk.Layer(
                            "ScatterplotLayer",
                            data=df,
                            get_position="[lon, lat]",
                            get_radius=2,
                            get_fill_color=[0, 194, 168],
                            pickable=True,
                        )
                        view = pdk.ViewState(latitude=lat, longitude=lon, zoom=16, pitch=45)
                        try:
                            st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view, map_style=_FREE_MAP_STYLE))
                        except Exception as exc:  # pragma: no cover
                            st.warning(f"Pydeck failed: {exc}")
                    else:
                        st.info("No OSM buildings found in the area.")
                else:
                    st.error("Geocoding returned no results.")
            except Exception as exc:
                st.error(f"Geocoding/OSM lookup failed: {exc}")


# Example integration into main.py:
# from app.visualization_3d import render_visualization_tab
# render_visualization_tab()
