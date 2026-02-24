# CrowAgent™ Platform — Enterprise Weather & Scalability Feasibility Analysis

**Date:** 23 February 2026
**Branch:** `claude/feasibility-analysis-weather-enterprise-6iYah`
**Status:** Research Complete — Recommendations Ready

---

## 1. Executive Summary

CrowAgent™ is a well-architected Streamlit-based campus thermal intelligence prototype with a physics-informed model (PINN), agentic AI advisor (Gemini 1.5 Flash), and dual weather integration (Open-Meteo + Met Office). This analysis evaluates the feasibility of scaling the platform to enterprise-grade weather capabilities, multi-tenant deployment, and commercial readiness.

**Verdict: Feasible with moderate effort.** The current architecture is clean, modular, and well-separated — making enterprise upgrades an extension rather than a rewrite.

---

## 2. Current Architecture Assessment

### 2.1 Strengths

| Component | Current State | Enterprise Readiness |
|-----------|--------------|---------------------|
| **Physics Engine** (`core/physics.py`) | Steady-state PINN model, 3 buildings, 5 scenarios, CIBSE/BEIS-calibrated | High — modular `calculate_thermal_load()` accepts any building/scenario dict |
| **Weather Service** (`services/weather.py`) | Dual-source: Open-Meteo (free, 10k/day) + Met Office DataPoint (free, registered) | Medium — good fallback chain, 1-hour cache, but single-location only |
| **AI Agent** (`core/agent.py`) | Gemini 1.5 Flash with 5 tool declarations, agentic loop (max 10 iterations) | Medium — well-structured tool-use pattern, but tightly coupled to 3 buildings |
| **Frontend** (`app/main.py`) | Streamlit with Plotly charts, sidebar API key management | Low — Streamlit is excellent for prototypes but limits enterprise UX |
| **Security** | API keys browser-session only, never stored server-side | Good baseline — no secrets in code |

### 2.2 Identified Limitations

1. **Single location** — hardcoded to Reading, Berkshire (lat/lon constants in `weather.py`)
2. **No database** — all building data is in-memory Python dicts
3. **No authentication/IAM** — no user accounts or role-based access
4. **No multi-tenancy** — one campus (Greenfield University) with 3 fictional buildings
5. **Streamlit scaling** — single-process model, limited to ~100 concurrent users

---

## 3. Enterprise Weather Integration Feasibility

### 3.1 Current Weather Stack

```
Priority 1: Met Office DataPoint (if key provided) → UK authoritative
Priority 2: Open-Meteo (free, no key)              → always available
Priority 3: Manual override (user slider)           → offline fallback
```

### 3.2 Recommended Enterprise Weather Upgrades

| Upgrade | Effort | Cost | Impact |
|---------|--------|------|--------|
| **Multi-location support** — parameterise lat/lon per building | Low | Free | High — enables any UK campus |
| **Open-Meteo Historical API** — hourly data for backtesting models | Low | Free (10k req/day) | High — enables model validation |
| **Met Office DataHub** (replaces DataPoint) — higher-res UK weather | Medium | Free tier available | Medium — better spatial resolution |
| **Weather forecast integration** — 7-day ahead for predictive scheduling | Medium | Free (Open-Meteo) | High — enables proactive heating control |
| **Visual Crossing Weather API** — global coverage, historical + forecast | Medium | Free tier: 1000 req/day | Medium — enables international campuses |
| **Degree-day calculation module** — industry-standard HDD/CDD from weather | Low | Free | High — aligns with CIBSE TM41 methodology |

### 3.3 Recommended Implementation Priority

**Phase 1 (Quick wins — 1-2 weeks):**
- Parameterise location in `weather.py` (remove hardcoded `READING_LAT`/`READING_LON`)
- Add building-level lat/lon to `BUILDINGS` dict in `physics.py`
- Add Open-Meteo Historical endpoint for model backtesting

**Phase 2 (Medium effort — 2-4 weeks):**
- 7-day forecast integration for predictive energy management
- Degree-day (HDD/CDD) calculation module
- Migrate from Met Office DataPoint to Met Office DataHub API

**Phase 3 (Enterprise — 4-8 weeks):**
- Multi-campus weather aggregation service
- Weather data caching with Redis/PostgreSQL (replace `st.cache_data`)
- Alerting service for extreme weather events affecting building performance

---

## 4. Multi-Tenant & IAM Feasibility

### 4.1 Free/Low-Cost IAM Options

| Solution | Cost | Suitability |
|----------|------|-------------|
| **Firebase Authentication** (Google) | Free up to 50k MAU | Best fit — integrates with existing Gemini API usage |
| **Supabase Auth** | Free up to 50k MAU | Good — includes PostgreSQL for building data |
| **Auth0 Free Tier** | Free up to 7.5k MAU | Good — enterprise-grade, but lower free limit |
| **Clerk** | Free up to 10k MAU | Good — modern developer experience |

