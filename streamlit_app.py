"""
# Crow Agent Platform

This is the main entry point for the Streamlit application.

This script initializes the multi-page Streamlit application and serves as the primary
launch point. It directs users to the main application page and other functional
modules, which are organized as separate pages.

"""

import streamlit as st

# Redirect to the main application page.
# This is a workaround to use a multi-page app structure where the main app
# is not in the root script.
st.switch_page("app/main.py")
