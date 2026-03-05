# CrowAgent™ Platform

**Sustainability AI Decision Intelligence for University Estate Management**

> ⚠️ **Working Prototype — Results Are Indicative Only.**
> Not for use as the sole basis for capital investment decisions.

---

## Overview

CrowAgent™ Platform is a physics-informed campus thermal intelligence system that helps university estate managers and sustainability professionals make evidence-based, cost-effective decisions for achieving Net Zero targets.

The platform combines:
- **Physics-Informed Thermal Model** (PINN methodology — Raissi et al., 2019)
- **Agentic AI Advisor** powered by Google Gemini 1.5 Flash
- **Live Weather Integration** via Open-Meteo API and Met Office DataPoint
- **Structured Scenario Comparison** across retrofit interventions

---

## Features

- 📊 **Dashboard** — Energy, carbon, and financial KPIs for multiple building scenarios  
- 📈 **Financial Analysis** — Payback period, ROI, and cost-per-tonne CO₂ comparisons  
- 🤖 **AI Advisor** — Agentic LLM with physics tool‑use for expert recommendations  
- 🌤 **Live Weather** — Real-time temperature integration for accurate thermal calculations  
- 🏢 **Multi-Building Portfolio** — Compare interventions across your campus estate  
- 🎨 **Branding & Layout** — consistent CrowAgent™ logo in both header and footer, centrally aligned  
- 🏷 **Robust asset loading** — logo/icon files are looked up relative to the working directory so they still render when Streamlit copies the script (no more emoji fallback)  
- ✏️ **Customisation** — use the “➕ Add building” control under the Building section and the “➕ Add scenario” control under Scenarios; enter simple JSON objects (session‑only)

---

## Quick Start

### Prerequisites

- Python 3.11+
- A free [Gemini API key](https://aistudio.google.com) (for AI Advisor)
- Optionally, a free [Met Office DataPoint key](https://www.metoffice.gov.uk/services/data/datapoint)

### Installation

```bash
git clone https://github.com/WonderApri/crowagent-platform.git
cd crowagent-platform
```

1. (optional) create and activate a virtualenv:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. configure environment variables:

   ```bash
   cp .env.example .env
   # or create .streamlit/secrets.toml with the same values
   ```

   Edit the file with your own keys; never commit real secrets.

### Running the App

```bash
streamlit run app/main.py
# or, thanks to the helper wrapper included at the repository root:
# streamlit run streamlit_app.py
```

### Running Tests

```bash
pytest tests/ -v
```

The test suite now includes startup and validation checks that exercise
key parts of the application logic without launching a browser.  They use
monkeypatching to simulate network responses so you can run them offline.
---

## API Keys

API keys are **never stored server-side**. They live in your browser session only.

| Key                  | Required | Where to get                                                    |
|----------------------|----------|-----------------------------------------------------------------|
| Gemini API key       | ✅        | [aistudio.google.com](https://aistudio.google.com)              |
| Met Office DataPoint | ❌        | [metoffice.gov.uk/services/data/datapoint](https://www.metoffice.gov.uk/services/data/datapoint) |

### Additional environment variables

The application looks for secrets (GEMINI_KEY, MET_OFFICE_KEY) in
`.streamlit/secrets.toml` or, as a fallback, in `.env` loaded via
`python-dotenv`. Use `.env.example` as a template.

---


## Module Compatibility

To maintain backwards compatibility with older integrations, the repository now includes import shims for legacy paths such as `core.agents.*`, `orchestrator`, `financial_agent`, `location`, and `visualization_3d`. New development should prefer the canonical modules under `core/`, `app/`, and `services/`.

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

---

## Disclaimer

CrowAgent™ Platform is a **working research prototype**. All energy, carbon, and financial results are based on simplified steady-state physics models calibrated against published UK higher education sector averages. They do not reflect the specific characteristics of any real building or institution.

**Greenfield University is a fictional institution** created for demonstration purposes. Any resemblance to any real institution is coincidental.

Results **must not** be used as the sole basis for any capital investment, procurement, or planning decision. Commission a site-specific energy assessment by a suitably qualified energy surveyor before undertaking any retrofit programme.

---

## Intellectual Property & Legal

**Copyright © 2026 Aparajita Parihar. All rights reserved.**

CrowAgent™ Platform — including all source code, physics models, UI design, and brand assets — is the original work of Aparajita Parihar.

**CrowAgent™** is an unregistered trademark of Aparajita Parihar. A UK Intellectual Property Office (UK IPO) Class 42 trademark application is currently pending. Use of the CrowAgent name or logo without permission is prohibited.

This project is an **independent research project** and is **not affiliated with the University of Reading** or any other institution.

This software is **not licensed for commercial use** without written permission of the author. Redistribution, modification, and non-commercial use for research and educational purposes are permitted provided this copyright notice and trademark statement are retained.

For licensing enquiries: crowagent.platform@gmail.com

---

## Contact

- **Email:** crowagent.platform@gmail.com
- **GitHub:** [github.com/WonderApri/crowagent-platform](https://github.com/WonderApri/crowagent-platform)
- **Issues:** [github.com/WonderApri/crowagent-platform/issues](https://github.com/WonderApri/crowagent-platform/issues)

---

*v2.0.0 · 28 February 2026 · Working Prototype*

## Contributing

Before submitting a pull request, make sure the `security_check.py` script runs cleanly (it will fail if `.env` or `.streamlit/secrets.toml` is missing or contains placeholder values).  See the SECURITY_GUIDE.md for details on safe handling of API keys and configuration.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
