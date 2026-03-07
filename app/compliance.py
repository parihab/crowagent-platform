# ═══════════════════════════════════════════════════════════════════════════════
# CrowAgent™ Platform — UK Compliance Module
# © 2026 Aparajita Parihar. All rights reserved.
#
# Covers:
#   • EPC rating estimation + MEES gap analysis (SMB landlords)
#   • SECR / Scope 1 & 2 carbon baseline (SMB industrial)
#   • Part L / Future Homes Standard compliance check (individual self-build)
#
# Data sources:
#   BEIS GHG Conversion Factors 2023 · SAP 10.2 methodology (DLUHC) ·
#   Part L Building Regulations 2021 uplift · MEES (England & Wales) 2023 ·
#   SECR framework (Companies Act 2006 (Strategic Report) and Directors' Report
#   (Amendment) Regulations 2013)
#
# DISCLAIMER: Results are indicative only. Not a substitute for a formal
# SAP/SBEM assessment by an accredited energy assessor.
# ═══════════════════════════════════════════════════════════════════════════════

from __future__ import annotations
from typing import Optional

from config.constants import (
    CI_ELECTRICITY,
    CI_GAS,
    CI_OIL,
    CI_LPG,
    ELEC_COST_PER_KWH,
    GAS_COST_PER_KWH,
    EPC_BANDS,
    MEES_CURRENT_MIN_BAND,
    MEES_2028_TARGET_BAND,
    MEES_2030_TARGET_BAND,
    PART_L_2021_U_WALL,
    PART_L_2021_U_ROOF,
    PART_L_2021_U_GLAZING,
    PART_L_2021_ND_U_WALL,
    PART_L_2021_ND_U_ROOF,
    PART_L_2021_ND_U_GLAZING,
    FHS_MAX_PRIMARY_ENERGY,
)

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS — BEIS GHG Conversion Factors 2023
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# SAP/EPC BAND LOOKUP  (SAP 10.2 — proxy, indicative only)
# Band thresholds: A ≥ 92 · B 81–91 · C 69–80 · D 55–68 · E 39–54 · F 21–38 · G 1–20
# ─────────────────────────────────────────────────────────────────────────────
# EPC_BANDS imported from config.constants
# Note: config.constants defines EPC_BANDS as a dict {Band: (min, max)}.
# The original list format [(92, "A", "#00873D"), ...] is used here for logic.
# We reconstruct the list format locally for compatibility with existing functions
# while using the thresholds from config.

_EPC_BANDS_LIST: list[tuple[int, str, str]] = [
    (b["threshold"], b["band"], b["colour"]) for b in EPC_BANDS
]

# ─────────────────────────────────────────────────────────────────────────────
# SEGMENT BUILDING TEMPLATES
# These supplement the existing university buildings and become available
# when a non-university user segment is selected.
# ─────────────────────────────────────────────────────────────────────────────
# SEGMENT_BUILDINGS removed. Building templates now live in app/segments/*.py

# ─────────────────────────────────────────────────────────────────────────────
# VALIDATION HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def validate_energy_kwh(kwh: float, label: str = "Energy") -> tuple[bool, str]:
    """Validate an annual energy consumption figure (kWh)."""
    if not isinstance(kwh, (int, float)):
        return False, f"{label} must be a number."
    if kwh < 0:
        return False, f"{label} cannot be negative."
    if kwh > 100_000_000:
        return False, f"{label} value ({kwh:,.0f} kWh) is unrealistically large — please check."
    return True, "ok"


def validate_floor_area(area_m2: float) -> tuple[bool, str]:
    """Validate a floor area in m²."""
    if not isinstance(area_m2, (int, float)):
        return False, "Floor area must be a number."
    if area_m2 <= 0:
        return False, "Floor area must be greater than zero."
    if area_m2 > 1_000_000:
        return False, f"Floor area ({area_m2:,.0f} m²) is unrealistically large."
    return True, "ok"


