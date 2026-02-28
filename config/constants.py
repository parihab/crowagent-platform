"""
Single source of truth for all physical, financial, and regulatory constants.

This module centralises values that are used across the simulation engine,
compliance checkers, and UI components. It should not contain any dynamic
logic or functions, only constant definitions.

Sources:
- Carbon Factors: UK Government GHG Conversion Factors for Company Reporting 2024
- Energy Costs: Ofgem Price Cap, Q2 2026 forecast
- Building Regs: UK Part L (2021), MEES, FHS statutory instruments
"""

# ─────────────────────────────────────────────────────────────────────────────
# 1. CARBON INTENSITY FACTORS (kgCO2e / kWh)
# ─────────────────────────────────────────────────────────────────────────────
# Source: UK Government GHG Conversion Factors for Company Reporting 2024
# Using 'combined' factors which include generation and T&D losses.

CI_ELECTRICITY = 0.22535  # For grid electricity
CI_GAS = 0.18290          # For natural gas
CI_LPG = 0.23031          # For Liquefied Petroleum Gas
CI_OIL = 0.30             # For heating oil (conservative estimate)

# ─────────────────────────────────────────────────────────────────────────────
# 2. FINANCIAL CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
# Source: Ofgem price cap forecast for Q2 2026 (in GBP)

ELEC_COST_PER_KWH = 0.2467  # £/kWh for electricity
GAS_COST_PER_KWH = 0.0574   # £/kWh for natural gas
# Note: Oil and LPG costs are more volatile and typically handled differently.
# These values represent user-overridable defaults.

# ─────────────────────────────────────────────────────────────────────────────
# 3. BUILDING PHYSICS & SIMULATION DEFAULTS
# ─────────────────────────────────────────────────────────────────────────────

HEATING_SETPOINT_C = 20.0  # Assumed internal target temperature in Celsius
HEATING_HOURS_PER_YEAR = 2500.0  # Assumed annual heating operation hours
BASE_ACH = 0.5  # Air Changes per Hour baseline for a typical building
SOLAR_IRRADIANCE_KWH_M2_YEAR = 1000.0  # Average solar gain in kWh per m² of glazing per year

# ─────────────────────────────────────────────────────────────────────────────
# 4. UK BUILDING REGULATIONS & STANDARDS
# ─────────────────────────────────────────────────────────────────────────────

# Part L 2021 U-Value Targets (for existing buildings, retrofits) in W/m²K
PART_L_2021_U_WALL = 0.18
PART_L_2021_U_ROOF = 0.15
PART_L_2021_U_GLAZING = 1.4

# Future Homes Standard (FHS) 2025 Target
FHS_MAX_PRIMARY_ENERGY = 35.0  # kWh/m²/year

# Energy Performance Certificate (EPC) Bands by SAP (Standard Assessment Procedure) points
EPC_BANDS = {
    "A": (92, 1000), # 100+ is possible
    "B": (81, 91),
    "C": (69, 80),
    "D": (55, 68),
    "E": (39, 54),
    "F": (21, 38),
    "G": (1, 20),
}

# Minimum Energy Efficiency Standards (MEES) for commercial properties
MEES_CURRENT_MIN_BAND = "E"
MEES_2028_TARGET_BAND = "C"
MEES_2030_TARGET_BAND = "B"
