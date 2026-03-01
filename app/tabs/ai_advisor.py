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
    st.markdown(
        """
        <div style="margin-bottom: 20px;">
            <h2 style="margin-bottom: 5px;">🤖 AI Sustainability Consultant</h2>
            <div style="color: #5A7A90; font-size: 0.9rem;">
                Physics-informed decision support for your portfolio.
                <span style="background: rgba(240,180,41,0.15); color: #8A6D0B; padding: 2px 6px; border-radius: 4px; font-size: 0.8rem; font-weight: 600; margin-left: 8px;">
                    ⚠️ AI outputs are indicative only. Verify with a qualified surveyor.
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # 2. Check API Key
    if not st.session_state.get("gemini_key_valid"):
        st.info("🔑 Please enter a valid Google Gemini API key in the sidebar to activate the AI Advisor.")
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
                _handle_user_input(q, handler, portfolio)
                st.rerun()

    # 6. Chat Input
    if prompt := st.chat_input("Ask about your portfolio, scenarios, or regulations..."):
        _handle_user_input(prompt, handler, portfolio)
        st.rerun()


def _handle_user_input(user_text: str, handler, portfolio: list[dict]) -> None:
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
                gemini_key=st.session_state.gemini_key,
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