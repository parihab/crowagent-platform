"""
Compliance Hub Tab Renderer
===========================
Panels rendered dynamically based on handler.compliance_checks:
  Panel A — SECR & TCFD     ('secr')      university_he, smb_industrial
  Panel B — MEES & EPC      ('epc_mees')  commercial_landlord
  Panel C — Part L & FHS    ('part_l','fhs')  commercial_landlord, smb_industrial,
                                               individual_selfbuild

NOTE: Underlying carbon math, scope definitions, and baseline compliance logic
      are untouched — only the presentation layer is restructured.
"""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

import app.branding as branding
import app.compliance as compliance


def render(handler, portfolio: list[dict]) -> None:
    """Render the compliance hub tab for the active segment."""
    buildings = handler.building_registry   # dict[name → building dict]

    if not buildings:
        st.info("No buildings available for compliance checks.")
        return

    branding.render_html(
        f'<h2 style="font-family:Rajdhani,sans-serif;color:#071A2F;margin-bottom:4px;">'
        f"Compliance Hub — {handler.display_label}</h2>"
    )

    checks = handler.compliance_checks

    # Panel A — Carbon & Regulatory Compliance (SECR + TCFD)
    if "secr" in checks:
        _panel_secr_tcfd(buildings)

    # Panel B — MEES & EPC (coming in next update)
    if "epc_mees" in checks:
        _panel_mees_epc(buildings)

    # Panel C — Part L 2021 & FHS (coming in next update)
    if "part_l" in checks or "fhs" in checks:
        _panel_part_l_fhs_stub()


# ─────────────────────────────────────────────────────────────────────────────
# PANEL A — SECR & TCFD
# ─────────────────────────────────────────────────────────────────────────────

