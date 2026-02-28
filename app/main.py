"""
Main application logic for the Streamlit app.

NOTE: This is a transitional stub maintained during the refactor.
      Full orchestration logic will be restored in Batch 5 (UI Redesign).
      Imports have been aligned with the restored Batch 1 module contracts.
"""
import streamlit as st
from .session import init_session
from .branding import PAGE_CONFIG, inject_branding
from .segments import get_segment_handler, SEGMENT_IDS, SEGMENT_LABELS
from app.segments.university_he import UniversityHEHandler as _UHE
from config.scenarios import SCENARIOS, SEGMENT_SCENARIOS, SEGMENT_DEFAULT_SCENARIOS

BUILDINGS = _UHE().building_registry


def run():
    """
    The main function that orchestrates the Streamlit application.
    """
    st.set_page_config(**PAGE_CONFIG)
    inject_branding()
    init_session()

    st.sidebar.title("Segment Selection")

    # Segment selection dropdown
    label_options = [""] + [SEGMENT_LABELS[sid] for sid in SEGMENT_IDS]
    selected_label = st.sidebar.selectbox(
        "Choose your customer segment:",
        options=label_options,
        index=0,
        key="segment_selector",
    )

    # Resolve label back to segment ID
    label_to_id = {v: k for k, v in SEGMENT_LABELS.items()}
    selected_id = label_to_id.get(selected_label)

    if selected_id:
        handler = get_segment_handler(selected_id)
        st.session_state["user_segment"] = selected_id
        st.info(
            f"**{handler.display_label}** — "
            f"{len(handler.building_registry)} buildings · "
            f"{len(handler.scenario_whitelist)} scenarios available"
        )
    else:
        st.session_state["user_segment"] = None
        st.title("Welcome to CrowAgent™")
        st.write("Please select a customer segment from the sidebar to begin.")
