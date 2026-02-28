"""
Utility functions for the Streamlit application.
"""
import re
import streamlit as st
import time

# Gemini API Key Validation
# Matches the format "AIza" followed by 35 alphanumeric/hyphen/underscore characters.
# Legacy keys might be 39 chars, but this is the modern standard.
GEMINI_API_KEY_RE = re.compile(r"^AIza[A-Za-z0-9\-_]{35}$")

def show_congratulations():
    """Displays a congratulations message and balloons."""
    st.success("Congratulations! You've successfully run the script.")
    time.sleep(1)
    st.balloons()

def validate_gemini_key(key: str) -> tuple[bool, str]:
    """
    Performs security and format validation for a Gemini API key.

    Hardening measures:
    1. Strips leading/trailing whitespace to prevent injection attacks.
    2. Explicitly forbids newline and null characters.
    3. Matches the key against a strict regex for the expected format.

    Returns
    -------
    tuple[bool, str]
        (is_valid, message)
    """
    if not isinstance(key, str):
        return False, "Invalid input: Key must be a string."

    key = key.strip()

    if not key:
        return False, "API key is missing."

    if "\n" in key or "\r" in key:
        return False, "Key contains invalid line break characters."

    if "\x00" in key:
        return False, "Key contains invalid null bytes."

    if not GEMINI_API_KEY_RE.match(key):
        return False, "Invalid format. A Gemini API key starts with 'AIza' and has 39 characters."

    # Placeholder for a live, lightweight check if one becomes available.
    # For now, format validation is the primary client-side check.
    # A real check would involve a simple, low-cost API call.
    # e.g., google.generativeai.get_model("gemini-pro") with the key.

    return True, "API key format is valid."
