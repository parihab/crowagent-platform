"""
CrowAgent™ Portfolio Report Generator.

Generates a structured PDF report of the current portfolio analysis.
Uses fpdf2 (pip install fpdf2) — lightweight, no external font deps.
Falls back to a UTF-8 HTML bytes string if fpdf2 is not installed,
so st.download_button() always has a valid payload.

Public API
----------
generate_portfolio_report(
    segment: str,
    portfolio: list[dict],
    scenario_results: dict,
    compliance_results: dict,
) -> bytes
"""

from __future__ import annotations

import html as html_mod
from datetime import date
from typing import Any

try:
    from fpdf import FPDF
except ImportError:
    FPDF = None  # type: ignore[assignment,misc]

# ── Brand colours (hex without #) ────────────────────────────────────────────
_DARK_BG = (7, 26, 47)        # #071A2F
_ACCENT  = (0, 194, 168)      # #00C2A8
_WHITE   = (240, 244, 248)    # #F0F4F8
_MUTED   = (90, 122, 144)     # #5A7A90
_MID     = (26, 58, 92)       # #1A3A5C

_DISCLAIMER = (
    "This report has been generated automatically by CrowAgent™ for "
    "informational purposes only. Energy and carbon figures are modelled "
    "estimates based on physics-engine calculations and EPC/registry data. "
    "They do not constitute professional engineering advice. Always commission "
    "an accredited energy assessor before making investment decisions. "
    "CrowAgent™ and Crow Digital Ltd accept no liability for decisions taken "
    "on the basis of this report."
)

_DATA_SOURCES = (
    "Physics model: CrowAgent™ thermal engine v2 (CIBSE TM54 methodology). "
    "Carbon intensities: BEIS 2023 grid emission factors. "
    "EPC data: UK EPC Open Data (api.opendatasoft.com / epc.opendatacommunities.org). "
    "Weather data: Open-Meteo API / UK Met Office. "
    "Compliance thresholds: Part L 2021, MEES 2018 (amended 2023), SECR 2019."
)

_SEGMENT_LABELS: dict[str, str] = {
    "university_he":        "University / Higher Education",
    "smb_landlord":         "Commercial Landlord",
    "smb_industrial":       "SMB Industrial",
    "individual_selfbuild": "Individual Self-Build",
}

_EPC_COLOURS_HEX: dict[str, str] = {
    "A": "#00873D", "B": "#2ECC40", "C": "#85C226",
    "D": "#F0B429", "E": "#F06623", "F": "#E84C4C", "G": "#C0392B",
}


# ─────────────────────────────────────────────────────────────────────────────
# PDF generation (fpdf2 path)
# ─────────────────────────────────────────────────────────────────────────────

class _CrowPDF(FPDF if FPDF is not None else object):  # type: ignore[misc]
    """Custom FPDF subclass with CrowAgent branding."""

    def __init__(self, segment: str, *args: Any, **kwargs: Any) -> None:
        if FPDF is None:
            raise RuntimeError("fpdf2 not installed")
        super().__init__(*args, **kwargs)
        self._segment = segment

    def header(self) -> None:
        self.set_fill_color(*_DARK_BG)
        self.rect(0, 0, 210, 14, "F")
        self.set_text_color(*_ACCENT)
        self.set_font("Helvetica", "B", 10)
        self.set_xy(8, 3)
        self.cell(0, 8, "CrowAgent™  |  Portfolio Analysis Report", ln=False)
        self.set_text_color(*_MUTED)
        self.set_font("Helvetica", "", 7)
        self.set_xy(0, 5)
        self.cell(200, 5, f"{_SEGMENT_LABELS.get(self._segment, self._segment)}", align="R", ln=True)
        self.ln(4)

    def footer(self) -> None:
        self.set_y(-12)
        self.set_fill_color(*_MID)
        self.rect(0, self.get_y(), 210, 12, "F")
        self.set_text_color(*_MUTED)
        self.set_font("Helvetica", "", 7)
        self.set_xy(8, self.get_y() + 3)
        self.cell(0, 5, f"Page {self.page_no()} — © CrowAgent™ {date.today().year} — Confidential", ln=False)

    def section_header(self, title: str) -> None:
        self.set_fill_color(*_MID)
        self.set_text_color(*_ACCENT)
        self.set_font("Helvetica", "B", 11)
        self.cell(0, 9, f"  {title}", ln=True, fill=True)
        self.ln(3)

    def body_text(self, text: str, size: int = 9) -> None:
        self.set_text_color(*_WHITE)
        self.set_font("Helvetica", "", size)
        self.multi_cell(0, 5, text)
        self.ln(1)

    def kv_row(self, key: str, value: str) -> None:
        self.set_text_color(*_MUTED)
        self.set_font("Helvetica", "", 8)
        self.cell(55, 6, key, ln=False)
        self.set_text_color(*_WHITE)
        self.set_font("Helvetica", "", 8)
        self.cell(0, 6, value, ln=True)

    def bar(self, label: str, value: float, max_val: float, colour: tuple[int, int, int]) -> None:
        """Render a simple text-based horizontal bar."""
        max_width = 100.0
        bar_w = (value / max_val * max_width) if max_val > 0 else 0.0
        self.set_text_color(*_MUTED)
        self.set_font("Helvetica", "", 7)
        self.cell(55, 5, label[:30], ln=False)
        self.set_fill_color(*colour)
        self.cell(max(1.0, bar_w), 4, "", fill=True, ln=False)
        self.set_text_color(*_WHITE)
        self.set_font("Helvetica", "", 7)
        self.cell(0, 5, f"  {value:,.0f} MWh", ln=True)


