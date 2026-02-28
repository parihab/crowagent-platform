# ═══════════════════════════════════════════════════════════════════════════════
# CrowAgent™ Platform — Canonical Constants Registry
# © 2026 Aparajita Parihar. All rights reserved.
#
# Single source of truth for all physical, financial, and regulatory constants.
# All modules MUST import from here — never redefine constants locally.
#
# Sources:
#   BEIS GHG Conversion Factors 2023
#   SAP 10.2 methodology (DLUHC)
#   Part L Building Regulations 2021 uplift
#   MEES (England & Wales) 2023
#   CIBSE Guide A (environmental design)
#   Raissi et al. (2019) doi:10.1016/j.jcp.2018.10.045 (PINN basis)
#
# This file has ZERO Streamlit, ZERO network, and ZERO side-effect imports.
# It is safe to import in any context, including unit tests without a
# running Streamlit server.
# ═══════════════════════════════════════════════════════════════════════════════

from __future__ import annotations

# ─────────────────────────────────────────────────────────────────────────────
# PHYSICS CONSTANTS
# Sourced from: core/physics.py
# ─────────────────────────────────────────────────────────────────────────────

# UK national grid electricity carbon intensity — BEIS 2023
GRID_CARBON_INTENSITY_KG_PER_KWH: float = 0.20482  # kgCO₂e / kWh

# Default electricity tariff (SMB commercial rate assumption)
DEFAULT_ELECTRICITY_TARIFF_GBP_PER_KWH: float = 0.28  # £ / kWh

# Internal heating setpoint temperature
HEATING_SETPOINT_C: float = 21.0  # °C

# Annual heating season hours (UK average commercial building)
HEATING_HOURS_PER_YEAR: float = 5800.0  # hours / year

# Infiltration heat capacity factor — ISO 13789 proxy
INFILTRATION_HEAT_CAPACITY_FACTOR: float = 0.33  # Wh / m³·K

# Baseline air changes per hour (unoccupied leakage)
BASE_ACH: float = 0.7  # ACH

# UK annual total horizontal solar irradiance
SOLAR_IRRADIANCE_KWH_M2_YEAR: float = 950.0  # kWh / m² / year

# Effective solar aperture factor for south-facing vertical glazing
SOLAR_APERTURE_FACTOR: float = 0.6

# Solar gain utilisation factor (thermal mass proxy)
SOLAR_UTILISATION_FACTOR: float = 0.3


# ─────────────────────────────────────────────────────────────────────────────
# GHG CONVERSION FACTORS — BEIS 2023
# Sourced from: app/compliance.py
# ─────────────────────────────────────────────────────────────────────────────

CI_ELECTRICITY: float = 0.20482  # kgCO₂e / kWh — UK grid (Scope 2)
CI_GAS: float         = 0.18316  # kgCO₂e / kWh — natural gas (Scope 1)
CI_OIL: float         = 0.24615  # kgCO₂e / kWh — gas oil (Scope 1)
CI_LPG: float         = 0.21435  # kgCO₂e / kWh — LPG (Scope 1)


# ─────────────────────────────────────────────────────────────────────────────
# ENERGY COST ASSUMPTIONS
# Sourced from: app/compliance.py
# ─────────────────────────────────────────────────────────────────────────────

ELEC_COST_PER_KWH: float = 0.28  # £ / kWh — SMB commercial rate
GAS_COST_PER_KWH: float  = 0.07  # £ / kWh


# ─────────────────────────────────────────────────────────────────────────────
# EPC / SAP BAND LOOKUP — SAP 10.2 (indicative proxy only)
# Sourced from: app/compliance.py
#
# Each tuple: (min_sap_score, band_letter, hex_colour)
# Thresholds: A ≥ 92 · B 81–91 · C 69–80 · D 55–68 · E 39–54 · F 21–38 · G 1–20
# ─────────────────────────────────────────────────────────────────────────────

EPC_BANDS: list[tuple[int, str, str]] = [
    (92, "A", "#00873D"),
    (81, "B", "#2ECC40"),
    (69, "C", "#85C226"),
    (55, "D", "#F0B429"),
    (39, "E", "#F06623"),
    (21, "F", "#E84C4C"),
    (1,  "G", "#C0392B"),
]


# ─────────────────────────────────────────────────────────────────────────────
# MEES THRESHOLDS — England & Wales (non-domestic properties)
# Sourced from: app/compliance.py
# ─────────────────────────────────────────────────────────────────────────────

MEES_CURRENT_MIN_BAND: str = "E"  # In force since April 2023
MEES_2028_TARGET_BAND: str = "C"  # Planned for new tenancies by 2028
MEES_2030_TARGET_BAND: str = "C"  # All leases by 2030


# ─────────────────────────────────────────────────────────────────────────────
# PART L 2021 U-VALUE TARGETS — Domestic (new dwellings, notional building)
# Sourced from: app/compliance.py
# ─────────────────────────────────────────────────────────────────────────────

PART_L_2021_U_WALL:    float = 0.18  # W / m²K
PART_L_2021_U_ROOF:    float = 0.11  # W / m²K
PART_L_2021_U_GLAZING: float = 1.20  # W / m²K

# Future Homes Standard — maximum primary energy (indicative; final TBC)
FHS_MAX_PRIMARY_ENERGY: int = 35  # kWh / m² / year


# ─────────────────────────────────────────────────────────────────────────────
# PART L 2021 U-VALUE TARGETS — Non-Domestic (new builds / major renovations)
# Sourced from: app/compliance.py
# ─────────────────────────────────────────────────────────────────────────────

PART_L_2021_ND_U_WALL:    float = 0.26  # W / m²K
PART_L_2021_ND_U_ROOF:    float = 0.18  # W / m²K
PART_L_2021_ND_U_GLAZING: float = 1.60  # W / m²K
