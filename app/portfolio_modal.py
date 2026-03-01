"""
Portfolio Management Modal Component
====================================
Renders the 'Manage Portfolio' dialog overlay.
Handles postcode search, asset addition, and portfolio management.
"""
import streamlit as st
from app.utils import _extract_uk_postcode
from services.epc import fetch_epc_data
from app.sidebar import init_portfolio_entry

@st.dialog("📂 Manage Portfolio")
def render_portfolio_modal():
    """
    Renders a modal dialog for managing the asset portfolio.
    Allows adding new buildings by postcode and removing existing ones.
    """
    st.caption("Add or remove assets from your active portfolio.")

    # --- Add Section ---
    with st.container(border=True):
        st.markdown("**Add New Asset**")
        c1, c2 = st.columns([3, 1])
        with c1:
            pc_input = st.text_input("UK Postcode", key="modal_pc", placeholder="SW1A 1AA", label_visibility="collapsed")
        with c2:
            search = st.button("Search", key="modal_search", use_container_width=True)
        
        if search and pc_input:
            try:
                clean_pc = _extract_uk_postcode(pc_input)
                if clean_pc:
                    with st.spinner("Fetching data..."):
                        # Use current segment
                        segment = st.session_state.get("user_segment", "university_he")
                        api_key = st.session_state.get("epc_api_key")
                        
                        # Fetch data
                        epc_data = fetch_epc_data(clean_pc, api_key=api_key)
                        
                        # Create entry
                        entry = init_portfolio_entry(epc_data, segment)
                        
                        if "portfolio" not in st.session_state:
                            st.session_state.portfolio = []
                        
                        # Check duplicates
                        if not any(p["id"] == entry["id"] for p in st.session_state.portfolio):
                            st.session_state.portfolio.append(entry)
                            st.success(f"Added {entry['display_name']}")
                            st.rerun()
                        else:
                            st.warning("Asset already in portfolio.")
                else:
                    st.warning("Invalid postcode format.")
            except Exception as e:
                st.error(f"Failed to add: {str(e)}")

    # --- List Section ---
    st.markdown("### Active Assets")
    portfolio = st.session_state.get("portfolio", [])
    segment = st.session_state.get("user_segment")
    
    # Filter by current segment
    seg_portfolio = [p for p in portfolio if p.get("segment") == segment]
    
    if not seg_portfolio:
        st.info("No assets found for this segment.")
    else:
        for p in seg_portfolio:
            c1, c2, c3 = st.columns([4, 2, 1])
            with c1:
                st.markdown(f"**{p.get('display_name', 'Unknown')}**")
                st.caption(p.get('postcode', ''))
            with c2:
                st.caption(f"{p.get('floor_area_m2', 0):.0f} m² • Band {p.get('epc_rating', '?')}")
            with c3:
                if st.button("🗑️", key=f"del_{p['id']}", help="Remove asset"):
                    st.session_state.portfolio = [x for x in portfolio if x['id'] != p['id']]
                    st.rerun()

    if st.button("Close", key="modal_close", use_container_width=True):
        st.session_state.show_portfolio_modal = False
        st.rerun()