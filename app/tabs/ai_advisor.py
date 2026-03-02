# ═══════════════════════════════════════════════════════════════════════════════
# CrowAgent™ Platform — AI Advisor Tab
# © 2026 Aparajita Parihar. All rights reserved.
#
# Independent research project. Not affiliated with any institution.
# Not licensed for commercial use without written permission of the author.
# Trademark rights reserved pending UK IPO registration — Class 42.
# ═══════════════════════════════════════════════════════════════════════════════

import streamlit as st

try:
    from app.branding import COLOURS, FONTS
except ImportError:
    COLOURS: dict = {}
    FONTS: dict = {}

from core.agent import run_agent_turn

# ─────────────────────────────────────────────────────────────────────────────
# STARTER PROMPTS — segment-specific suggested queries
# ─────────────────────────────────────────────────────────────────────────────
STARTER_PROMPTS = {
    "university_he": [
        "What is the cheapest intervention to bring my campus to MEES Band C?",
        "Analyse my portfolio's compliance gap for SECR reporting.",
        "Which renewable energy scenario offers the fastest payback?",
    ],
    "smb_landlord": [
        "Which properties are most at risk of failing MEES 2028 compliance?",
        "What retrofit investment delivers the best rental yield uplift?",
        "Summarise my portfolio EPC rating distribution and compliance timeline.",
    ],
    "smb_industrial": [
        "What is my estimated SECR Scope 1 and Scope 2 carbon footprint?",
        "Which energy efficiency measure has the shortest payback?",
        "Model a solar PV installation across my industrial estate.",
    ],
    "individual_selfbuild": [
        "What upgrades do I need to meet Part L 2021 for my self-build?",
        "Compare fabric-first vs renewables for my Net Zero pathway.",
        "What is the estimated ROI on ASHP versus gas boiler replacement?",
    ],
}


def render(handler, weather: dict, portfolio: list[dict]) -> None:
    """Renders the AI Advisor tab."""

    # ── BLOCK 1: PAGE HEADER ──────────────────────────────────────────────────
    st.markdown("## 🤖 CrowAgent™ AI Advisor")
    st.markdown(
        "Physics-grounded agentic AI that runs real thermal simulations, "
        "compares scenarios and gives evidence-based Net Zero investment "
        "recommendations."
    )
    st.caption(
        "Powered by Google Gemini · Physics-informed reasoning "
        "· © 2026 CrowAgent™"
    )

    # ── BLOCK 2: DISCLAIMER ───────────────────────────────────────────────────
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

    # ── BLOCK 3: BRANCHING GATE ───────────────────────────────────────────────
    api_key = st.session_state.get("gemini_key", "").strip()

    if not api_key:
        # ── BLOCK 4: LOCKED STATE ─────────────────────────────────────────────
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

    # ── BLOCK 5: ACTIVE CHAT STATE ────────────────────────────────────────────

    # 5a. SESSION INIT
    st.session_state.setdefault("ai_chat_history", [])
    segment = st.session_state.get("user_segment", "university_he")
    portfolio = st.session_state.get("portfolio", [])

    # 5b. WELCOME BANNER
    st.info(
        "Welcome to your AI Advisor. I am connected to your active "
        "property portfolio and ready to run thermal load simulations, "
        "analyze ROI, and check regulatory compliance."
    )

    # 5c. STARTER PROMPTS (only shown when chat history is empty)
    if len(st.session_state.ai_chat_history) == 0:
        prompts = STARTER_PROMPTS.get(segment, STARTER_PROMPTS["university_he"])
        st.markdown("**Suggested Queries for your Portfolio:**")
        for prompt in prompts:
            if st.button(
                prompt,
                key=f"starter_{prompt[:30]}",
                use_container_width=True,
            ):
                st.session_state.ai_chat_history.append(
                    {"role": "user", "content": prompt}
                )
                st.rerun()

    # 5d. CHAT HISTORY DISPLAY
    for msg in st.session_state.ai_chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 5e. PENDING RESPONSE HANDLER
    history = st.session_state.ai_chat_history
    if history and history[-1]["role"] == "user":
        with st.status("⚙️ Analysing your portfolio...", expanded=True) as status:
            try:
                response = run_agent_turn(
                    user_message=history[-1]["content"],
                    segment=segment,
                    portfolio=portfolio,
                    api_key=api_key,
                    status_widget=status,
                )
                status.update(
                    label="✅ Analysis complete",
                    state="complete",
                    expanded=False,
                )
                st.session_state.ai_chat_history.append(
                    {"role": "assistant", "content": response}
                )
                st.rerun()
            except Exception as e:
                err = str(e).lower()
                if "429" in err:
                    msg = (
                        "Gemini API rate limit reached. "
                        "Please wait 60 seconds and try again."
                    )
                elif "401" in err or "invalid" in err or "api key" in err:
                    msg = (
                        "Invalid API key detected. "
                        "Please verify your key in Settings."
                    )
                elif "timeout" in err:
                    msg = (
                        "Request timed out. "
                        "Please check your connection and retry."
                    )
                else:
                    msg = (
                        "AI Advisor encountered an unexpected error. "
                        "Please retry in a moment."
                    )
                status.update(
                    label="❌ Error occurred",
                    state="error",
                    expanded=False,
                )
                st.warning(msg)
                st.session_state.ai_chat_history.pop()
                # ↑ remove unanswered user message to prevent infinite retry loop

    # 5f. CHAT INPUT
    user_input = st.chat_input(
        "Ask about your portfolio, energy expenses, or compliance..."
    )
    if user_input:
        st.session_state.ai_chat_history.append(
            {"role": "user", "content": user_input}
        )
        st.rerun()
