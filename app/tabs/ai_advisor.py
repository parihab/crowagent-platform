# ═══════════════════════════════════════════════════════════════════════════════
# CrowAgent™ Platform — AI Advisor Tab
# © 2026 Aparajita Parihar. All rights reserved.
#
# Independent research project. Not affiliated with any institution.
# Not licensed for commercial use without written permission of the author.
# Trademark rights reserved pending UK IPO registration — Class 42.
# ═══════════════════════════════════════════════════════════════════════════════

import streamlit as st
import logging

try:
    import concurrent.futures
    import json
    from app.branding import COLOURS, FONTS
    from app.utils import validate_gemini_key
except ImportError:
    COLOURS: dict = {}
    FONTS: dict = {}
    def validate_gemini_key(key: str) -> tuple[bool, str]:
        return True, ""

from core.agent import run_agent_turn
from core.orchestrator import ESGOrchestrator

logger = logging.getLogger(__name__)

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

    # Segment reset guard: if user segment changed, clear advisor histories immediately.
    current_segment = st.session_state.get("user_segment", "university_he")
    last_segment = st.session_state.get(
        "last_advisor_segment",
        st.session_state.get("last_segment", current_segment),
    )
    if last_segment != current_segment:
        st.session_state["ai_chat_history"] = []
        st.session_state["agent_history"] = []
        st.session_state["chat_history"] = []
        st.session_state.setdefault("ai_chat_history_by_segment", {})[current_segment] = []
    st.session_state["last_advisor_segment"] = current_segment
    st.session_state["last_segment"] = current_segment

    # Legacy/session compatibility keys must exist even in locked mode
    if "ai_chat_history" not in st.session_state:
        st.session_state["ai_chat_history"] = st.session_state.get("chat_history", [])
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = st.session_state.get("ai_chat_history", [])
    if "ai_chat_history_by_segment" not in st.session_state:
        st.session_state["ai_chat_history_by_segment"] = {}

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

    # ── BLOCK 3: PRIMARY GATE ─────────────────────────────────────────────────
    # The AI advisor is locked until a valid Gemini API key is activated in settings.
    # Check both the activation flag and raw key presence to prevent lockout
    _key = st.session_state.get("gemini_key", "")
    _looks_valid = isinstance(_key, str) and _key.strip().startswith("AIza")

    if not st.session_state.get("GEMINI_API_KEY_ACTIVATED", False) and not _looks_valid:
        # ── BLOCK 4: LOCKED STATE ─────────────────────────────────────────────
        with st.container(border=True):
            st.markdown("### 🔑 Activate AI Advisor with a free Gemini API key")
            st.markdown("""
1. Visit [aistudio.google.com](https://aistudio.google.com) and sign in.
2. Click **Get API key** → **Create API key in new project**.
3. Copy the generated key.
4. Paste it into the **API Keys** section in the **Settings** tab.
""")
            st.caption("Free tier · 1,500 requests/day · No credit card required.")
            st.image("assets/CrowAgent_Logo_Horizontal_Dark.svg", width=200)
        return

    # ── BLOCK 5: ACTIVE CHAT STATE ────────────────────────────────────────────

    # 5a. Get required data from session state & handle segment resets
    current_segment = st.session_state.get("user_segment", "university_he")
    last_segment = st.session_state.get(
        "ai_advisor_last_segment",
        st.session_state.get("last_segment"),
    )

    # If the segment changed since they last opened this tab, clear the chat memory
    if last_segment is not None and current_segment != last_segment:
        st.session_state["ai_chat_history"] = []
        st.session_state["chat_history"] = []

    st.session_state["ai_advisor_last_segment"] = current_segment
    st.session_state["last_segment"] = current_segment

    st.session_state.setdefault("ai_chat_history", [])
    st.session_state.setdefault("chat_history", st.session_state["ai_chat_history"])
    st.session_state.setdefault("ai_chat_history_by_segment", {})

    api_key = st.session_state.get("gemini_key", "")
    segment = current_segment
    segment_name = st.session_state.get("current_segment_name", "University / Higher Education")
    portfolio = st.session_state.get("portfolio", [])

    # Keep legacy and current keys synchronized
    st.session_state["chat_history"] = st.session_state["ai_chat_history"]
    st.session_state["ai_chat_history_by_segment"][segment] = st.session_state["chat_history"]

    # 5b. Define the two-column layout
    left_col, right_col = st.columns([1, 2.5], gap="large")

    # 5c. LEFT COLUMN: Context and starter prompts
    with left_col:
        st.markdown(f"**Segment:**\n`{segment_name}`")
        st.markdown(f"**Active Assets:**\n`{len(portfolio)}`")
        st.markdown("---")
        st.markdown("**Suggested Queries:**")
        prompts = STARTER_PROMPTS.get(segment, STARTER_PROMPTS["university_he"])
        for prompt in prompts:
            if st.button(
                prompt,
                key=f"starter_{prompt[:30]}",
                use_container_width=True,
            ):
                # Add starter to history and rerun to trigger agent
                st.session_state["chat_history"].append({"role": "user", "content": prompt})
                st.session_state["ai_chat_history"] = st.session_state["chat_history"]
                st.session_state["ai_chat_history_by_segment"][segment] = st.session_state["chat_history"]
                st.rerun()
        st.info("The AI is aware of your loaded assets and current business segment.", icon="ℹ️")

    # 5d. RIGHT COLUMN: Chat interface sub-frame
    with right_col:
        # This container creates a scrollable, bordered frame for the chat history
        with st.container(height=500, border=True):
            # Render the chat history from session state
            for msg in st.session_state["chat_history"]:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

            # If the last message is from the user, run the agent
            history = st.session_state["chat_history"]
            if history and history[-1]["role"] == "user":
                with st.chat_message("assistant"):
                    # The spinner appears inside the container while the agent runs
                    with st.spinner("Analyzing portfolio..."):
                        try:
                            # 1. Safety Check: API Key
                            if not api_key:
                                st.warning("⚠️ AI Advisor is in offline mode. Please configure your Gemini API Key to receive portfolio insights.")
                                st.stop()

                            # 2. Safety Check: Portfolio
                            if not portfolio:
                                st.error("Portfolio is empty. Please add assets to run analysis.")
                                st.stop()

                            # 3. Orchestrator Call
                            # We wrap the orchestrator and agent call in a thread pool as requested
                            def _process_advisor_request():
                                # a) Run Orchestrator
                                orch = ESGOrchestrator()
                                # Wrap list in dict as expected by orchestrator
                                orch_input = {"assets": portfolio}
                                analysis = orch.run(orch_input, segment)
                                
                                # b) Build deterministic prompt with analysis
                                analysis_str = json.dumps(analysis, default=str)
                                if len(analysis_str) > 10000:
                                    analysis_str = analysis_str[:10000] + "...(truncated)"
                                
                                augmented_message = (
                                    f"{history[-1]['content']}\n\n"
                                    f"[SYSTEM INJECTED ANALYSIS]:\n{analysis_str}\n\n"
                                    "Please use the above analysis to answer the user's question."
                                )

                                # c) Call Gemini
                                return run_agent_turn(
                                    user_message=augmented_message,
                                    segment=segment,
                                    portfolio=portfolio,
                                    api_key=api_key,
                                )

                            with concurrent.futures.ThreadPoolExecutor() as executor:
                                future = executor.submit(_process_advisor_request)
                                response = future.result()

                        except RuntimeError as e:
                            response = f"An error occurred while running the agent. \n\n**Error details:**\n`{e}`"
                        except Exception as e:
                            response = f"An unexpected error occurred. \n\n**Error details:**\n`{e}`"

                    # Display the agent's response
                    st.markdown(response)
                    # Add the response to history and rerun to clear the spinner
                    st.session_state["chat_history"].append({"role": "assistant", "content": response})
                    st.session_state["ai_chat_history"] = st.session_state["chat_history"]
                    st.session_state["ai_chat_history_by_segment"][segment] = st.session_state["chat_history"]
                    st.rerun()

        # The chat input is in the right column, but *outside* the scrollable container
        if user_input := st.chat_input("Ask about your portfolio, energy, or compliance..."):
            st.session_state["chat_history"].append({"role": "user", "content": user_input})
            st.session_state["ai_chat_history"] = st.session_state["chat_history"]
            st.session_state["ai_chat_history_by_segment"][segment] = st.session_state["chat_history"]
            st.rerun()
