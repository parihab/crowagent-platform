"""
🤖 AI Advisor Tab Renderer
==========================
Renders the enterprise-grade conversational interface for the AI Advisor.
Includes:
- Segment-specific starter questions
- Live tool execution status
- Markdown-rich chat bubbles
- Robust error handling
"""
from __future__ import annotations

import streamlit as st
import core.agent as agent
import app.branding as branding
from config.scenarios import SCENARIOS

# ─────────────────────────────────────────────────────────────────────────────
# SEGMENT-SPECIFIC STARTER QUESTIONS
# ─────────────────────────────────────────────────────────────────────────────
SEGMENT_STARTER_QUESTIONS = {
    "university_he": [
        "Which campus building yields the best ROI for a deep retrofit?",
        "How can we reduce Scope 1 & 2 emissions by 20% by 2030?",
        "Compare the payback period of solar PV across all buildings.",
        "What is the carbon impact of upgrading the Science Block glazing?"
    ],
    "smb_landlord": [
        "What is the cheapest way to bring my portfolio up to MEES Band C?",
        "Which property has the worst EPC rating and how do I fix it?",
        "Calculate the ROI of installing heat pumps in Unit 1.",
        "Does a fabric upgrade make financial sense for the Office Block?"
    ],
    "smb_industrial": [
        "How can I reduce Scope 1 emissions in my warehouse?",
        "What is the payback period for a solar roof installation?",
        "Compare LED lighting vs heating upgrades for carbon reduction.",
        "Estimate the energy savings of improving wall insulation."
    ],
    "individual_selfbuild": [
        "Does a heat pump meet the Future Homes Standard for my property?",
        "What is the most cost-effective way to improve my EPC band?",
        "How much will triple glazing save on my annual energy bill?",
        "Is a green roof a viable option for my detached house?"
    ]
}

def render(handler, weather: dict, portfolio: list[dict]) -> None:
    """
    Renders the AI Advisor tab content.

    Args:
        handler: The active SegmentHandler instance.
        weather: Current weather data dictionary.
        portfolio: Full list of portfolio assets.
    """
    # 1. Header & Disclaimer
    st.markdown("# 🤖 CrowAgent™ AI Advisor")
    st.markdown(
        "Physics-grounded agentic AI that runs real thermal "
        "simulations, compares scenarios and gives evidence-based "
        "Net Zero investment recommendations."
    )
    st.caption(
        "Powered by Google Gemini · Physics-informed reasoning "
        "· © 2026 Aparajita Parihar"
    )
    st.warning(
        "⚠️ AI Accuracy Disclaimer. The AI Advisor generates responses "
        "based on physics tool outputs and large language model reasoning. "
        "Like all AI systems, it can make mistakes, misinterpret questions, "
        "or produce plausible-sounding but incorrect conclusions. All "
        "AI-generated recommendations must be independently verified by a "
        "qualified professional before any action is taken. This AI Advisor "
        "is not a substitute for professional engineering or financial "
        "advice. Results are indicative only.",
        icon=None,
    )

    # 2. Check API Key
    api_key = st.session_state.get("gemini_key", "").strip()

    if not api_key:
        # --- LOCKED STATE ---
        with st.container(border=True):
            st.markdown("### 🔑 Activate AI Advisor with a free Gemini API key")
            st.markdown("""
            1. Visit [aistudio.google.com](https://aistudio.google.com)
            2. Sign in with any Google account
            3. Click **Get API key** → **Create API key**
            4. Paste it into **API Keys** in the sidebar
            """)
            st.caption("Free tier · 1,500 requests/day · No credit card required")
            st.caption("CrowAgent™ Platform")
        return

    # 3. Initialize Chat History
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "agent_history" not in st.session_state:
        st.session_state.agent_history = []
    
    # 4. Render Chat History
    for msg in st.session_state.chat_history:
        role = msg["role"]
        content = msg["content"]
        
        with st.chat_message(role):
            css_class = "ca-user" if role == "user" else "ca-ai"
            st.markdown(
                f'<div class="{css_class}" style="border:none; background:transparent; padding:0;">{content}</div>', 
                unsafe_allow_html=True
            )

    # 5. Starter Questions (Only if history is empty)
    if not st.session_state.chat_history:
        st.markdown("---")
        st.markdown("**Suggested Questions:**")
        
        questions = SEGMENT_STARTER_QUESTIONS.get(
            handler.segment_id, 
            SEGMENT_STARTER_QUESTIONS["university_he"]
        )
        
        cols = st.columns(2)
        for i, q in enumerate(questions):
            if cols[i % 2].button(q, key=f"starter_{i}", use_container_width=True):
                _handle_user_input(q, handler, portfolio, api_key)
                st.rerun()

    # 6. Chat Input
    if prompt := st.chat_input("Ask about your portfolio, scenarios, or regulations..."):
        _handle_user_input(prompt, handler, portfolio, api_key)
        st.rerun()


def _handle_user_input(user_text: str, handler, portfolio: list[dict], api_key: str) -> None:
    """Process user input, run the agent loop, and update UI."""
    st.session_state.chat_history.append({"role": "user", "content": user_text})
    
    # Filter portfolio for this segment
    segment_portfolio = [p for p in portfolio if p.get("segment") == handler.segment_id]
    building_registry = {b["name"]: b for b in segment_portfolio}
    
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        status_container = st.status("🧠 AI Advisor is thinking...", expanded=True)
        
        try:
            stream = agent.run_agent_turn(
                user_message=user_text,
                history=st.session_state.agent_history,
                gemini_key=api_key,
                building_registry=building_registry,
                scenario_registry=SCENARIOS,
                tariff=st.session_state.get("energy_tariff_gbp_per_kwh", 0.28),
                segment=handler.segment_id
            )
            
            final_response = None
            for event in stream:
                if event["type"] == "status":
                    status_container.update(label=event["msg"], state="running")
                elif event["type"] == "tool_start":
                    status_container.write(f"🛠️ **Executing Tool:** `{event['name']}`")
                elif event["type"] == "tool_end":
                    status_container.write(f"✅ **Tool Complete:** `{event['name']}`")
                elif event["type"] == "final":
                    final_response = event["response"]
                    status_container.update(label="Analysis Complete", state="complete", expanded=False)
            
            if final_response:
                st.session_state.agent_history = final_response["updated_history"]
                if final_response.get("error"):
                    error_msg = f"**Error:** {final_response['error']}"
                    st.error(error_msg)
                    st.session_state.chat_history.append({"role": "assistant", "content": error_msg})
                else:
                    answer = final_response["answer"]
                    response_placeholder.markdown(
                        f'<div class="ca-ai" style="border:none; background:transparent; padding:0;">{answer}</div>', 
                        unsafe_allow_html=True
                    )
                    st.session_state.chat_history.append({"role": "assistant", "content": answer})
            
        except Exception as e:
            status_container.update(label="System Error", state="error")
            st.error(f"An unexpected error occurred: {str(e)}")