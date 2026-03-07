# 📦 Release Notes — CrowAgent™ Platform

## v2.1.0 — Repository Cleanup & Maintenance Release
**Date:** 7 March 2026
**Status:** Stable / Working Prototype

This release contains no application logic changes. It focuses entirely on
repository hygiene to produce a clean, well-documented public codebase.

### 🗑️ Files Removed
- **Stale compatibility shims** (`app/orchestrator.py`, `app/tabs/{financial_agent,orchestrator,retrofit_agent,risk_agent}.py`, `core/agents/` package, root `__init__.py`) — nothing in the codebase imported these paths; canonical imports already point directly to `core/`.
- **Temporary developer scripts** (`verify_api_key.py`, `verify_gemini_key.py`, `test_api_key_activation.py`) — standalone CLI utilities used during development, not part of the application.
- **Dead application code** — `show_congratulations()` in `app/utils.py` was never called; removed along with its unused `import time`.
- **Internal development documentation** (`AGENTIC_CODE_ASSIST_PROMPT.md`, `AUDIT_REPORT.md`, `EXECUTION_SPECIFICATION.md`, `FEASIBILITY_ANALYSIS.md`, `FIX_SUMMARY.md`, `REPO_ANALYSIS.md`, `governance/ARCHITECTURE_FREEZE.md`) — developer-only artefacts not relevant to users or contributors.

### 📁 Repository Structure
- Remaining secondary docs consolidated into `docs/` subdirectory.
- Root retains only `README.md` and `SECURITY_GUIDE.md`.

### 📖 Documentation
- `README.md` fully rewritten with sections: Project Overview, Architecture,
  Setup Instructions, Environment Variables, Running the Application,
  Repository Structure.
- `docs/RELEASE_NOTES.md` updated with this entry.

### 🔢 Version Bumps
- Version string updated to `v2.1.0` in `core/about.py`, `app/tabs/settings.py`, and `README.md`.

---

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