**Recommendation:** Supabase — provides auth + PostgreSQL database in one free tier, solving both IAM and data persistence.

### 4.2 Multi-Tenancy Architecture

```
Current:   Streamlit → in-memory dicts → single campus
Proposed:  Streamlit/FastAPI → Supabase PostgreSQL → multi-campus
           └── Auth (Supabase) → tenant isolation by university_id
```

---

## 5. Mapping & Spatial Visualisation Feasibility

### 5.1 Free Mapping Libraries

| Library | Cost | Use Case |
|---------|------|----------|
| **Folium** (Leaflet.js wrapper) | Free, OSS | Campus maps with building overlays — excellent Streamlit integration |
| **Pydeck** (deck.gl wrapper) | Free, OSS | 3D building visualisation, heatmaps — built into Streamlit |
| **Streamlit-Folium** | Free, OSS | Direct Streamlit component for interactive maps |
| **OpenStreetMap tiles** | Free | Base map tiles — no API key needed |

**Recommendation:** `streamlit-folium` with OpenStreetMap tiles — zero cost, excellent Streamlit integration, supports building polygon overlays with colour-coded energy performance.

---

## 6. AI Advisor Enterprise Upgrades

### 6.1 Current Agent Capabilities

- 5 physics tools (run_scenario, compare_all_buildings, find_best_for_budget, get_building_info, rank_all_scenarios)
- Agentic loop with max 10 iterations
- Temperature 0.2 (low creativity, high factual consistency)
- Gemini 1.5 Flash — free tier: 15 req/min, 1,500 req/day

### 6.2 Recommended Upgrades

| Upgrade | Effort | Impact |
|---------|--------|--------|
| Add `get_weather_forecast` tool — agent can check upcoming weather | Low | High |
| Add `compare_campuses` tool — cross-university benchmarking | Medium | High |
| Add conversation memory (Supabase) — persistent advisory sessions | Medium | High |
| Upgrade to Gemini 2.0 Flash — better reasoning, same free tier | Low | Medium |
| Add PDF report generation tool — agent produces downloadable reports | Medium | High |

---

## 7. Deployment & Scalability

### 7.1 Current: Streamlit Cloud (Prototype)

- Free hosting on Streamlit Community Cloud
- Limited to ~100 concurrent users
- Single-process, in-memory state

### 7.2 Enterprise Deployment Options

| Platform | Cost | Scalability | Effort |
|----------|------|-------------|--------|
| **Streamlit on Railway/Render** | Free tier available | ~500 users | Low |
| **FastAPI + React** (full rewrite) | Hosting ~$5-20/mo | 10,000+ users | High |
| **Streamlit + FastAPI backend** (hybrid) | ~$5-10/mo | ~2,000 users | Medium |

**Recommendation:** Short-term, stay on Streamlit with backend extraction to FastAPI for API endpoints. Long-term, migrate frontend to React/Next.js for full enterprise UX.

---

## 8. Cost Summary (Enterprise MVP)

| Item | Monthly Cost |
|------|-------------|
| Weather APIs (Open-Meteo + Met Office) | **Free** |
| Authentication (Supabase free tier) | **Free** |
| Database (Supabase PostgreSQL free tier) | **Free** |
| Mapping (Folium + OpenStreetMap) | **Free** |
| AI Advisor (Gemini 1.5 Flash free tier) | **Free** |
| Hosting (Railway/Render free tier) | **Free** |
| **Total for Enterprise MVP** | **£0/month** |

*Note: Free tiers are sufficient for up to ~5 universities, ~500 users. Beyond that, estimated costs are £20-50/month.*

---

## 9. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Gemini API free tier rate limits hit | Medium | High | Implement request queuing; offer BYO-key model |
| Open-Meteo service disruption | Low | Medium | Already handled — Met Office fallback + manual override |
| Streamlit scalability ceiling | High | Medium | Extract backend to FastAPI early |
| GDPR compliance for multi-tenant | Medium | High | Supabase EU region; building data only (no personal data) |
| Met Office DataPoint API deprecation | Medium | Low | Already planned migration to DataHub |

---

## 10. Conclusion & Next Steps

The CrowAgent™ platform is **well-positioned for enterprise scaling**. The modular architecture means upgrades are additive, not destructive. The entire enterprise MVP can be built on **free-tier services** for the initial rollout.

### Recommended Roadmap

1. **Immediate** — Parameterise location, add forecast weather endpoint
2. **Short-term** — Add Supabase for auth + database, integrate Folium maps
3. **Medium-term** — Multi-campus support, PDF report generation, persistent AI conversations
4. **Long-term** — FastAPI backend extraction, React frontend, commercial licensing model

---

*Analysis prepared for CrowAgent™ Platform feasibility review.*
*CrowAgent™ is an unregistered trademark of Aparajita Parihar. © 2026 All rights reserved.*
