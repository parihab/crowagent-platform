"""Portfolio utility helpers shared by portfolio UI components."""

from __future__ import annotations

import uuid
from typing import Any

import streamlit as st


def init_portfolio_entry(epc_data: dict[str, Any] | None, segment: str) -> dict[str, Any]:
    """Create a normalized portfolio asset from EPC lookup output."""
    epc_data = epc_data or {}
    band = str(epc_data.get("epc_band") or epc_data.get("epc_rating") or "D").upper()
    floor_area = float(epc_data.get("floor_area_m2") or 150.0)
    built_year = int(epc_data.get("built_year") or 1995)
    postcode = str(epc_data.get("postcode") or st.session_state.get("modal_pc", "")).strip().upper()

    return {
        "id": f"asset_{uuid.uuid4().hex[:8]}",
        "segment": segment,
        "name": epc_data.get("name") or epc_data.get("display_name") or f"Asset {postcode or 'Unknown'}",
        "display_name": epc_data.get("display_name") or epc_data.get("name") or f"Asset {postcode or 'Unknown'}",
        "building_type": epc_data.get("property_type") or "Office",
        "floor_area_m2": floor_area,
        "baseline_energy_mwh": float(epc_data.get("baseline_energy_mwh") or max(25.0, floor_area * 0.12)),
        "epc_rating": band,
        "built_year": built_year,
        "latitude": float(epc_data.get("latitude") or st.session_state.get("wx_lat", 51.45)),
        "longitude": float(epc_data.get("longitude") or st.session_state.get("wx_lon", -0.97)),
        "postcode": postcode,
        "u_value_wall": float(epc_data.get("u_value_wall") or 0.55),
        "u_value_roof": float(epc_data.get("u_value_roof") or 0.35),
        "u_value_glazing": float(epc_data.get("u_value_glazing") or 2.4),
        "glazing_ratio": float(epc_data.get("glazing_ratio") or 0.35),
        "occupancy_hours": int(epc_data.get("occupancy_hours") or 2600),
        "height_m": float(epc_data.get("height_m") or 10.0),
        "is_default": False,
        "source": epc_data.get("source") or "epc",
    }
