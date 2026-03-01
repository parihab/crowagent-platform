"""
📊 Dashboard Tab Renderer
=========================
Renders the main dashboard view for all segments.

Block order (per Prompt B specification):
  1. Page Title (h2 + caption)
  2. Segment Switch Modal (if pending)
  3. KPI Cards (Portfolio Energy, Carbon, Cost, Active Assets)
  4. 3D Map Section
  5. Portfolio Management Section
  6. Asset Performance Summary Table
  7. Thermal Load Analysis Chart
"""
from __future__ import annotations

import html as html_mod

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import app.branding as branding
import core.physics as physics
from config.scenarios import SCENARIOS


def _render_segment_switch_modal() -> None:
    """
    Renders the segment switch confirmation panel.
    Uses st.container(border=True) with .switch-modal CSS class.
    Shows: warning text, segment being switched to,
           PDF download button, Continue button, Cancel button.
    """
    from services.report_generator import generate_portfolio_report
    from app.session import switch_segment_with_defaults
    from app.segments import SEGMENT_LABELS

    pending = st.session_state.get("pending_segment_switch", "")
    new_label = SEGMENT_LABELS.get(pending, pending) if pending else "new segment"

    with st.container(border=True):
        branding.render_html(
            '<div class="switch-modal">'
            f'<h3 style="color:#F0B429;">⚠️ Switch to {html_mod.escape(str(new_label))}?</h3>'
            '<p style="color:#3A576B; font-size:0.9rem;">'
            "Your current portfolio and analysis will be replaced "
            "with the new segment defaults. Would you like to "
            "download your current report first?</p>"
            "</div>"
        )
        col_dl, col_go, col_cancel = st.columns([2, 1.5, 1.5])
        with col_dl:
            try:
                report_bytes = generate_portfolio_report(
                    segment=st.session_state.get("user_segment"),
                    portfolio=st.session_state.get("portfolio", []),
                    scenario_results={},
                    compliance_results={},
                )
                ext = "pdf" if report_bytes[:4] == b"%PDF" else "html"
                st.download_button(
                    label="📄 Download Portfolio Report",
                    data=report_bytes,
                    file_name=f"CrowAgent_Report_{st.session_state.get('user_segment', 'portfolio')}.{ext}",
                    mime=f"application/{ext}",
                    use_container_width=True,
                )
            except Exception:
                st.caption("Report generation unavailable.")
        with col_go:
            if st.button("Continue without downloading", use_container_width=True):
                if pending:
                    switch_segment_with_defaults(pending)
                st.rerun()
        with col_cancel:
            if st.button("Cancel", use_container_width=True, type="secondary"):
                st.session_state.show_segment_switch_modal = False
                st.session_state.pending_segment_switch = None
                st.rerun()


