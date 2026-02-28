# ═══════════════════════════════════════════════════════════════════════════════
# CrowAgent™ Platform — Scenario & Segment Registry
# © 2026 Aparajita Parihar. All rights reserved.
#
# Single source of truth for:
#   • SCENARIOS          — intervention scenario definitions (physics parameters)
#   • SEGMENT_SCENARIOS  — per-segment scenario whitelists
#   • SEGMENT_DEFAULT_SCENARIOS — per-segment default selections
#
# Sourced from:
#   core/physics.py      — SCENARIOS dict (verbatim copy)
#   app/main.py          — SEGMENT_SCENARIOS, SEGMENT_DEFAULT_SCENARIOS (verbatim copy)
#
# This file has ZERO Streamlit and ZERO network imports.
# It is safe to import in unit tests and CLI contexts.
# ═══════════════════════════════════════════════════════════════════════════════

from __future__ import annotations

# ─────────────────────────────────────────────────────────────────────────────
# INTERVENTION SCENARIOS
# Each entry defines the physics multipliers and financial parameters for one
# retrofit intervention.  Keys must be stable — they are referenced by
# SEGMENT_SCENARIOS whitelists below.
# ─────────────────────────────────────────────────────────────────────────────

SCENARIOS: dict[str, dict] = {
    "Baseline (No Intervention)": {
        "description":            "Current state — no modifications applied.",
        "u_wall_factor":          1.0,
        "u_roof_factor":          1.0,
        "u_glazing_factor":       1.0,
        "solar_gain_reduction":   0.0,
        "infiltration_reduction": 0.0,
        "renewable_kwh":          0,
        "install_cost_gbp":       0,
        "colour":                 "#4A6FA5",
        "icon":                   "🏢",
    },
    "Solar Glass Installation": {
        "description":            "Replace standard glazing with BIPV solar glass. U-value improvement ~45%.",
        "u_wall_factor":          1.0,
        "u_roof_factor":          1.0,
        "u_glazing_factor":       0.55,
        "solar_gain_reduction":   0.15,
        "infiltration_reduction": 0.05,
        "renewable_kwh":          42000,
        "install_cost_gbp":       280000,
        "colour":                 "#00C2A8",
        "icon":                   "☀️",
    },
    "Green Roof Installation": {
        "description":            "Vegetated green roof layer. Roof U-value improvement ~55%.",
        "u_wall_factor":          1.0,
        "u_roof_factor":          0.45,
        "u_glazing_factor":       1.0,
        "solar_gain_reduction":   0.0,
        "infiltration_reduction": 0.02,
        "renewable_kwh":          0,
        "install_cost_gbp":       95000,
        "colour":                 "#1DB87A",
        "icon":                   "🌱",
    },
    "Enhanced Insulation Upgrade": {
        "description":            "Wall, roof and glazing upgrade to near-Passivhaus standard.",
        "u_wall_factor":          0.40,
        "u_roof_factor":          0.35,
        "u_glazing_factor":       0.70,
        "solar_gain_reduction":   0.0,
        "infiltration_reduction": 0.20,
        "renewable_kwh":          0,
        "install_cost_gbp":       520000,
        "colour":                 "#0A5C3E",
        "icon":                   "🏗️",
    },
    "Combined Package (All Interventions)": {
        "description":            "Solar glass + green roof + enhanced insulation simultaneously.",
        "u_wall_factor":          0.40,
        "u_roof_factor":          0.35,
        "u_glazing_factor":       0.55,
        "solar_gain_reduction":   0.15,
        "infiltration_reduction": 0.22,
        "renewable_kwh":          42000,
        "install_cost_gbp":       895000,
        "colour":                 "#062E1E",
        "icon":                   "⚡",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# PER-SEGMENT SCENARIO WHITELISTS
# Defines which scenarios are available for each user segment.
# Every entry must reference a key that exists in SCENARIOS above.
# Sourced from: app/main.py  SEGMENT_SCENARIOS dict
# ─────────────────────────────────────────────────────────────────────────────

SEGMENT_SCENARIOS: dict[str, list[str]] = {
    "university_he": [
        "Baseline (No Intervention)",
        "Solar Glass Installation",
        "Green Roof Installation",
        "Enhanced Insulation Upgrade",
        "Combined Package (All Interventions)",
    ],
    "smb_landlord": [
        "Baseline (No Intervention)",
        "Enhanced Insulation Upgrade",
        "Combined Package (All Interventions)",
    ],
    "smb_industrial": [
        "Baseline (No Intervention)",
        "Solar Glass Installation",
        "Enhanced Insulation Upgrade",
        "Combined Package (All Interventions)",
    ],
    "individual_selfbuild": [
        "Baseline (No Intervention)",
        "Enhanced Insulation Upgrade",
        "Combined Package (All Interventions)",
    ],
}


# ─────────────────────────────────────────────────────────────────────────────
# PER-SEGMENT DEFAULT SCENARIO SELECTIONS
# Defines which scenarios are pre-selected on first load for each segment.
# Every entry must reference a key that exists in SCENARIOS above.
# Sourced from: app/main.py  SEGMENT_DEFAULT_SCENARIOS dict
# ─────────────────────────────────────────────────────────────────────────────

SEGMENT_DEFAULT_SCENARIOS: dict[str, list[str]] = {
    "university_he": [
        "Baseline (No Intervention)",
        "Combined Package (All Interventions)",
    ],
    "smb_landlord": [
        "Baseline (No Intervention)",
        "Combined Package (All Interventions)",
    ],
    "smb_industrial": [
        "Baseline (No Intervention)",
        "Combined Package (All Interventions)",
    ],
    "individual_selfbuild": [
        "Baseline (No Intervention)",
        "Combined Package (All Interventions)",
    ],
}


# ─────────────────────────────────────────────────────────────────────────────
# INTEGRITY ASSERTION (runs at import time — zero cost in production)
# Raises AssertionError immediately if a whitelist references a missing scenario.
# ─────────────────────────────────────────────────────────────────────────────

def _assert_whitelist_integrity() -> None:
    for seg_id, whitelist in SEGMENT_SCENARIOS.items():
        for name in whitelist:
            assert name in SCENARIOS, (
                f"config/scenarios.py integrity error: "
                f"segment '{seg_id}' references unknown scenario '{name}'"
            )
    for seg_id, defaults in SEGMENT_DEFAULT_SCENARIOS.items():
        for name in defaults:
            assert name in SCENARIOS, (
                f"config/scenarios.py integrity error: "
                f"segment '{seg_id}' default references unknown scenario '{name}'"
            )
        whitelist = SEGMENT_SCENARIOS.get(seg_id, [])
        for name in defaults:
            assert name in whitelist, (
                f"config/scenarios.py integrity error: "
                f"segment '{seg_id}' default '{name}' is not in its whitelist"
            )


_assert_whitelist_integrity()
