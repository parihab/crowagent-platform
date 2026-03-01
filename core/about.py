import streamlit as st

def render():
    st.header("ℹ️ About & Contact")
    
    # Layout: Contact info on left (narrower), Main content on right (wider)
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("📬 Contact & Enquiries")
        st.markdown("""
        **Project Lead**
        Aparajita Parihar
        BSc Computer Science (Year 1)
        University of Reading
        
        **Email**
        [crowagent.platform@gmail.com](mailto:crowagent.platform@gmail.com)
        
        **GitHub**
        [github.com/WonderApri/crowagent-platform](https://github.com/WonderApri/crowagent-platform)
        
        **Trademark Status**
        CrowAgent™ is an unregistered trademark.
        UK IPO Class 42 application pending.
        
        **Enquiry Types Welcome**
        • Demo or pilot programme requests
        • Academic collaboration
        • Research partnerships
        • Technical questions
        • Press & media
        • Bug reports & feedback
        
        **RESPONSE TIME**
        We aim to respond to all enquiries within 2–3
        business days.
        """)
        
        st.markdown("---")
        
        st.subheader("🛠 Build Information")
        st.markdown("""
        **Version:** v2.0.0
        **Released:** 21 February 2026
        **Status:** 🚧 Working Prototype
        **Weather:** ● Live — Open-Meteo API
        **Cache TTL:** 60 min (weather)
        **Physics:** PINN (Raissi et al., 2019)
        """)

    with col2:
        st.subheader("About CrowAgent™ Platform")
        st.markdown("""
        CrowAgent™ Platform is a physics-informed campus thermal intelligence system designed to help
        university estate managers and sustainability professionals make evidence-based, cost-effective
        decisions for achieving Net Zero targets.

        The platform combines **Physics-Informed Neural Network (PINN)** methodology with an **agentic AI
        advisor**, live **Met Office weather integration**, and structured **scenario comparison** to evaluate retrofit
        interventions across a campus portfolio.
        """)
        
        st.warning("""
        **⚠️ FULL PLATFORM DISCLAIMER**
        
        **Working Prototype — Indicative Results Only**
        
        CrowAgent™ Platform is currently a working research prototype. All energy, carbon, and financial
        results produced by this platform are based on simplified steady-state physics models calibrated against
        published UK higher education sector averages (HESA 2022-23, CIBSE Guide A). They do not reflect the
        specific characteristics of any real building or institution.

        **Results must not be used as the sole basis for any capital investment, procurement, or planning
        decision.** Before undertaking any retrofit programme, organisations should commission a site-specific
        energy assessment by a suitably qualified energy surveyor or building services engineer in accordance
        with BS EN ISO 52000 and relevant CIBSE guidance.

        Greenfield University is a fictional institution created for demonstration purposes. Any resemblance to
        any real institution is coincidental.
        """)
        
        with st.expander("🤖 AI Advisor Disclaimer"):
            st.markdown("""
            The CrowAgent™ AI Advisor is powered by **Google Gemini 1.5 Pro**, a large language
            model (LLM). Like all LLM-based systems, the AI Advisor may:
            • Generate plausible-sounding but factually incorrect information ("hallucination")
            • Misinterpret ambiguous questions
            • Produce recommendations that do not account for site-specific factors
            • Provide outdated information beyond its training cutoff
            
            All AI-generated recommendations must be independently verified by a qualified
            professional before any action is taken. The AI Advisor is not a substitute for professional
            engineering, financial, or legal advice. Neither Aparajita Parihar nor CrowAgent™ Platform
            accepts liability for decisions made on the basis of AI Advisor outputs.
            """)
            
        with st.expander("📊 Data Sources & Assumptions"):
            st.markdown("""
            All figures are derived from publicly available UK sector data: 
            *   **BEIS Greenhouse Gas Conversion Factors 2023** (carbon intensity 0.20482 kgCO₂e/kWh)
            *   **HESA Estates Management Statistics 2022-23** (electricity cost £0.28/kWh)
            *   **CIBSE Guide A Environmental Design** (U-values, heating season 5,800 hrs/yr)
            *   **PVGIS EC Joint Research Centre** (Reading solar irradiance 950 kWh/m²/yr)
            *   **US DoE EnergyPlus** for cross-validation
            *   **Raissi, Perdikaris & Karniadakis (2019)** for PINN methodology. 
            
            Weather data from **Open-Meteo API** and optionally **Met Office DataPoint**.
            """)
            
        with st.expander("⚖️ Intellectual Property"):
            st.markdown("""
            **CrowAgent™ Platform**, including all source code, physics models, UI design, and brand assets, is the
            original work of **Aparajita Parihar** and is protected by copyright.

            **CrowAgent™** is an unregistered trademark of Aparajita Parihar. A UK IPO Class 42 trademark application
            is currently pending.

            This platform is an independent research project and is not affiliated with the University of Reading or
            any other institution.

            **© 2026 Aparajita Parihar. All rights reserved.** Not licensed for commercial use without written permission
            of the author.
            """)
            
        st.subheader("💻 Technology Stack")
        st.markdown("""
        `Python 3.11` `Streamlit` `Plotly` `Open-Meteo API` `Met Office DataPoint` `Google Gemini 1.5 Pro`
        `PINN Thermal Model` `Streamlit Community Cloud`
        """)
        
        st.subheader("☁️ Deployment (Zero Cost)")
        st.caption("""
        This platform is deployed entirely on free tiers:
        **GitHub Free** (public repo, unlimited) → **Streamlit Community Cloud** (1 free app, 1 GB memory,
        unlimited views) → **Open-Meteo** (10,000 req/day free, no key needed) → **Gemini 1.5 Pro** (1,500
        req/day free, user's own key).

        Smart weather caching (1-hour TTL) means only ~24 weather API calls per day regardless of visitor
        volume. Total monthly cost: **£0.00**.
        """)