def validate_u_value(u: float, label: str = "U-value") -> tuple[bool, str]:
    """Validate a U-value in W/m²K (range 0.05–6.0 is physically plausible)."""
    if not isinstance(u, (int, float)):
        return False, f"{label} must be a number."
    if u <= 0:
        return False, f"{label} must be greater than zero."
    if u > 6.0:
        return False, f"{label} ({u} W/m²K) is outside the physically plausible range (≤ 6.0)."
    return True, "ok"


# ─────────────────────────────────────────────────────────────────────────────
# EPC RATING ESTIMATION  (SAP 10.2 proxy, indicative)
# ─────────────────────────────────────────────────────────────────────────────

def _band_from_sap(sap: float) -> tuple[str, str]:
    """Return (band_letter, hex_colour) for a given SAP score."""
    for threshold, band, colour in _EPC_BANDS_LIST:
        if sap >= threshold:
            return band, colour
    return "G", "#C0392B"


def estimate_epc_rating(
    floor_area_m2: float | None = None,
    annual_energy_kwh: float | None = None,
    u_wall: float = PART_L_2021_ND_U_WALL,
    u_roof: float = PART_L_2021_ND_U_ROOF,
    u_glazing: float = PART_L_2021_ND_U_GLAZING,
    glazing_ratio: float = 0.30,
    building_type: str = "commercial",
    building: dict | None = None,
) -> dict:
    """
    Estimate an indicative EPC rating based on energy intensity and fabric U-values.

    Methodology: proxy SAP score derived from:
      - Energy use intensity (EUI) kWh/m²/yr mapped to a 0–100 scale
      - Fabric penalty from U-values relative to Part L 2021 targets
      - Glazing adjustment

    Returns a dict with keys:
      sap_score      : float  — estimated SAP score (0–100)
      epc_band       : str    — A–G
      epc_colour     : str    — hex colour for the band
      eui_kwh_m2     : float  — energy use intensity
      mees_compliant_now  : bool  — meets current E minimum (England & Wales)
      mees_2028_compliant : bool  — meets planned C target
      mees_gap_bands      : int   — bands below 2028 target (0 = compliant)
      recommendation      : str   — plain English summary

    DISCLAIMER: Indicative only. Not a formal SAP/SBEM assessment.
    """
    # Backward-compatible object input
    if building is not None:
        floor_area_m2 = building.get("floor_area_m2", floor_area_m2)
        if annual_energy_kwh is None:
            annual_energy_kwh = building.get("baseline_energy_mwh", 0.0) * 1000.0

    # Input validation
    ok, msg = validate_floor_area(floor_area_m2)
    if not ok:
        raise ValueError(f"EPC estimation: {msg}")
    ok, msg = validate_energy_kwh(annual_energy_kwh, "Annual energy")
    if not ok:
        raise ValueError(f"EPC estimation: {msg}")
    for label, val in [("U-wall", u_wall), ("U-roof", u_roof), ("U-glazing", u_glazing)]:
        ok, msg = validate_u_value(val, label)
        if not ok:
            raise ValueError(f"EPC estimation: {msg}")
    if not 0.0 < glazing_ratio < 1.0:
        raise ValueError("EPC estimation: glazing_ratio must be between 0 and 1 (exclusive).")

    eui = annual_energy_kwh / max(floor_area_m2, 1.0)   # kWh/m²/yr

    # Map EUI to a base SAP score (lower EUI = higher SAP)
    # Reference ranges (approximate, non-domestic mixed use):
    #   EUI < 50   → very efficient  (SAP 90+)
    #   EUI 50–100 → good (SAP 75–89)
    #   EUI 100–175 → average (SAP 55–74)
    #   EUI 175–250 → poor (SAP 40–54)
    #   EUI 250+   → very poor (SAP < 40)
    if eui <= 50:
        base_sap = 90 + max(0.0, (50 - eui) / 50 * 9)     # up to 99
    elif eui <= 100:
        base_sap = 75 + (100 - eui) / 50 * 15
    elif eui <= 175:
        base_sap = 55 + (175 - eui) / 75 * 20
    elif eui <= 250:
        base_sap = 40 + (250 - eui) / 75 * 15
    else:
        base_sap = max(1.0, 40 - (eui - 250) / 10)

    # Fabric penalty: compare U-values to Part L 2021 notional targets
    if building_type in ("residential", "individual_selfbuild"):
        ref_u_wall    = PART_L_2021_U_WALL
        ref_u_roof    = PART_L_2021_U_ROOF
        ref_u_glazing = PART_L_2021_U_GLAZING
    else:
        ref_u_wall    = PART_L_2021_ND_U_WALL
        ref_u_roof    = PART_L_2021_ND_U_ROOF
        ref_u_glazing = PART_L_2021_ND_U_GLAZING

    # Penalty per unit excess U-value above target (scaled to SAP points)
    wall_penalty    = max(0.0, u_wall    - ref_u_wall)    * 8
    roof_penalty    = max(0.0, u_roof    - ref_u_roof)    * 6
    glazing_penalty = max(0.0, u_glazing - ref_u_glazing) * 2 * glazing_ratio * 10

    sap_score = max(1.0, min(100.0, base_sap - wall_penalty - roof_penalty - glazing_penalty))

    band, colour = _band_from_sap(sap_score)

    # MEES compliance checks
    band_order = ["A", "B", "C", "D", "E", "F", "G"]
    band_idx = band_order.index(band)
    mees_min_idx     = band_order.index(MEES_CURRENT_MIN_BAND)   # E = index 4
    mees_2028_idx    = band_order.index(MEES_2028_TARGET_BAND)   # C = index 2

    mees_compliant_now  = band_idx <= mees_min_idx
    mees_2028_compliant = band_idx <= mees_2028_idx
    mees_gap_bands      = max(0, band_idx - mees_2028_idx)

    # Plain English recommendation
    if mees_2028_compliant:
        recommendation = (
            f"EPC {band} — already meets the planned 2028 MEES minimum (C). "
            "No additional upgrade is typically required for MEES C alignment, subject to formal EPC confirmation."
        )
    elif mees_compliant_now:
        recommendation = (
            f"EPC {band} — meets the current MEES minimum (E) but is {mees_gap_bands} band(s) "
            f"below the planned 2028 target (C). Improvement works are recommended before 2028 "
            "to avoid letting restrictions and civil penalties."
        )
    else:
        recommendation = (
            f"EPC {band} — below the current MEES minimum (E). This property cannot legally be "
            "let in England & Wales without an applicable exemption. Immediate improvement planning "
            "and accredited EPC reassessment are advised before letting decisions."
        )

    return {
        "sap_score":           round(sap_score, 1),
        "epc_band":            band,
        "epc_colour":          colour,
        "band":                band,
        "color":               colour,
        "eui_kwh_m2":          round(eui, 1),
        "mees_compliant_now":  mees_compliant_now,
        "mees_2028_compliant": mees_2028_compliant,
        "mees_gap_bands":      mees_gap_bands,
        "recommendation":      recommendation,
    }


