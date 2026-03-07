# CrowAgent™ Platform

**Sustainability AI Decision Intelligence for University Estate Management**

> ⚠️ **Working Prototype — Results Are Indicative Only.**
> Not for use as the sole basis for capital investment decisions.

---

## Project Overview

CrowAgent™ Platform is a physics-informed campus thermal intelligence system that helps university estate managers and sustainability professionals make evidence-based, cost-effective decisions for achieving Net Zero targets.

The platform combines:
- **Physics-Informed Thermal Model** (PINN methodology — Raissi et al., 2019)
- **Agentic AI Advisor** powered by Google Gemini 1.5 Flash
- **Live Weather Integration** via Open-Meteo API and Met Office DataPoint
- **Structured Scenario Comparison** across retrofit interventions
- **Multi-segment support** for universities, commercial landlords, SMB industrial, and individual self-builds

**Key Features:**
- 📊 **Dashboard** — Energy, carbon, and financial KPIs for multiple building scenarios
- 📈 **Financial Analysis** — Payback period, ROI, and cost-per-tonne CO₂ comparisons
- 🤖 **AI Advisor** — Agentic LLM with physics tool-use for expert recommendations
- 🌤 **Live Weather** — Real-time temperature integration for accurate thermal calculations
- 🏢 **Multi-Building Portfolio** — Compare interventions across your campus estate
- 📋 **Compliance Hub** — MEES, EPC, SECR, Part L 2021, and Future Homes Standard tracking

---

## Architecture

```
crowagent-platform/
├── app/                    # Streamlit UI layer
│   ├── main.py             # Application orchestrator and navigation
│   ├── session.py          # Session state initialisation
│   ├── sidebar.py          # Sidebar controls
│   ├── branding.py         # Brand colours, fonts, logo assets
│   ├── compliance.py       # Compliance data processing helpers
│   ├── visualization_3d.py # 3-D building heat-loss visualisation
│   ├── components/         # Reusable UI components
│   │   └── portfolio_manager.py
│   ├── segments/           # Segment-specific default configurations
│   │   ├── base.py
│   │   ├── university_he.py
│   │   ├── commercial_landlord.py
│   │   ├── smb_industrial.py
│   │   └── individual_selfbuild.py
│   └── tabs/               # Individual page-tab renderers
│       ├── dashboard.py
│       ├── financial.py
│       ├── compliance_hub.py
│       ├── ai_advisor.py
│       └── settings.py
├── core/                   # Core business logic (no Streamlit dependencies)
│   ├── agent.py            # Gemini AI agent and tool-use loop
│   ├── physics.py          # PINN thermal model
│   ├── orchestrator.py     # ESG agent orchestrator
│   ├── finance_agent.py    # Financial modelling agent
│   ├── retrofit_agent.py   # Retrofit recommendation agent
│   ├── risk_agent.py       # Climate risk assessment agent
│   └── about.py            # About / provenance content
├── services/               # External integrations
│   ├── epc.py              # EPC Open Data Communities API client
│   ├── weather.py          # Weather provider abstraction
│   ├── location.py         # OSM / geocoding helpers
│   ├── report_generator.py # PDF report export
│   └── audit.py            # In-session audit log
├── config/                 # Constants and scenario definitions
│   ├── constants.py        # Physical, energy, and compliance constants
│   └── scenarios.py        # Retrofit scenario definitions
├── assets/                 # SVG brand assets
├── tests/                  # Pytest test suite (24 files)
├── docs/                   # Extended documentation and guides
├── governance/             # Architecture governance documents
├── streamlit_app.py        # Entry point wrapper
├── security_check.py       # Pre-deployment security verification
├── requirements.txt
└── .env.example
```

**Data flow:**
1. User selects segment and building via Streamlit UI (`app/`)
2. `app/session.py` initialises session state and loads defaults
3. Physics calculations run in `core/physics.py` (no external calls)
4. Weather data is fetched from `services/weather.py` and injected into the physics model
5. AI Advisor (`core/agent.py`) uses Gemini with tool-use to call the physics engine
6. Results are rendered in tab modules under `app/tabs/`

---

## Setup Instructions

### Prerequisites