def _build_pdf(
    segment: str,
    portfolio: list[dict],
    scenario_results: dict,
    compliance_results: dict,
) -> bytes:
    """Build and return PDF bytes using fpdf2."""
    pdf = _CrowPDF(segment=segment, orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.set_fill_color(*_DARK_BG)

    today = date.today().strftime("%d %B %Y")
    seg_label = _SEGMENT_LABELS.get(segment, segment)

    # ── Page 1: Cover ─────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.set_fill_color(*_DARK_BG)
    pdf.rect(0, 0, 210, 297, "F")

    pdf.set_y(40)
    pdf.set_text_color(*_ACCENT)
    pdf.set_font("Helvetica", "B", 28)
    pdf.cell(0, 12, "CrowAgent", ln=True, align="C")
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(*_MUTED)
    pdf.cell(0, 8, "Portfolio Analysis Report", ln=True, align="C")

    pdf.ln(10)
    pdf.set_text_color(*_WHITE)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, seg_label, ln=True, align="C")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*_MUTED)
    pdf.cell(0, 6, today, ln=True, align="C")

    pdf.ln(12)
    pdf.set_fill_color(*_MID)
    pdf.rect(15, pdf.get_y(), 180, 0.5, "F")
    pdf.ln(6)

    # Portfolio summary table
    pdf.set_text_color(*_ACCENT)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 7, "Portfolio Summary", ln=True)
    pdf.ln(2)

    for i, asset in enumerate(portfolio[:3]):
        pdf.set_fill_color(*_MID)
        pdf.set_text_color(*_WHITE)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 7, f"  Asset {i + 1}: {asset.get('display_name', 'Unknown')}", fill=True, ln=True)
        pdf.set_fill_color(*_DARK_BG)
        pdf.kv_row("Building Type:", str(asset.get("building_type", "—")))
        pdf.kv_row("Floor Area:", f"{asset.get('floor_area_m2', 0):,.0f} m²")
        pdf.kv_row("EPC Rating:", str(asset.get("epc_rating", "—")))
        pdf.kv_row("Year Built:", str(asset.get("built_year", "—")))
        pdf.kv_row("Postcode:", str(asset.get("postcode", "—")))
        pdf.ln(3)

    pdf.ln(8)
    pdf.set_text_color(*_MUTED)
    pdf.set_font("Helvetica", "I", 7)
    pdf.multi_cell(0, 4, _DISCLAIMER)

    # ── Page 2: Dashboard KPIs ────────────────────────────────────────────────
    pdf.add_page()
    pdf.section_header("Dashboard KPIs")

    total_energy = sum(a.get("baseline_energy_mwh", 0) for a in portfolio[:3])
    total_carbon = total_energy * 0.20482  # BEIS 2023 kgCO2e/kWh → tCO2e
    total_cost = total_energy * 1000 * 0.28  # £/MWh at 28p/kWh
    asset_count = len(portfolio[:3])

    pdf.set_fill_color(*_MID)
    pdf.set_text_color(*_ACCENT)
    pdf.set_font("Helvetica", "B", 9)

    kpis = [
        ("Total Energy Use", f"{total_energy:,.0f} MWh/yr"),
        ("Total Carbon", f"{total_carbon:,.1f} tCO₂e/yr"),
        ("Total Energy Cost", f"£{total_cost:,.0f}/yr"),
        ("Assets in Portfolio", str(asset_count)),
    ]
    col_w = 45
    for label, value in kpis:
        pdf.set_fill_color(*_MID)
        pdf.cell(col_w - 2, 18, "", fill=True, ln=False)
        x_save, y_save = pdf.get_x(), pdf.get_y()
        pdf.set_xy(pdf.get_x() - col_w + 2 + 2, y_save + 2)
        pdf.set_text_color(*_MUTED)
        pdf.set_font("Helvetica", "", 7)
        pdf.cell(col_w - 6, 5, label, ln=True)
        pdf.set_text_color(*_ACCENT)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(col_w - 6, 8, value, ln=True)
        pdf.set_xy(x_save + 2, y_save)

    pdf.ln(6)
    pdf.section_header("Per-Asset Energy Baseline")

    max_energy = max((a.get("baseline_energy_mwh", 0) for a in portfolio[:3]), default=1)
    _colours = [_ACCENT, (0, 135, 61), (240, 180, 41)]
    for i, asset in enumerate(portfolio[:3]):
        label = str(asset.get("display_name", f"Asset {i + 1}"))[:30]
        val = float(asset.get("baseline_energy_mwh", 0))
        pdf.bar(label, val, max_energy, _colours[i % len(_colours)])

    # ── Page 3: Financial Analysis ────────────────────────────────────────────
    pdf.add_page()
    pdf.section_header("Financial Analysis")

    if scenario_results:
        pdf.set_text_color(*_WHITE)
        pdf.set_font("Helvetica", "B", 8)
        headers = ["Scenario", "Energy Saving (MWh/yr)", "Cost Saving (£/yr)", "Payback (yrs)"]
        col_widths = [65, 40, 40, 30]
        for h, w in zip(headers, col_widths):
            pdf.set_fill_color(*_MID)
            pdf.cell(w, 7, h, fill=True, ln=False)
        pdf.ln()

        pdf.set_font("Helvetica", "", 8)
        for sc_name, sc_data in scenario_results.items():
            if not isinstance(sc_data, dict):
                continue
            energy_saving = sc_data.get("total_energy_saving_mwh", 0) or 0
            cost_saving = sc_data.get("total_cost_saving_gbp", 0) or 0
            payback = sc_data.get("payback_years") or "—"
            if isinstance(payback, (int, float)):
                payback_str = f"{payback:.1f}"
            else:
                payback_str = str(payback)
            pdf.set_text_color(*_WHITE)
            pdf.set_fill_color(*_DARK_BG)
            row = [str(sc_name)[:30], f"{energy_saving:,.0f}", f"£{cost_saving:,.0f}", payback_str]
            for val, w in zip(row, col_widths):
                pdf.cell(w, 6, val, fill=True, ln=False)
            pdf.ln()
    else:
        pdf.body_text("No scenario analysis data available.")

    # ── Page 4: Compliance Summary ────────────────────────────────────────────
    pdf.add_page()
    pdf.section_header("Compliance Summary")

    if compliance_results:
        for asset_name, checks in compliance_results.items():
            pdf.set_fill_color(*_MID)
            pdf.set_text_color(*_WHITE)
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(0, 7, f"  {asset_name}", fill=True, ln=True)
            if isinstance(checks, dict):
                for check_name, check_val in checks.items():
                    status = "✓ PASS" if check_val else "✗ FAIL"
                    colour = _ACCENT if check_val else (232, 76, 76)
                    pdf.set_text_color(*colour)
                    pdf.set_font("Helvetica", "", 8)
                    pdf.cell(0, 6, f"    {check_name}: {status}", ln=True)
            else:
                pdf.set_text_color(*_MUTED)
                pdf.set_font("Helvetica", "", 8)
                pdf.cell(0, 6, f"    {str(checks)}", ln=True)
            pdf.ln(2)
    else:
        pdf.body_text("No compliance data available for this portfolio.")

    # ── Page 5: Disclaimer + Data Sources ────────────────────────────────────
    pdf.add_page()
    pdf.section_header("Data Sources & Disclaimer")
    pdf.ln(3)
    pdf.set_text_color(*_MUTED)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 6, "Data Sources", ln=True)
    pdf.body_text(_DATA_SOURCES)
    pdf.ln(4)
    pdf.set_text_color(*_MUTED)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 6, "Disclaimer", ln=True)
    pdf.body_text(_DISCLAIMER)
    pdf.ln(6)
    pdf.set_text_color(*_ACCENT)
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(0, 6, f"© CrowAgent™ {date.today().year} — All rights reserved", ln=True, align="C")

    return pdf.output()