# ─────────────────────────────────────────────────────────────────────────────
# MEES GAP ANALYSIS — upgrade cost and measure prioritisation
# ─────────────────────────────────────────────────────────────────────────────

# Indicative cost ranges for common retrofit measures (England, 2024 prices)
MEES_MEASURES: list[dict] = [
    {
        "name":        "Loft / Roof Insulation Upgrade",
        "sap_lift":    6,
        "cost_low":    2_500,
        "cost_high":   8_000,
        "u_roof_improvement": 0.60,   # factor reduction on u_roof
        "regulation":  "Part L 2021 · MEES compliance measure",
    },
    {
        "name":        "Cavity / External Wall Insulation",
        "sap_lift":    8,
        "cost_low":    5_000,
        "cost_high":   25_000,
        "u_wall_improvement": 0.45,
        "regulation":  "Part L 2021 · MEES compliance measure",
    },
    {
        "name":        "Double / Triple Glazing Upgrade",
        "sap_lift":    4,
        "cost_low":    4_000,
        "cost_high":   18_000,
        "u_glazing_improvement": 0.55,
        "regulation":  "Part L 2021 · MEES compliance measure",
    },
    {
        "name":        "LED Lighting Replacement",
        "sap_lift":    3,
        "cost_low":    1_500,
        "cost_high":   6_000,
        "regulation":  "ESOS / MEES supporting measure",
    },
    {
        "name":        "Air Source Heat Pump (ASHP)",
        "sap_lift":    12,
        "cost_low":    8_000,
        "cost_high":   20_000,
        "regulation":  "Future Homes Standard · Boiler Upgrade Scheme eligible",
    },
    {
        "name":        "Rooftop Solar PV (10 kWp)",
        "sap_lift":    7,
        "cost_low":    8_000,
        "cost_high":   15_000,
        "regulation":  "Part L 2021 · Smart Export Guarantee eligible",
    },
]