def _panel_secr_tcfd(buildings: dict) -> None:
    """Carbon & Regulatory Compliance Overview — SECR reporting + TCFD alignment."""
    branding.render_html(
        '<div class="sec-hdr">Carbon &amp; Regulatory Compliance Overview</div>'
    )

    # Compute portfolio-level carbon baseline
    total_elec_kwh = sum(b["baseline_energy_mwh"] for b in buildings.values()) * 1000
    res = compliance.calculate_carbon_baseline(
        elec_kwh=total_elec_kwh,
        gas_kwh=total_elec_kwh * 0.5,
        fleet_miles=5000,
    )
    threshold = res.get("secr_threshold_check", {})

    # ── Section 1: Compliance Status Banner ──────────────────────────────────
    with st.container(border=True):
        if threshold.get("supply_chain_pressure"):
            branding.render_html(
                '<div style="background:#2A1010;border:1px solid #E84C4C;border-radius:6px;'
                'padding:12px;color:#F0B429;font-weight:600;">'
                "&#9888; Carbon footprint exceeds 50 t — supply chain reporting likely required."
                "</div>"
            )
        else:
            branding.render_html(
                '<div style="background:#071A2F;border:1px solid #00C2A8;border-radius:6px;'
                'padding:12px;color:#00C2A8;font-weight:600;">'
                "&#10004; SECR threshold met — no mandatory disclosure trigger at this time."
                "</div>"
            )

    branding.render_html(
        '<div style="font-size:0.82rem;color:#5A7A90;margin:8px 0 4px;">Emissions Summary</div>'
    )

    # ── Section 2: KPI Columns ───────────────────────────────────────────────
    with st.container(border=True):
        k1, k2, k3 = st.columns(3)
        k1.metric("Scope 1 (Direct)", f"{res['scope1_tco2e']:.1f} t",
                  help="Gas combustion + fleet fuel (proxy estimate)")
        k2.metric("Scope 2 (Grid Elec)", f"{res['scope2_tco2e']:.1f} t",
                  help="Grid electricity — BEIS 2023 carbon intensity factor")
        k3.metric("Total tCO\u2082e", f"{res['total_tco2e']:.1f} t",
                  help="Scope 1 + Scope 2 combined footprint")

    # ── Section 3: Carbon Breakdown Chart ────────────────────────────────────
    branding.render_html(
        '<div style="font-size:0.82rem;color:#5A7A90;margin:8px 0 4px;">Carbon Breakdown</div>'
    )
    with st.container(border=True):
        fig = go.Figure(go.Bar(
            x=["Scope 1 (Direct)", "Scope 2 (Grid Electricity)"],
            y=[res["scope1_tco2e"], res["scope2_tco2e"]],
            marker_color=["#F0B429", "#00C2A8"],
            text=[f"{res['scope1_tco2e']:.1f} t", f"{res['scope2_tco2e']:.1f} t"],
            textposition="auto",
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=10, b=30, l=50, r=20),
            height=280,
            yaxis_title="tCO\u2082e",
            font=dict(family="Nunito Sans"),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # ── Section 4: TCFD Framework Alignment ──────────────────────────────────
    branding.render_html(
        '<div style="font-size:0.82rem;color:#5A7A90;margin:8px 0 4px;">'
        "TCFD Framework Alignment</div>"
    )
    with st.container(border=True):
        st.markdown(
            "**Governance** — Board-level oversight of climate-related risks and "
            "opportunities is recommended. Assign a senior responsible owner for "
            "net-zero delivery and embed climate risk into the annual reporting cycle.\n\n"
            "**Strategy** — Short-term: energy efficiency retrofits aligned to MEES "
            "Band C targets. Medium-term: transition to low-carbon heat (heat pumps, "
            "district heating). Long-term: net-zero by 2050 consistent with a 1.5 °C "
            "pathway under IPCC AR6.\n\n"
            "**Risk Management** — Physical risks (overheating, flood events, extreme "
            "cold) and transition risks (carbon pricing, tightening MEES, stranded "
            "assets) should be integrated into the asset register and scenario "
            "planning framework.\n\n"
            "**Metrics & Targets** — Report Scope 1, 2, and material Scope 3 emissions "
            "annually. Set Science-Based Targets (SBTi) aligned to sector pathways. "
            "Track progress against the Taskforce on Nature-related Financial Disclosures "
            "(TNFD) where biodiversity exposure is material."
        )

    branding.render_html('<div class="main-section-divider"></div>')


# ─────────────────────────────────────────────────────────────────────────────
# PANEL B — MEES & EPC  (redesign scheduled — next commit)
# ─────────────────────────────────────────────────────────────────────────────

def _panel_mees_epc(buildings: dict) -> None:
    """MEES & EPC Compliance Overview — to be redesigned in next commit."""
    branding.render_html(
        '<div class="sec-hdr">MEES &amp; EPC Compliance Overview</div>'
    )
    st.info("Target: EPC Band C by 2028 (Private Rented Sector)")

    for b_name, b_data in buildings.items():
        with st.expander(f"{b_name}", expanded=True):
            res = compliance.estimate_epc_rating(
                floor_area_m2=b_data["floor_area_m2"],
                annual_energy_kwh=b_data["baseline_energy_mwh"] * 1000,
                u_wall=b_data["u_value_wall"],
                u_roof=b_data["u_value_roof"],
                u_glazing=b_data["u_value_glazing"],
                glazing_ratio=b_data["glazing_ratio"],
            )
            c1, c2 = st.columns([1, 3])
            with c1:
                st.metric("Est. Rating", f"{res['sap_score']} ({res['epc_band']})")
                st.caption(f"EUI: {res['eui_kwh_m2']} kWh/m\u00b2")
            with c2:
                if res["mees_2028_compliant"]:
                    st.success(res["recommendation"])
                else:
                    st.warning(res["recommendation"])
                    gap = compliance.mees_gap_analysis(res["sap_score"], "C")
                    if gap["recommended_measures"]:
                        st.markdown("**Recommended Upgrades:**")
                        for m in gap["recommended_measures"]:
                            st.markdown(f"- {m['name']} (Lift: +{m['sap_lift']} pts)")

    branding.render_html('<div class="main-section-divider"></div>')


# ─────────────────────────────────────────────────────────────────────────────
# PANEL C — Part L & FHS  (redesign scheduled — next commit)
# ─────────────────────────────────────────────────────────────────────────────

def _panel_part_l_fhs_stub() -> None:
    """Part L 2021 & FHS Readiness — to be redesigned in next commit."""
    branding.render_html(
        '<div class="sec-hdr">Part L 2021 &amp; FHS Readiness Overview</div>'
    )
    st.info(
        "Full Part L 2021 & FHS compliance panel is being redesigned. "
        "The updated layout will include fabric U-value checks and Future Homes Standard "
        "primary energy metrics.",
        icon="ℹ️",
    )
    branding.render_html('<div class="main-section-divider"></div>')