# ─────────────────────────────────────────────────────────────────────────────
# HTML fallback
# ─────────────────────────────────────────────────────────────────────────────

def _build_html(
    segment: str,
    portfolio: list[dict],
    scenario_results: dict,
    compliance_results: dict,
) -> bytes:
    """Generate an HTML report as UTF-8 bytes (fpdf2 fallback)."""
    today = date.today().strftime("%d %B %Y")
    seg_label = _SEGMENT_LABELS.get(segment, segment)

    total_energy = sum(a.get("baseline_energy_mwh", 0) for a in portfolio[:3])
    total_carbon = total_energy * 0.20482
    total_cost = total_energy * 1000 * 0.28

    def esc(v: Any) -> str:
        return html_mod.escape(str(v))

    asset_rows = ""
    for i, asset in enumerate(portfolio[:3]):
        epc = str(asset.get("epc_rating") or "?").upper()
        epc_colour = _EPC_COLOURS_HEX.get(epc, "#607D8B")
        asset_rows += f"""
        <tr>
          <td>{esc(i + 1)}</td>
          <td><strong>{esc(asset.get('display_name', 'Unknown'))}</strong></td>
          <td>{esc(asset.get('building_type', '—'))}</td>
          <td>{esc(f"{asset.get('floor_area_m2', 0):,.0f} m²")}</td>
          <td style="color:{epc_colour};font-weight:700;">{esc(epc)}</td>
          <td>{esc(asset.get('baseline_energy_mwh', 0)):} MWh/yr</td>
          <td>{esc(asset.get('built_year', '—'))}</td>
          <td>{esc(asset.get('postcode', '—'))}</td>
        </tr>"""

    scenario_rows = ""
    for sc_name, sc_data in (scenario_results or {}).items():
        if not isinstance(sc_data, dict):
            continue
        energy_saving = sc_data.get("total_energy_saving_mwh", 0) or 0
        cost_saving = sc_data.get("total_cost_saving_gbp", 0) or 0
        payback = sc_data.get("payback_years")
        payback_str = f"{payback:.1f} yrs" if isinstance(payback, (int, float)) else "—"
        scenario_rows += f"""
        <tr>
          <td>{esc(sc_name)}</td>
          <td>{esc(f'{energy_saving:,.0f}')} MWh/yr</td>
          <td>£{esc(f'{cost_saving:,.0f}')}/yr</td>
          <td>{esc(payback_str)}</td>
        </tr>"""

    compliance_rows = ""
    for asset_name, checks in (compliance_results or {}).items():
        if isinstance(checks, dict):
            for check_name, check_val in checks.items():
                status = "✓ PASS" if check_val else "✗ FAIL"
                colour = "#00C2A8" if check_val else "#E84C4C"
                compliance_rows += f"""
                <tr>
                  <td>{esc(asset_name)}</td>
                  <td>{esc(check_name)}</td>
                  <td style="color:{colour};font-weight:700;">{status}</td>
                </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>CrowAgent Portfolio Report — {esc(seg_label)}</title>
<style>
  body {{
    font-family: Helvetica, Arial, sans-serif;
    background: #071A2F;
    color: #F0F4F8;
    margin: 0; padding: 2rem;
    font-size: 13px;
  }}
  h1 {{ color: #00C2A8; margin-bottom: 0; }}
  h2 {{ color: #00C2A8; border-bottom: 1px solid #1A3A5C; padding-bottom: 4px; }}
  h3 {{ color: #8AACBF; }}
  p  {{ color: #CBD8E6; }}
  table {{
    width: 100%; border-collapse: collapse; margin-bottom: 1.5rem;
  }}
  th {{
    background: #1A3A5C; color: #00C2A8;
    padding: 8px; text-align: left; font-size: 11px;
  }}
  td {{
    border-bottom: 1px solid #1A3A5C;
    padding: 7px; color: #CBD8E6; vertical-align: top;
  }}
  .kpi-grid {{
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 1.5rem;
  }}
  .kpi-card {{
    background: #1A3A5C; border-radius: 8px; padding: 12px;
  }}
  .kpi-label {{ color: #8AACBF; font-size: 11px; margin-bottom: 4px; }}
  .kpi-value {{ color: #00C2A8; font-size: 1.4rem; font-weight: 700; }}
  .disclaimer {{ color: #5A7A90; font-size: 11px; font-style: italic; margin-top: 2rem; }}
  .footer {{ text-align: center; color: #5A7A90; font-size: 10px; margin-top: 3rem; }}
  @media print {{ body {{ background: white; color: black; }} }}
</style>
</head>
<body>

<h1>CrowAgent™</h1>
<p style="color:#8AACBF;margin-top:0;">Portfolio Analysis Report</p>
<h2 style="font-size:1.3rem;">{esc(seg_label)}</h2>
<p style="color:#8AACBF;">Generated: {esc(today)}</p>

<h2>Dashboard KPIs</h2>
<div class="kpi-grid">
  <div class="kpi-card">
    <div class="kpi-label">Total Energy Use</div>
    <div class="kpi-value">{total_energy:,.0f} MWh/yr</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Total Carbon</div>
    <div class="kpi-value">{total_carbon:,.1f} tCO₂e/yr</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Total Energy Cost</div>
    <div class="kpi-value">£{total_cost:,.0f}/yr</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Assets</div>
    <div class="kpi-value">{len(portfolio[:3])}</div>
  </div>
</div>

<h2>Portfolio Assets</h2>
<table>
  <thead>
    <tr>
      <th>#</th><th>Name</th><th>Type</th><th>Floor Area</th>
      <th>EPC</th><th>Energy</th><th>Built</th><th>Postcode</th>
    </tr>
  </thead>
  <tbody>{asset_rows}</tbody>
</table>

<h2>Financial Analysis — Scenario Comparison</h2>
{'<table><thead><tr><th>Scenario</th><th>Energy Saving</th><th>Cost Saving</th><th>Payback</th></tr></thead><tbody>' + scenario_rows + '</tbody></table>'
  if scenario_rows else '<p>No scenario data available.</p>'}

<h2>Compliance Summary</h2>
{'<table><thead><tr><th>Asset</th><th>Check</th><th>Status</th></tr></thead><tbody>' + compliance_rows + '</tbody></table>'
  if compliance_rows else '<p>No compliance data available.</p>'}

<h2>Data Sources</h2>
<p class="disclaimer">{esc(_DATA_SOURCES)}</p>

<h2>Disclaimer</h2>
<p class="disclaimer">{esc(_DISCLAIMER)}</p>

<div class="footer">
  &copy; CrowAgent™ {date.today().year} — All rights reserved — Confidential
</div>

</body>
</html>"""

    return html.encode("utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def generate_portfolio_report(
    segment: str,
    portfolio: list[dict],
    scenario_results: dict | None = None,
    compliance_results: dict | None = None,
) -> bytes:
    """
    Generate a portfolio report as bytes.

    Parameters
    ----------
    segment:
        The user segment key (e.g. "university_he").
    portfolio:
        List of portfolio asset dicts (up to 3).
    scenario_results:
        Optional dict mapping scenario name → result dict.
        Expected keys per result: total_energy_saving_mwh,
        total_cost_saving_gbp, payback_years.
    compliance_results:
        Optional dict mapping asset name → compliance check dict.

    Returns
    -------
    bytes
        PDF bytes if fpdf2 is installed, otherwise UTF-8 HTML bytes.
        Compatible with st.download_button(data=...).
    """
    sc = scenario_results or {}
    co = compliance_results or {}

    if FPDF is not None:
        try:
            return _build_pdf(segment, portfolio, sc, co)
        except Exception:
            pass  # fall through to HTML

    return _build_html(segment, portfolio, sc, co)
