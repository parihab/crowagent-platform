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
        "Analyze my portfolio's compliance gap for SECR reporting.",
        "Which renewable energy scenario offers the fastest payback?",
        "Draft a decarbonisation strategy for the Science Block."
    ],
    "smb_landlord": [
        "What is the cheapest way to bring my portfolio up to MEES Band C?",
        "Which property has the worst EPC rating and how do I fix it?",
        "Calculate the ROI of installing heat pumps in Unit 1.",
        "Compare insulation upgrades across all properties."
    ],
    "smb_industrial": [
        "How can I reduce Scope 1 emissions in my warehouse?",
        "What is the payback period for a solar roof installation?",
        "Analyze my portfolio's compliance gap for SECR reporting.",
        "Estimate the energy savings of improving wall insulation in Unit 4."
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
    # 1. Page Header
    st.markdown(
        """
        # 🤖 CrowAgent™ AI Advisor
        *Physics-grounded agentic AI that runs real thermal simulations, compares scenarios and gives evidence-based Net Zero investment recommendations.*
        *(Powered by Google Gemini · Physics-informed reasoning · © 2026 Aparajita Parihar)*
        """,
        unsafe_allow_html=False
    )

    # 2. Disclaimer Block
    st.warning(
        "**⚠️ AI Accuracy Disclaimer.** The AI Advisor generates responses based on physics tool outputs and large language model reasoning. Like all AI systems, it can make mistakes, misinterpret questions, or produce plausible-sounding but incorrect conclusions. All AI-generated recommendations must be independently verified by a qualified professional before any action is taken. This AI Advisor is not a substitute for professional engineering or financial advice. Results are indicative only."
    )

    # 3. API Key Gate
    # Show ONLY if st.session_state.gemini_key is empty
    if not st.session_state.get("gemini_key"):
        st.markdown(
            """
            ### 🔑 Activate AI Advisor with a free Gemini API key
            1. Visit aistudio.google.com
            2. Sign in with any Google account
            3. Click Get API key → Create API key
            4. Paste it into API Keys in the sidebar

            *Free tier · 1,500 requests/day · No credit card required*
            *CrowAgent™ Platform*
            """
        )
        return

    # 4. Main Chat Interface (Only if API Key is provided)
    
    # Initialize Chat History
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "agent_history" not in st.session_state:
        st.session_state.agent_history = []
    
    # Dynamic Segment Welcome text
    st.markdown(
        "\"Welcome to your AI Advisor. I am connected to your active property portfolio and ready to run thermal load simulations, analyze ROI, and check regulatory compliance.\""
    )

    # Render Chat History
    for msg in st.session_state.chat_history:
        role = msg["role"]
        content = msg["content"]
        
        with st.chat_message(role):
            css_class = "ca-user" if role == "user" else "ca-ai"
            st.markdown(
                f'<div class="{css_class}" style="border:none; background:transparent; padding:0;">{content}</div>', 
                unsafe_allow_html=True
            )

    # Suggested Prompts Section - Show ONLY if chat history is empty
    if not st.session_state.chat_history:
        st.markdown("---")
        st.markdown("**Suggested Queries for your Portfolio:**")
        
        questions = SEGMENT_STARTER_QUESTIONS.get(
            handler.segment_id, 
            SEGMENT_STARTER_QUESTIONS["university_he"]
        )
        
        cols = st.columns(2)
        for i, q in enumerate(questions):
            if cols[i % 2].button(q, key=f"starter_{i}", use_container_width=True):
                _handle_user_input(q, handler, portfolio)
                st.rerun()

    # Chat Input Box
    if prompt := st.chat_input("Ask about your portfolio, expenses, or compliance..."):
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