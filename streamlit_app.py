# entry point for Streamlit Cloud and simple local runs

# import the main module from the app package which executes the
# Streamlit script when imported.  This wrapper makes it easier for the
# cloud to discover the correct app file without manual settings.

from app import main  # noqa: F401