def render(handler, weather: dict, portfolio: list[dict]) -> None:
    """
    Renders the dashboard tab content.

    Args:
        handler: The active SegmentHandler instance.
        weather: Current weather data dictionary.
        portfolio: Full list of portfolio assets (will be filtered by segment).
    """
    # ── BLOCK 1: PAGE TITLE ──────────────────────────────────────────────────
    selected_names = st.session_state.get("selected_scenario_names", [])
    if not selected_names:
        selected_names = handler.default_scenarios

    branding.render_html(
        '<h2 style="font-family:Rajdhani,sans-serif; '
        'color:#071A2F; margin-bottom:4px;">📊 Portfolio Dashboard</h2>'
    )
    st.caption(
        f"Active segment: {handler.display_label} · "
        f"{len(portfolio)} assets · "
        f"Scenario: {selected_names[0] if selected_names else 'None'}"
    )

    # ── BLOCK 2: SEGMENT SWITCH MODAL ────────────────────────────────────────
    if st.session_state.get("show_segment_switch_modal"):
        _render_segment_switch_modal()

    # 1. Filter portfolio for this segment
    segment_portfolio = [p for p in portfolio if p.get("segment") == handler.segment_id]

    if not segment_portfolio:
        st.info("Portfolio is empty. Add a building in the sidebar to begin analysis.")
        return

    # Ensure Baseline is present for comparison
    if "Baseline (No Intervention)" not in selected_names:
        selected_names = ["Baseline (No Intervention)"] + selected_names

    # Calculate results
    tariff = st.session_state.get("energy_tariff_gbp_per_kwh", 0.28)
    scenario_totals = {}

    for s_name in selected_names:
        if s_name not in SCENARIOS:
            continue

        s_data = SCENARIOS[s_name]
        totals = {
            "annual_energy_mwh": 0.0,
            "carbon_saving_tco2": 0.0,
            "cost_saving_gbp": 0.0,
            "install_cost_gbp": 0.0,
            "energy_saving_mwh": 0.0,
        }

        for building in segment_portfolio:
            if "height_m" not in building:
                building["height_m"] = 3.5
            r = physics.calculate_thermal_load(building, s_data, weather, tariff)
            totals["annual_energy_mwh"] += r["scenario_energy_mwh"]
            totals["carbon_saving_tco2"] += r["carbon_saving_t"]
            totals["cost_saving_gbp"] += r["annual_saving_gbp"]
            totals["energy_saving_mwh"] += r["energy_saving_mwh"]
            totals["install_cost_gbp"] += s_data.get("install_cost_gbp", 0.0)

        scenario_totals[s_name] = totals

    # Determine baseline and best scenario for KPIs
    baseline_data = scenario_totals.get("Baseline (No Intervention)", {})
    comparison_scenarios = [s for s in selected_names if s != "Baseline (No Intervention)"]

    # ── BLOCK 3: KPI CARDS ────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        branding.render_card(
            label="PORTFOLIO ENERGY",
            value=f"{baseline_data.get('annual_energy_mwh', 0):,.1f}",
            subtext="MWh / yr",
            accent_class="accent-teal",
        )
    with col2:
        # Carbon: total_energy × BEIS 2023 factor (0.20482 tCO2e/MWh)
        total_carbon = baseline_data.get("annual_energy_mwh", 0) * 0.20482
        branding.render_card(
            label="CARBON FOOTPRINT",
            value=f"{total_carbon:,.1f}",
            subtext="tCO₂e / yr",
            accent_class="accent-green",
        )
    with col3:
        total_cost = baseline_data.get("annual_energy_mwh", 0) * 1000 * tariff
        branding.render_card(
            label="EST. ENERGY COST",
            value=f"£{total_cost:,.0f}",
            subtext="per annum",
            accent_class="accent-gold",
        )
    with col4:
        branding.render_card(
            label="ACTIVE ASSETS",
            value=str(len(segment_portfolio)),
            subtext="Buildings",
            accent_class="accent-navy",
        )

    branding.render_html('<div class="main-section-divider"></div>')

    # ── BLOCK 4: 3D MAP SECTION ───────────────────────────────────────────────
    branding.render_html('<div class="sec-hdr">🌍 Campus / Portfolio Digital Twin</div>')
    from app.visualization_3d import render_3d_building
    render_3d_building(segment_portfolio)

    branding.render_html('<div class="main-section-divider"></div>')

    # ── BLOCK 5: PORTFOLIO MANAGEMENT SECTION ─────────────────────────────────
    from app.components.portfolio_manager import render_portfolio_section

    # Hotfix for KeyError: 'address' in portfolio_manager.py
    # Ensure search results have the 'address' key expected by the renderer
    if "portfolio_search_results" in st.session_state:
        results = st.session_state.portfolio_search_results
        if results and isinstance(results, list) and len(results) > 0:
            first = results[0]
            # Ensure items are dicts and have 'address' key
            if isinstance(first, dict) and "address" not in first:
                # If we have display_name (Nominatim style), map it to address
                if "display_name" in first:
                    for r in results:
                        if isinstance(r, dict):
                            r["address"] = r.get("display_name", "Unknown")
                else:
                    # Unknown format - clear to avoid crash
                    st.session_state.portfolio_search_results = []

    branding.render_html(
        '<div class="portfolio-section-hdr">'
        "📋 Asset Portfolio Management</div>"
    )
    render_portfolio_section()

    branding.render_html('<div class="main-section-divider"></div>')

    # ── BLOCK 6: ASSET PERFORMANCE SUMMARY TABLE ──────────────────────────────
    branding.render_html('<div class="sec-hdr">📊 Asset Performance Summary</div>')
    st.caption(
        "Physics-based simulation of heating demand under "
        "current weather conditions."
    )

    table_rows = []
    for b in segment_portfolio:
        table_rows.append({
            "Building": b.get("display_name", b.get("name", "Unknown")),
            "Type": b.get("building_type", "—"),
            "Area (m²)": b.get("floor_area_m2", 0),
            "Baseline (MWh)": b.get("baseline_energy_mwh", 0),
            "Built": b.get("built_year", "—"),
        })

    st.dataframe(
        pd.DataFrame(table_rows),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Area (m²)": st.column_config.NumberColumn(format="%.0f"),
            "Baseline (MWh)": st.column_config.NumberColumn(format="%.1f"),
        },
    )

    branding.render_html('<div class="main-section-divider"></div>')

    # ── BLOCK 7: THERMAL LOAD CHART ───────────────────────────────────────────
    branding.render_html('<div class="sec-hdr">📈 Thermal Load Analysis</div>')
    st.caption(
        "Physics-based simulation of heating demand under "
        "current weather conditions."
    )

    chart_data = []
    for s_name in selected_names:
        if s_name in scenario_totals:
            chart_data.append({
                "Scenario": s_name,
                "Energy (MWh)": scenario_totals[s_name]["annual_energy_mwh"],
            })

    if chart_data:
        df_chart = pd.DataFrame(chart_data)
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_chart["Scenario"],
            y=df_chart["Energy (MWh)"],
            marker_color="#00C2A8",
            text=df_chart["Energy (MWh)"].apply(lambda x: f"{x:.1f}"),
            textposition="auto",
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=20, b=40, l=40, r=20),
            height=350,
            yaxis_title="Annual Energy (MWh)",
            font=dict(family="Nunito Sans"),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