def mees_gap_analysis(current_sap: float, target_band: str = "C") -> dict:
    """
    Identify the minimum set of measures to reach the target EPC band.

    Returns:
      target_sap       : float — minimum SAP score for target band
      sap_gap          : float — SAP points needed
      recommended_measures : list[dict] — ordered by SAP lift per £ cost
      total_cost_low   : int — indicative lower cost estimate (£)
      total_cost_high  : int — indicative upper cost estimate (£)
      achievable       : bool — can target be reached with listed measures
    """
    if target_band not in [b for _, b, _ in _EPC_BANDS_LIST]:
        raise ValueError(f"Invalid target band '{target_band}'. Must be A–G.")

    target_sap = next(thresh for thresh, band, _ in _EPC_BANDS_LIST if band == target_band)
    sap_gap = max(0.0, target_sap - current_sap)

    if sap_gap <= 0:
        return {
            "target_sap":            target_sap,
            "sap_gap":               0.0,
            "recommended_measures":  [],
            "total_cost_low":        0,
            "total_cost_high":       0,
            "achievable":            True,
        }

    # Sort by SAP lift per midpoint cost (best value first)
    sorted_measures = sorted(
        MEES_MEASURES,
        key=lambda m: m["sap_lift"] / max((m["cost_low"] + m["cost_high"]) / 2, 1),
        reverse=True,
    )

    recommended, total_low, total_high, accumulated_sap = [], 0, 0, 0.0
    for measure in sorted_measures:
        if accumulated_sap >= sap_gap:
            break
        recommended.append(measure)
        total_low  += measure["cost_low"]
        total_high += measure["cost_high"]
        accumulated_sap += measure["sap_lift"]

    achievable = accumulated_sap >= sap_gap

    return {
        "target_sap":            target_sap,
        "sap_gap":               round(sap_gap, 1),
        "recommended_measures":  recommended,
        "total_cost_low":        total_low,
        "total_cost_high":       total_high,
        "achievable":            achievable,
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECR / SCOPE 1 & 2 CARBON BASELINE  (Companies Act 2006 / SECR 2019)
# ─────────────────────────────────────────────────────────────────────────────

def calculate_carbon_baseline(
    elec_kwh:        float = 0.0,
    gas_kwh:         float = 0.0,
    oil_kwh:         float = 0.0,
    lpg_kwh:         float = 0.0,
    fleet_miles:     float = 0.0,
    floor_area_m2:   Optional[float] = None,
) -> dict:
    """
    Calculate Scope 1 and Scope 2 carbon emissions for SECR reporting.

    Inputs (all annual figures):
      elec_kwh      : kWh — purchased electricity (Scope 2)
      gas_kwh       : kWh — natural gas combustion (Scope 1)
      oil_kwh       : kWh — gas oil / diesel combustion (Scope 1)
      lpg_kwh       : kWh — LPG combustion (Scope 1)
      fleet_miles   : miles — business fleet miles (Scope 1, car average 0.168 kgCO2e/mile)
      floor_area_m2 : m² — optional, used to compute intensity metric

    Returns:
      scope1_tco2e        : float — Scope 1 total (tCO₂e)
      scope2_tco2e        : float — Scope 2 total (tCO₂e)
      total_tco2e         : float — combined
      intensity_kgco2_m2  : float | None — kgCO₂e/m² (if floor_area provided)
      annual_energy_kwh   : float — total purchased energy
      breakdown           : dict — per-source figures
      secr_threshold_check: dict — indicative SECR reporting obligation check

    DISCLAIMER: Simplified calculation. SECR reporting requires
    methodology disclosure and may need third-party verification.
    """
    # Input validation
    inputs = {
        "Electricity": elec_kwh,
        "Gas": gas_kwh,
        "Oil": oil_kwh,
        "LPG": lpg_kwh,
        "Fleet miles": fleet_miles,
    }
    for label, val in inputs.items():
        ok, msg = validate_energy_kwh(float(val), label)
        if not ok and label != "Fleet miles":
            raise ValueError(f"Carbon baseline: {msg}")
        if val < 0:
            raise ValueError(f"Carbon baseline: {label} cannot be negative.")

    if floor_area_m2 is not None:
        ok, msg = validate_floor_area(floor_area_m2)
        if not ok:
            raise ValueError(f"Carbon baseline: {msg}")

    # Scope 1: combustion + fleet
    fleet_kgco2 = fleet_miles * 0.168  # avg car — BEIS 2023 medium petrol car
    gas_kgco2   = gas_kwh  * CI_GAS
    oil_kgco2   = oil_kwh  * CI_OIL
    lpg_kgco2   = lpg_kwh  * CI_LPG
    scope1_kgco2 = gas_kgco2 + oil_kgco2 + lpg_kgco2 + fleet_kgco2

    # Scope 2: electricity (location-based, BEIS 2023 UK grid)
    scope2_kgco2 = elec_kwh * CI_ELECTRICITY

    scope1_tco2e = scope1_kgco2 / 1000.0
    scope2_tco2e = scope2_kgco2 / 1000.0
    total_tco2e  = scope1_tco2e + scope2_tco2e

    total_energy_kwh = elec_kwh + gas_kwh + oil_kwh + lpg_kwh

    intensity = (
        (total_tco2e * 1000.0 / floor_area_m2)
        if floor_area_m2 and floor_area_m2 > 0 else None
    )

    # Indicative SECR obligation check (large company threshold)
    # Large = 250+ employees OR £36M+ turnover OR £18M+ balance sheet
    # SMBs below threshold: voluntary but supply-chain pressure applies
    secr_check = {
        "mandatory_reporter":    False,   # SMB tool — users below threshold
        "supply_chain_pressure": total_tco2e > 50,  # >50 tCO2e likely triggers buyer requests
        "pas2060_candidacy":     total_tco2e < 500,  # PAS 2060 practical for small footprints
        "note": (
            "SECR mandatory reporting applies to large UK companies (250+ employees, "
            "£36M+ turnover). SMBs below this threshold are not legally required to "
            "report but face increasing supply-chain pressure from large corporate buyers."
        ),
    }

    return {
        "scope1_tco2e":       round(scope1_tco2e, 2),
        "scope2_tco2e":       round(scope2_tco2e, 2),
        "total_tco2e":        round(total_tco2e, 2),
        "intensity_kgco2_m2": round(intensity, 1) if intensity is not None else None,
        "annual_energy_kwh":  round(total_energy_kwh, 0),
        "breakdown": {
            "electricity_scope2_tco2e": round(scope2_kgco2 / 1000, 2),
            "gas_scope1_tco2e":         round(gas_kgco2   / 1000, 2),
            "oil_scope1_tco2e":         round(oil_kgco2   / 1000, 2),
            "lpg_scope1_tco2e":         round(lpg_kgco2   / 1000, 2),
            "fleet_scope1_tco2e":       round(fleet_kgco2 / 1000, 2),
        },
        "secr_threshold_check": secr_check,
    }


# ─────────────────────────────────────────────────────────────────────────────
# PART L / FUTURE HOMES STANDARD COMPLIANCE  (self-build / new dwellings)
# ─────────────────────────────────────────────────────────────────────────────

def part_l_compliance_check(
    u_wall:    float,
    u_roof:    float,
    u_glazing: float,
    floor_area_m2: float,
    annual_energy_kwh: float,
    building_type: str = "residential",
) -> dict:
    """
    Check proposed fabric U-values against Part L 2021 (England) notional targets
    and estimate Future Homes Standard readiness.

    Returns:
      part_l_2021_pass     : bool
      fhs_ready            : bool
      primary_energy_est   : float — kWh/m²/yr (proxy)
      compliance_items     : list[dict] — per-element pass/fail
      overall_verdict      : str
      improvement_actions  : list[str]

    DISCLAIMER: Indicative only. Full Part L compliance requires a SAP/SBEM
    calculation by an accredited assessor submitted to Building Control.
    """
    ok, msg = validate_floor_area(floor_area_m2)
    if not ok:
        raise ValueError(f"Part L check: {msg}")
    ok, msg = validate_energy_kwh(annual_energy_kwh, "Annual energy")
    if not ok:
        raise ValueError(f"Part L check: {msg}")
    for label, val in [("U-wall", u_wall), ("U-roof", u_roof), ("U-glazing", u_glazing)]:
        ok, msg = validate_u_value(val, label)
        if not ok:
            raise ValueError(f"Part L check: {msg}")

    if building_type in ("residential", "individual_selfbuild"):
        target_wall    = PART_L_2021_U_WALL
        target_roof    = PART_L_2021_U_ROOF
        target_glazing = PART_L_2021_U_GLAZING
        regs_label     = "Part L 2021 (Dwellings — ADL1A)"
    else:
        target_wall    = PART_L_2021_ND_U_WALL
        target_roof    = PART_L_2021_ND_U_ROOF
        target_glazing = PART_L_2021_ND_U_GLAZING
        regs_label     = "Part L 2021 (Non-Domestic — ADL2A)"

    items = [
        {
            "element":       "External Wall",
            "proposed_u":    u_wall,
            "target_u":      target_wall,
            "pass":          u_wall <= target_wall,
            "gap":           round(max(0.0, u_wall - target_wall), 3),
            "unit":          "W/m²K",
        },
        {
            "element":       "Roof / Ceiling",
            "proposed_u":    u_roof,
            "target_u":      target_roof,
            "pass":          u_roof <= target_roof,
            "gap":           round(max(0.0, u_roof - target_roof), 3),
            "unit":          "W/m²K",
        },
        {
            "element":       "Windows / Glazing",
            "proposed_u":    u_glazing,
            "target_u":      target_glazing,
            "pass":          u_glazing <= target_glazing,
            "gap":           round(max(0.0, u_glazing - target_glazing), 3),
            "unit":          "W/m²K",
        },
    ]

    all_pass = all(item["pass"] for item in items)

    # Proxy primary energy kWh/m²/yr
    primary_energy_est = annual_energy_kwh / max(floor_area_m2, 1.0) * 2.5  # PE factor ~2.5 for elec

    fhs_ready = primary_energy_est <= FHS_MAX_PRIMARY_ENERGY and all_pass

    improvement_actions = []
    for item in items:
        if not item["pass"]:
            improvement_actions.append(
                f"Improve {item['element']} from {item['proposed_u']} to ≤ {item['target_u']} W/m²K "
                f"(gap: {item['gap']} W/m²K) — indicative target aligned with {regs_label}; confirm via formal design-stage assessment."
            )
    if primary_energy_est > FHS_MAX_PRIMARY_ENERGY:
        improvement_actions.append(
            f"Reduce primary energy from ~{primary_energy_est:.0f} to ≤ {FHS_MAX_PRIMARY_ENERGY} "
            "kWh/m²/yr — indicative Future Homes Standard readiness threshold. "
            "Consider ASHP, solar PV, and enhanced fabric."
        )

    if all_pass and fhs_ready:
        verdict = (
            f"PASS — All fabric elements meet {regs_label} targets and the building "
            "is indicative of strong design-stage alignment; formal compliance still requires approved SAP/SBEM evidence."
        )
    elif all_pass:
        verdict = (
            f"CONDITIONAL PASS — Fabric meets {regs_label} U-value targets but primary "
            "energy intensity is above the indicative Future Homes Standard (FHS) proxy threshold."
        )
    else:
        n_fail = sum(1 for i in items if not i["pass"])
        verdict = (
            f"FAIL — {n_fail} fabric element(s) do not meet {regs_label} targets. "
            "Design revisions are likely before Building Control sign-off, subject to formal submission calculations."
        )

    return {
        "part_l_2021_pass":      all_pass,
        "fhs_ready":             fhs_ready,
        "primary_energy_est":    round(primary_energy_est, 1),
        "fhs_threshold":         FHS_MAX_PRIMARY_ENERGY,
        "regs_label":            regs_label,
        "compliance_items":      items,
        "overall_verdict":       verdict,
        "improvement_actions":   improvement_actions,
    }


# ─────────────────────────────────────────────────────────────────────────────
# SEGMENT METADATA
# ─────────────────────────────────────────────────────────────────────────────

SEGMENT_META: dict[str, dict] = {
    "university_he": {
        "label":       "University / Higher Education",
        "icon":        "🎓",
        "description": "Campus estate managers and sustainability leads at UK universities and HE institutions.",
        "regulations": ["SECR (mandatory)", "TCFD (large HEIs)", "Part L (new builds)", "PPN 06/21"],
        "compliance_tool": None,   # existing university dashboard handles this
    },
    "individual_selfbuild": {
        "label":       "Individual / Self-Build",
        "icon":        "🏠",
        "description": "Individual self-builders and home renovators subject to UK Building Regulations.",
        "regulations": ["Part L 2021 (ADL1A)", "Future Homes Standard (from 2025/26)", "EPC (on completion)"],
        "compliance_tool": "part_l",
    },
    "smb_landlord": {
        "label":       "SMB / Commercial Landlord (MEES)",
        "icon":        "🏢",
        "description": "SMB property owners and landlords subject to Minimum Energy Efficiency Standards.",
        "regulations": ["MEES (current: E minimum)", "MEES (2028: C target)", "EPC mandatory on letting"],
        "compliance_tool": "mees",
    },
    "smb_industrial": {
        "label":       "SMB / Industrial Operator (Carbon)",
        "icon":        "🏭",
        "description": "Small manufacturers and industrial SMBs facing SECR supply-chain pressure.",
        "regulations": ["SECR (voluntary / supply-chain)", "PAS 2060", "UK ETS (if applicable)"],
        "compliance_tool": "secr",
    },
}


# Backward-compatible aliases used by legacy tests/callers
def secr_carbon_baseline(
    building: dict | None = None,
    elec_kwh: float = 0.0,
    gas_kwh: float = 0.0,
    oil_kwh: float = 0.0,
    lpg_kwh: float = 0.0,
    fleet_miles: float = 0.0,
) -> dict:
    """Compatibility wrapper for legacy SECR naming."""
    floor_area_m2 = (building or {}).get("floor_area_m2") or None
    return calculate_carbon_baseline(
        elec_kwh=elec_kwh,
        gas_kwh=gas_kwh,
        oil_kwh=oil_kwh,
        lpg_kwh=lpg_kwh,
        fleet_miles=fleet_miles,
        floor_area_m2=floor_area_m2,
    )


def part_l_check(
    building: dict,
    fabric: dict | None = None,
    scenario_energy_kwh: float | None = None,
    u_wall: float | None = None,
    u_roof: float | None = None,
    u_glazing: float | None = None,
    annual_energy_kwh: float | None = None,
    building_type: str | None = None,
) -> dict:
    """Compatibility wrapper for legacy Part L function naming."""
    fabric = fabric or {}
    floor_area_m2 = building.get("floor_area_m2")
    if annual_energy_kwh is None:
        annual_energy_kwh = scenario_energy_kwh
    if annual_energy_kwh is None:
        annual_energy_kwh = building.get("baseline_energy_mwh", 0.0) * 1000.0
    if u_wall is None:
        u_wall = fabric.get("u_wall")
    if u_roof is None:
        u_roof = fabric.get("u_roof")
    if u_glazing is None:
        u_glazing = fabric.get("u_glazing")
    if building_type is None:
        building_type = building.get("building_type", "residential")

    return part_l_compliance_check(
        u_wall=u_wall,
        u_roof=u_roof,
        u_glazing=u_glazing,
        floor_area_m2=floor_area_m2,
        annual_energy_kwh=annual_energy_kwh,
        building_type=building_type,
    )
