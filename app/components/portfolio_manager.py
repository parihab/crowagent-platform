"""
Portfolio Management UI component for the CrowAgent™ Platform.

Exports one public function: render_portfolio_section()
Called from within app/tabs/dashboard.py after the 3D map.
"""

from __future__ import annotations

import uuid
import html as html_mod
import streamlit as st

import services.epc as epc_service

# ── EPC band colour mapping ───────────────────────────────────────────────────
_EPC_COLOURS: dict[str, str] = {
    "A": "#00873D",
    "B": "#2ECC40",
    "C": "#85C226",
    "D": "#F0B429",
    "E": "#F06623",
    "F": "#E84C4C",
    "G": "#C0392B",
}
_EPC_TEXT: dict[str, str] = {
    "A": "#ffffff", "B": "#ffffff", "C": "#ffffff",
    "D": "#ffffff", "E": "#ffffff", "F": "#ffffff", "G": "#ffffff",
}

# ── Segment-appropriate building type options ─────────────────────────────────
_SEGMENT_BUILDING_TYPES: dict[str, list[str]] = {
    "university_he": [
        "Library / Resource Centre", "Lab / Research", "Teaching / Studio",
        "Student Accommodation", "Sports / Leisure", "Administration",
    ],
    "smb_landlord": [
        "Office", "Retail", "Mixed-Use", "Warehouse", "Industrial",
        "Leisure / Hospitality", "Medical / Healthcare",
    ],
    "smb_industrial": [
        "Distribution", "Manufacturing", "Logistics", "Warehouse",
        "Cold Storage", "Data Centre", "Workshop",
    ],
    "individual_selfbuild": [
        "Detached", "Semi-Detached", "Terraced", "Flat / Apartment",
        "Bungalow", "Cottage",
    ],
}


def _epc_badge(rating: str | None) -> str:
    """Return inline HTML for a coloured EPC badge."""
    r = str(rating or "?").upper()
    colour = _EPC_COLOURS.get(r, "#607D8B")
    text_col = _EPC_TEXT.get(r, "#ffffff")
    safe_r = html_mod.escape(r)
    return (
        f'<span style="background:{colour};color:{text_col};'
        f'padding:2px 8px;border-radius:4px;font-weight:700;'
        f'font-size:0.85rem;">{safe_r}</span>'
    )


def _building_type_badge(btype: str | None) -> str:
    """Return inline HTML for a building-type chip."""
    safe = html_mod.escape(str(btype or "Unknown"))
    return (
        f'<span style="background:#1A3A5C;color:#8AACBF;'
        f'padding:2px 8px;border-radius:4px;font-size:0.75rem;">{safe}</span>'
    )


