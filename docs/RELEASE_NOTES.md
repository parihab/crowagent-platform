# 📦 Release Notes — CrowAgent™ Platform

## v2.0.0 — Architecture Refactor (Baseline Release)
**Date:** February 28, 2026
**Status:** Stable / Working Prototype

This release establishes the **CrowAgent™ Platform v2.0.0** as the stable baseline. It incorporates a complete architectural rewrite to support modularity, security, and multi-segment isolation.

### 🏛️ Architecture
- **Monolith Decomposition:** `app/main.py` reduced from ~3,000 lines to a thin orchestrator.
- **Package Structure:**
  - `app/segments/`: Isolated logic for University, Landlord, Industrial, and Self-Build.
  - `app/tabs/`: Dedicated renderers for Dashboard, Financial, and Compliance Hub.
  - `core/`: Pure Python physics engine and agent logic (Streamlit-free).
  - `config/`: Centralized constants and scenario registries.

### 🔒 Security & Governance
- **Session-Scoped Secrets:** API keys are never persisted to `os.environ` or disk.
- **Audit Hardening:** PII redaction (postcodes) and API key guards in logs.
- **Architecture Freeze:** Enforced stack constraints (Python, Streamlit, Plotly, Open-Meteo).

### ⚡ Performance
- **Caching Strategy:** LRU cache for thermal physics; resource caching for static assets.
- **Lazy Loading:** Segment handlers load on-demand to reduce cold start time.

### 📝 Restoration Instructions
To restore this specific release state in the future:

```bash
# 1. Checkout the tag
git checkout v2.0.0

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the application
streamlit run streamlit_app.py
```