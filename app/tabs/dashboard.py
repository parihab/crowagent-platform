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
from config.scenarios import SCENARIOS, SEGMENT_SCENARIOS


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

    # Guard: ensure physics calculations have a valid weather dict
    weather_for_calc = weather if weather.get("temperature_c") is not None else {"temperature_c": 10.0}

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
            r = physics.calculate_thermal_load(building, s_data, weather_for_calc, tariff)
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

    # ── CONTROLS PANEL ────────────────────────────────────────────────────────
    branding.render_html('<div class="sec-hdr">⚙️ Analysis Controls</div>')
    with st.container(border=True):
        ctrl1, ctrl2, ctrl3 = st.columns([3, 2, 2])

        with ctrl1:
            st.markdown("**📐 Scenarios**")
            _available_sc = SEGMENT_SCENARIOS.get(handler.segment_id, list(SCENARIOS.keys()))
            _new_selected = st.multiselect(
                "Select scenarios",
                options=_available_sc,
                default=[s for s in selected_names if s in _available_sc],
                key="dash_scenario_multiselect",
                label_visibility="collapsed",
            )
            st.session_state.selected_scenario_names = _new_selected

        with ctrl2:
            st.markdown("**🏢 Asset Portfolio**")
            _n = len(segment_portfolio)
            st.caption(f"{_n} {'properties' if _n != 1 else 'property'} active")
            for _asset in segment_portfolio:
                _aname = html_mod.escape(_asset.get("display_name", "Unknown"))
                _aepc = html_mod.escape(str(_asset.get("epc_rating", "?")))
                st.markdown(f"· {_aname} *(EPC {_aepc})*")

        with ctrl3:
            st.markdown("**🌦️ Weather API**")
            _prov_opts = ["open_meteo", "met_office", "manual"]
            _prov_labels = {
                "open_meteo": "Open-Meteo (free)",
                "met_office": "Met Office",
                "manual": "Manual override",
            }
            _cur_prov = st.session_state.get("weather_provider", "open_meteo")
            _prov_idx = _prov_opts.index(_cur_prov) if _cur_prov in _prov_opts else 0
            _new_prov = st.selectbox(
                "Provider",
                options=_prov_opts,
                format_func=lambda p: _prov_labels.get(p, p),
                index=_prov_idx,
                key="dash_wx_prov",
                label_visibility="collapsed",
            )
            st.session_state.weather_provider = _new_prov

    branding.render_html('<div class="main-section-divider"></div>')

    # ── BLOCK 4: 3D MAP + WEATHER PANEL ───────────────────────────────────────
    map_col, wx_col = st.columns([3, 1])

    with wx_col:
        # ── Weather card ──────────────────────────────────────────────────────
        _w_temp = html_mod.escape(f"{weather.get('temperature_c', 10.0):.1f}")
        _w_loc  = html_mod.escape(str(weather.get("location_name", "—")))
        _w_desc = html_mod.escape(
            str(weather.get("condition") or weather.get("description", "—"))
        )
        _w_wind = html_mod.escape(str(weather.get("wind_speed_mph", "—")))
        _w_hum  = html_mod.escape(str(weather.get("humidity_pct", "—")))
        branding.render_html(f"""
<div role="status" aria-label="Weather: {_w_temp}°C, {_w_desc}"
     style="background:#0D2640;border:1px solid #1A3A5C;border-radius:6px;
            padding:12px;margin-bottom:10px;">
  <div style="font-size:0.72rem;color:#8AACBF;margin-bottom:5px;">🌡️ Live Weather</div>
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
    <div style="font-size:1.9rem;font-weight:700;color:#F0F4F8;">{_w_temp}°C</div>
    <div style="font-size:0.76rem;color:#CBD8E6;text-align:right;">{_w_desc}</div>
  </div>
  <div style="font-size:0.69rem;color:#5A7A90;margin-bottom:6px;">📍 {_w_loc}</div>
  <div style="font-size:0.7rem;color:#5A7A90;display:flex;gap:10px;">
    <span>💨 {_w_wind} mph</span><span>💧 {_w_hum}%</span>
  </div>
</div>
""")
        # ── Location selector ─────────────────────────────────────────────────
        from services.location import city_options, city_meta, nearest_city
        _city_list = city_options()
        _cur_lat = float(st.session_state.get("wx_lat", 51.4543))
        _cur_lon = float(st.session_state.get("wx_lon", -0.9781))
        _cur_city = nearest_city(_cur_lat, _cur_lon)
        _city_idx = _city_list.index(_cur_city) if _cur_city in _city_list else 0
        _sel_city = st.selectbox(
            "📍 Location",
            _city_list,
            index=_city_idx,
            key="dash_city_sel",
        )
        if _sel_city:
            _ci = city_meta(_sel_city)
            if abs(_ci["lat"] - _cur_lat) > 0.01 or abs(_ci["lon"] - _cur_lon) > 0.01:
                st.session_state.wx_lat = _ci["lat"]
                st.session_state.wx_lon = _ci["lon"]
                st.session_state.wx_location_name = _sel_city
                st.rerun()

    with map_col:
        from app.visualization_3d import render_campus_3d_map
        render_campus_3d_map(selected_names, weather)

    branding.render_html('<div class="main-section-divider"></div>')

    # ── BLOCK 5: PORTFOLIO MANAGEMENT SECTION ─────────────────────────────────
    from app.components.portfolio_manager import render_portfolio_section

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