- Python 3.11 or 3.12
- A free [Gemini API key](https://aistudio.google.com) (for the AI Advisor tab)
- Optionally, a free [EPC Open Data Communities key](https://epc.opendatacommunities.org) (for live EPC lookups)
- Optionally, a free [Met Office DataPoint key](https://www.metoffice.gov.uk/services/data/datapoint)

### Installation

```bash
git clone https://github.com/WonderApri/crowagent-platform.git
cd crowagent-platform
```

1. Create and activate a virtual environment (recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate      # Linux / macOS
   .venv\Scripts\activate.bat     # Windows
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment variables (see next section).

---

## Environment Variables

Copy the template and fill in your own keys:

```bash
cp .env.example .env
```

| Variable | Required | Description |
|---|---|---|
| `GEMINI_KEY` | ✅ For AI Advisor | Google Gemini API key from [aistudio.google.com](https://aistudio.google.com) |
| `EPC_API_KEY` | ❌ Optional | EPC Open Data Communities API key |
| `MET_OFFICE_KEY` | ❌ Optional | Met Office DataPoint API key |

API keys are **never stored server-side**. They live in your browser session only and are cleared when the tab is closed.

The application looks for secrets in `.streamlit/secrets.toml` first, then falls back to a `.env` file loaded via `python-dotenv`. Use `.env.example` as a template — never commit real secrets.

---

## Running the Application

```bash
# Primary entry point
streamlit run app/main.py

# Convenience wrapper at repository root
streamlit run streamlit_app.py
```

Then open http://localhost:8501 in your browser.

### Running Tests

```bash
pytest tests/ -v
```

The test suite covers the physics engine, compliance logic, EPC service, weather service, location service, AI advisor history, and visualisation cache. Tests use monkeypatching to simulate network responses so they run fully offline.

### Security Check (before sharing publicly)

```bash
python security_check.py
```

---

## Repository Structure

```
.
├── app/            UI layer (Streamlit pages, tabs, components, segments)
├── core/           Business logic (physics, AI agent, ESG orchestrator)
├── services/       External integrations (EPC, weather, location, reports)
├── config/         Physical constants and scenario definitions
├── assets/         SVG brand logos
├── tests/          Pytest test suite (24 test files)
├── docs/           Extended documentation and guides
├── governance/     Architecture freeze and governance records
├── .streamlit/     Streamlit theme and server configuration
├── .github/        CI/CD workflows (GitHub Actions)
├── streamlit_app.py   Entry-point wrapper
├── security_check.py  Pre-deployment security verification script
├── requirements.txt
├── .env.example
└── README.md
```

---

## Data Sources & Citations

| Source | Usage |
|--------|-------|
| BEIS GHG Conversion Factors 2023 | Carbon intensity: 0.20482 kgCO₂e/kWh |
| HESA Estates Management Statistics 2022-23 | UK HE electricity cost: £0.28/kWh |
| CIBSE Guide A Environmental Design | U-values, heating season 5,800 hrs/yr |
| PVGIS (EC Joint Research Centre) | Solar irradiance Reading: 950 kWh/m²/yr |
| Raissi, Perdikaris & Karniadakis (2019) | PINN thermal methodology |
| Open-Meteo API | Free live weather data |
| Met Office DataPoint | Optional UK weather data |
| EPC Open Data Communities | Energy Performance Certificate data (England & Wales) |

---

## Disclaimer

CrowAgent™ Platform is a **working research prototype**. All energy, carbon, and financial results are based on simplified steady-state physics models calibrated against published UK higher education sector averages. They do not reflect the specific characteristics of any real building or institution.

**Greenfield University is a fictional institution** created for demonstration purposes. Any resemblance to any real institution is coincidental.

Results **must not** be used as the sole basis for any capital investment, procurement, or planning decision. Commission a site-specific energy assessment by a suitably qualified energy surveyor before undertaking any retrofit programme.

---

## Intellectual Property & Legal

**Copyright © 2026 Aparajita Parihar. All rights reserved.**

CrowAgent™ Platform — including all source code, physics models, UI design, and brand assets — is the original work of Aparajita Parihar.

CrowAgent™ is a trademark of Aparajita Parihar.
Trademark application filed with the UK Intellectual Property Office (UK IPO), Class 42.
Registration pending.

CrowAgent™ Platform is an independent research and development project created by Aparajita Parihar.
It is not endorsed by, affiliated with, or sponsored by the University of Reading or any other institution.

This software is **not licensed for commercial use** without written permission of the author. Redistribution, modification, and non-commercial use for research and educational purposes are permitted provided this copyright notice and trademark statement are retained.

For licensing enquiries: crowagent.platform@gmail.com

---

## Contributing

Before submitting a pull request, run the security verification script and ensure all tests pass:

```bash
python security_check.py
pytest tests/ -v
```

See `SECURITY_GUIDE.md` for safe handling of API keys and configuration.

---

## Contact

- **Email:** crowagent.platform@gmail.com
- **GitHub:** [github.com/WonderApri/crowagent-platform](https://github.com/WonderApri/crowagent-platform)
- **Issues:** [github.com/WonderApri/crowagent-platform/issues](https://github.com/WonderApri/crowagent-platform/issues)

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

*v2.1.0 · 7 March 2026 · Working Prototype*