def _render_asset_card(asset: dict, slot_index: int) -> None:
    """Render a single asset card inside a column."""
    name = html_mod.escape(str(asset.get("display_name", "Unknown")))
    btype = asset.get("building_type", "")
    epc = str(asset.get("epc_rating") or "?").upper()
    area = asset.get("floor_area_m2")
    energy = asset.get("baseline_energy_mwh")
    built = asset.get("built_year", "—")
    postcode = html_mod.escape(str(asset.get("postcode") or "—"))

    area_str = f"{area:,.0f} m²" if area else "—"
    energy_str = f"{energy:,.0f} MWh/yr" if energy else "—"
    epc_html = _epc_badge(epc)
    badge_html = _building_type_badge(btype)

    # Active indicator
    active_ids = st.session_state.get("active_analysis_ids", [])
    asset_id = asset.get("id", "")
    is_active = asset_id in active_ids
    status_dot = (
        '<span style="color:#00C2A8;font-size:0.75rem;">● Active</span>'
        if is_active
        else '<span style="color:#5A7A90;font-size:0.75rem;">○ Inactive</span>'
    )

    st.markdown(
        f"""
        <div style="background:#0D2640;border:1px solid #1A3A5C;border-radius:8px;
                    padding:14px;height:100%;min-height:220px;">
          <div style="font-weight:700;font-size:1rem;color:#F0F4F8;
                      margin-bottom:6px;line-height:1.3;">{name}</div>
          <div style="margin-bottom:10px;">{badge_html}</div>
          <table style="width:100%;font-size:0.82rem;color:#CBD8E6;
                        border-collapse:collapse;">
            <tr>
              <td style="padding:2px 0;color:#8AACBF;">EPC</td>
              <td style="padding:2px 0;">{epc_html}</td>
            </tr>
            <tr>
              <td style="padding:2px 0;color:#8AACBF;">Floor Area</td>
              <td style="padding:2px 0;">{html_mod.escape(area_str)}</td>
            </tr>
            <tr>
              <td style="padding:2px 0;color:#8AACBF;">Energy Use</td>
              <td style="padding:2px 0;">{html_mod.escape(energy_str)}</td>
            </tr>
            <tr>
              <td style="padding:2px 0;color:#8AACBF;">Built</td>
              <td style="padding:2px 0;">{html_mod.escape(str(built))}</td>
            </tr>
            <tr>
              <td style="padding:2px 0;color:#8AACBF;">Location</td>
              <td style="padding:2px 0;">📍 {postcode}</td>
            </tr>
          </table>
          <div style="margin-top:10px;">{status_dot}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("🔄 Replace", key=f"btn_replace_{slot_index}", use_container_width=True):
        st.session_state["_pm_replace_slot"] = slot_index
        st.session_state["_pm_search_expanded"] = True
        st.rerun()


def _render_search_panel(segment: str) -> None:
    """Render the Add / Replace asset search panel."""
    expanded = st.session_state.get("_pm_search_expanded", False)

    with st.expander("🔍 Add or Replace an Asset", expanded=expanded):
        st.markdown("**Step 1 — Search by Postcode**")
        postcode_input = st.text_input(
            "UK Postcode",
            value=st.session_state.get("portfolio_search_postcode", ""),
            key="pm_postcode_input",
            placeholder="e.g. RG1 6SP",
        ).upper()

        if st.button("Search Addresses", key="btn_pm_search"):
            pc = postcode_input.strip()
            if len(pc) >= 5:
                with st.spinner("Searching addresses…"):
                    results = epc_service.search_addresses(pc)
                st.session_state["portfolio_search_results"] = results
                st.session_state["portfolio_search_postcode"] = pc
                st.session_state["portfolio_epc_fallback"] = all(
                    r.get("source") in ("manual_entry", "nominatim")
                    for r in results
                )
            else:
                st.warning("Please enter a valid UK postcode.")
                return

        results: list[dict] = st.session_state.get("portfolio_search_results", [])
        if not results:
            return

        st.markdown("---")
        st.markdown("**Step 2 — Select Address**")

        if st.session_state.get("portfolio_epc_fallback"):
            st.info(
                "Live EPC data unavailable — showing address stubs. "
                "Please complete the building details below.",
                icon="ℹ️",
            )

        address_labels = [r["address"] for r in results]
        selected_idx = st.selectbox(
            "Address",
            options=range(len(address_labels)),
            format_func=lambda i: address_labels[i],
            key="pm_address_select",
        )
        selected_result = results[selected_idx]

        # Auto-fill preview from EPC data if available
        has_epc = (
            selected_result.get("epc_rating") is not None
            or selected_result.get("floor_area_m2") is not None
        )

        if has_epc:
            st.markdown("**EPC Data Preview:**")
            c1, c2, c3 = st.columns(3)
            c1.metric("EPC Rating", selected_result.get("epc_rating") or "—")
            c2.metric(
                "Floor Area",
                f"{selected_result['floor_area_m2']:,.0f} m²"
                if selected_result.get("floor_area_m2")
                else "—",
            )
            c3.metric("Year Built", selected_result.get("built_year") or "—")

        # Manual form (always shown; pre-filled from EPC where available)
        st.markdown("**Building Details**")
        building_name = st.text_input(
            "Building Name",
            value=selected_result["address"].split(",")[0].strip(),
            key="pm_building_name",
        )
        floor_area = st.number_input(
            "Floor Area (m²)",
            min_value=1.0,
            max_value=500_000.0,
            value=float(selected_result.get("floor_area_m2") or 200.0),
            step=10.0,
            key="pm_floor_area",
        )
        seg = st.session_state.get("user_segment", "smb_landlord")
        btype_options = _SEGMENT_BUILDING_TYPES.get(seg, ["Office", "Retail", "Residential"])
        # Pre-select from EPC property_type if available
        ptype = str(selected_result.get("property_type") or "").strip()
        default_btype_idx = 0
        if ptype:
            for i, opt in enumerate(btype_options):
                if ptype.lower() in opt.lower() or opt.lower() in ptype.lower():
                    default_btype_idx = i
                    break
        building_type = st.selectbox(
            "Building Type",
            options=btype_options,
            index=default_btype_idx,
            key="pm_building_type",
        )
        built_year = st.number_input(
            "Year Built",
            min_value=1800,
            max_value=2025,
            value=int(selected_result.get("built_year") or 1990),
            step=1,
            key="pm_built_year",
        )

        st.markdown("---")
        st.markdown("**Step 3 — Choose Replacement Slot**")

        portfolio = st.session_state.get("portfolio", [])
        if not portfolio:
            st.warning("No current assets to replace.")
            return

        slot_names = [
            f"Slot {i + 1}: {a.get('display_name', 'Unknown')}"
            for i, a in enumerate(portfolio[:3])
        ]
        # Pre-select slot if triggered via Replace button
        default_slot = st.session_state.get("_pm_replace_slot", 0)
        replace_idx = st.selectbox(
            "Replace which asset?",
            options=range(len(slot_names)),
            format_func=lambda i: slot_names[i],
            index=min(default_slot, len(slot_names) - 1),
            key="pm_replace_slot",
        )

        if st.button("✅ Confirm & Replace Asset", key="btn_pm_confirm", type="primary"):
            _confirm_replace(
                slot_index=replace_idx,
                building_name=building_name,
                floor_area=floor_area,
                building_type=building_type,
                built_year=int(built_year),
                selected_result=selected_result,
                segment=seg,
            )


def _confirm_replace(
    slot_index: int,
    building_name: str,
    floor_area: float,
    building_type: str,
    built_year: int,
    selected_result: dict,
    segment: str,
) -> None:
    """Build asset dict, enforce uniqueness, replace slot, rerun."""
    portfolio: list[dict] = st.session_state.get("portfolio", [])

    # Duplicate detection (case-insensitive)
    new_name_lower = building_name.strip().lower()
    for i, asset in enumerate(portfolio):
        if i == slot_index:
            continue
        if asset.get("display_name", "").strip().lower() == new_name_lower:
            st.warning(
                f"An asset named '{building_name}' already exists in the portfolio. "
                "Please use a different name.",
            )
            return

    # Derive sensible physics defaults from floor area + building type
    epc_rating = str(selected_result.get("epc_rating") or "D").upper()
    if epc_rating not in {"A", "B", "C", "D", "E", "F", "G"}:
        epc_rating = "D"

    # Rough energy estimate: kWh/m²/yr × area → MWh (varies by type/era)
    _EUI_BY_TYPE: dict[str, float] = {
        "Office": 160, "Retail": 220, "Distribution": 100,
        "Warehouse": 90, "Manufacturing": 180, "Logistics": 110,
        "Library / Resource Centre": 200, "Lab / Research": 350,
        "Teaching / Studio": 150, "Detached": 150, "Semi-Detached": 165,
        "Terraced": 145, "Flat / Apartment": 130, "Mixed-Use": 175,
        "Bungalow": 140, "Cottage": 145,
    }
    eui = _EUI_BY_TYPE.get(building_type, 160.0)  # kWh/m²/yr
    age_factor = max(0.6, min(1.6, 1.0 + (1990 - built_year) * 0.008))
    baseline_energy_mwh = round((eui * floor_area * age_factor) / 1000.0, 1)

    # Physics defaults (reasonable mid-range for any building)
    new_asset: dict = {
        "id": str(uuid.uuid4())[:8],
        "segment": segment,
        "name": building_name.strip(),
        "display_name": building_name.strip(),
        "building_type": building_type,
        "floor_area_m2": floor_area,
        "baseline_energy_mwh": baseline_energy_mwh,
        "epc_rating": epc_rating,
        "built_year": built_year,
        "latitude": selected_result.get("latitude") or st.session_state.get("wx_lat", 51.4543),
        "longitude": selected_result.get("longitude") or st.session_state.get("wx_lon", -0.9781),
        "postcode": selected_result.get("postcode", ""),
        "u_value_wall": 0.55,
        "u_value_roof": 0.35,
        "u_value_glazing": 2.4,
        "glazing_ratio": 0.35,
        "occupancy_hours": 2500,
        "height_m": 8.0,
        "is_default": False,
        "source": selected_result.get("source", "manual_entry"),
    }

    # Extend portfolio to 3 slots if needed (should always be 3, but guard)
    while len(portfolio) <= slot_index:
        portfolio.append({})

    portfolio[slot_index] = new_asset
    st.session_state.portfolio = portfolio[:3]

    # Update active analysis IDs
    st.session_state.active_analysis_ids = [
        a["id"] for a in st.session_state.portfolio if a.get("id")
    ]

    # Point 3D viz at the new asset
    st.session_state.viz3d_selected_building = new_asset["name"]

    # Clear search state
    st.session_state.portfolio_search_results = []
    st.session_state.portfolio_search_postcode = ""
    st.session_state["_pm_replace_slot"] = 0
    st.session_state["_pm_search_expanded"] = False

    st.toast(f"Replaced with '{building_name}'", icon="✅")
    st.rerun()


def render_portfolio_section() -> None:
    """
    Renders the full Asset Portfolio Management section.
    Called from within app/tabs/dashboard.py after the 3D map.
    Structure:
      [Section header]
      [3 asset cards side by side]
      [Add / Replace asset search panel — collapsible]
    """
    segment = st.session_state.get("user_segment")
    portfolio: list[dict] = st.session_state.get("portfolio", [])

    st.markdown("### Asset Portfolio")

    if not portfolio:
        st.info("No assets loaded. Select a segment to auto-load defaults.")
        return

    # ── 3 asset cards ─────────────────────────────────────────────────────────
    cols = st.columns(3)
    for i, col in enumerate(cols):
        with col:
            if i < len(portfolio):
                _render_asset_card(portfolio[i], slot_index=i)
            else:
                st.markdown(
                    '<div style="background:#0D2640;border:1px dashed #1A3A5C;'
                    'border-radius:8px;padding:14px;text-align:center;'
                    'color:#5A7A90;min-height:220px;display:flex;'
                    'align-items:center;justify-content:center;">'
                    "Empty slot</div>",
                    unsafe_allow_html=True,
                )

    st.markdown("")

    # ── Search / Replace panel ─────────────────────────────────────────────────
    _render_search_panel(segment or "smb_landlord")
