import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from core.physics import calculate_thermal_load
from config.scenarios import SCENARIOS
from config.constants import ELEC_COST_PER_KWH


def _irr(cash_flows: list) -> float | None:
    """
    Newton-Raphson IRR solver using the same cash flows as NPV.
    Returns IRR as a decimal (e.g. 0.18 = 18%), or None if no valid solution.
    No external dependencies — uses only built-in Python arithmetic.
    """
    rate = 0.1  # initial guess: 10%
    for _ in range(1000):
        npv = sum(cf / (1.0 + rate) ** t for t, cf in enumerate(cash_flows))
        d_npv = sum(-t * cf / (1.0 + rate) ** (t + 1) for t, cf in enumerate(cash_flows))
        if d_npv == 0:
            break
        new_rate = rate - npv / d_npv
        if abs(new_rate - rate) < 1e-8:
            # Guard: reject economically unreasonable values
            return new_rate if -1.0 < new_rate < 100.0 else None
        rate = new_rate
    return None


def render(handler, portfolio: list[dict]) -> None:
    """Render the Financial Analysis tab."""
    if not portfolio:
        st.info("Portfolio is empty. Add a building in the sidebar to begin.")
        return

    # ── Header ────────────────────────────────────────────────────────────
    st.header("Capital Investment Performance Analysis")

    # ── Session state ──────────────────────────────────────────────────────
    for key, default in [("fin_rate_pct", 5.0), ("fin_term_yrs", 10)]:
        if key not in st.session_state:
            st.session_state[key] = default

    # ── Section 1: Assumptions Card ───────────────────────────────────────
    with st.container(border=True):
        c1, c2 = st.columns([3, 2])

        with c1:
            st.markdown("**Discount Rate**")
            ra, rb = st.columns([3, 1])
            with ra:
                st.slider(
                    "Discount Rate Slider", 1.0, 15.0, step=0.5,
                    key="fin_rate_pct", label_visibility="collapsed",
                )
            with rb:
                manual_rate = st.number_input(
                    "%", 1.0, 15.0,
                    value=float(st.session_state.fin_rate_pct),
                    step=0.5, format="%.1f",
                    label_visibility="collapsed",
                )
            if manual_rate != float(st.session_state.fin_rate_pct):
                st.session_state.fin_rate_pct = manual_rate
                st.rerun()

        with c2:
            st.markdown("**Analysis Period**")
            st.slider(
                "Analysis Period Slider", 5, 25, step=1,
                key="fin_term_yrs", label_visibility="collapsed",
            )
            st.caption(f"{st.session_state.fin_term_yrs} years selected")

    discount_rate = float(st.session_state.fin_rate_pct) / 100.0
    term_years = int(st.session_state.fin_term_yrs)

    # ── Data preparation ───────────────────────────────────────────────────
    buildings = handler.building_registry
    scenarios = [s for s in handler.scenario_whitelist if s != "Baseline (No Intervention)"]

    if not buildings or not scenarios:
        st.info("Insufficient data for financial analysis.")
        return

    avg_weather = {"temperature_c": 10.5}
    roi_data = []

    for b_name, b_data in buildings.items():
        for s_name in scenarios:
            sc = SCENARIOS[s_name]
            res = calculate_thermal_load(b_data, sc, avg_weather)

            saving_gbp = res["annual_saving_gbp"]
            capex = res["install_cost_gbp"]
            payback = res["payback_years"] or 999

            cash_flows = [-capex] + [saving_gbp] * term_years
            npv = sum(cf / ((1.0 + discount_rate) ** t) for t, cf in enumerate(cash_flows))
            irr_val = _irr(cash_flows)

            roi_data.append({
                "Asset": b_name,
                "Scenario": s_name,
                "CAPEX (£)": capex,
                "OPEX Savings (£)": saving_gbp,
                "Payback (Yrs)": payback,
                "NPV (£)": npv,
                "IRR (%)": irr_val * 100.0 if irr_val is not None else None,
            })

    df = pd.DataFrame(roi_data)

    # ── Section 2: Executive Financial Summary ─────────────────────────────
    st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("**Executive Financial Summary**")
        sel_scenario = st.selectbox("Scenario", scenarios, label_visibility="collapsed")
        sel = df[df["Scenario"] == sel_scenario]

        if not sel.empty:
            avg_payback = sel["Payback (Yrs)"].replace(999, float("nan")).mean()
            avg_npv = sel["NPV (£)"].mean()
            avg_irr = sel["IRR (%)"].mean()

            m1, m2, m3 = st.columns(3)
            m1.metric("Payback Period", f"{avg_payback:.1f} Years" if pd.notna(avg_payback) else "N/A")
            m2.metric(f"NPV ({term_years}-Year)", f"£{avg_npv:,.0f}")
            m3.metric("IRR", f"{avg_irr:.1f}%" if pd.notna(avg_irr) else "N/A")

    # ── Section 3: Payback Period Comparison (full width) ──────────────────
    st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("**Payback Period Comparison**")
        fig = go.Figure()
        for s_name in scenarios:
            subset = df[df["Scenario"] == s_name]
            fig.add_trace(go.Bar(
                x=subset["Asset"],
                y=subset["Payback (Yrs)"].replace(999, None),
                name=s_name,
            ))
        fig.update_layout(
            barmode="group",
            height=400,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#CBD8E6"),
            xaxis=dict(title="Asset", tickangle=0, showgrid=False),
            yaxis=dict(
                title="Payback Period (Years)",
                gridcolor="rgba(203,216,230,0.15)",
            ),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(t=20, b=40),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Section 4: Detailed Financial Metrics Table ────────────────────────
    st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("**Detailed Financial Metrics**")
        display_df = df[["Asset", "Scenario", "CAPEX (£)", "OPEX Savings (£)", "NPV (£)", "IRR (%)"]].copy()
        st.dataframe(
            display_df.style.format(
                {
                    "CAPEX (£)": "£{:,.0f}",
                    "OPEX Savings (£)": "£{:,.0f}",
                    "NPV (£)": "£{:,.0f}",
                    "IRR (%)": "{:.1f}%",
                },
                na_rep="N/A",
            ),
            use_container_width=True,
            hide_index=True,
        )
