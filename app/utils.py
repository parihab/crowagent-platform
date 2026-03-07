"""
Utility functions for the Streamlit application.
"""
import re
import streamlit as st
import time
from typing import Any
import requests

# Gemini API Key Validation
# Matches the format "AIza" followed by 35 alphanumeric/hyphen/underscore characters.
# Modern keys are 39 chars total.
GEMINI_API_KEY_RE = re.compile(r"^AIza[A-Za-z0-9\-_]{35}$")
GEMINI_VALIDATION_URL = "https://generativelanguage.googleapis.com/v1/models"

def show_congratulations():
    """Displays a congratulations message and balloons."""
    st.success("Congratulations! You've successfully run the script.")
    time.sleep(1)
    st.balloons()

def _extract_uk_postcode(text: str) -> str:
    """
    Extracts the first valid UK postcode from a string.
    Returns the postcode in standard format (e.g., "SW1A 1AA") or empty string.
    """
    if not text:
        return ""
    # Regex for UK postcodes (simplified but robust for extraction)
    match = re.search(r'\b([A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2})\b', text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return ""

def _safe_number(value: Any, default: float = 0.0) -> float:
    """Safely converts a value to float, returning default on failure."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

def _safe_nested_number(container: dict, *keys: str, default: float = 0.0) -> float:
    """Safely retrieves a nested number from a dict."""
    current = container
    for k in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(k)
    return _safe_number(current, default)

def validate_gemini_key(key: str) -> tuple[bool, str, bool]:
    """
    Performs security, format, and live validation for a Gemini API key.

    Returns
    -------
    tuple[bool, str, bool]
        (is_valid, message, is_warning)
        is_warning=True means the key may be valid but could not be confirmed
        (e.g. network timeout or no internet connection).
    """
    if not isinstance(key, str):
        return False, "Invalid input: Key must be a string.", False

    key = key.strip()

    if not key:
        return False, "Invalid key format: API key is missing.", False

    if not key.startswith("AIza"):
        return False, "Invalid key format: Key must start with 'AIza'.", False

    # Live API check via POST to confirm the key works
    try:
        resp = requests.post(
            GEMINI_VALIDATION_URL,
            headers={"x-goog-api-key": key},
            json={},
            timeout=10,
        )
        if resp.status_code == 200:
            return True, "API key is ready and functional.", False
        if resp.status_code in (400, 401, 403):
            return False, "Invalid API key: The provided key is not authorized.", False
        return False, f"Invalid API key: validation returned status {resp.status_code}.", False

    except requests.exceptions.Timeout:
        return True, "API key validation timed out — key accepted provisionally.", True
    except requests.exceptions.ConnectionError:
        return True, "No internet connection — key accepted provisionally.", True
    except requests.exceptions.RequestException as exc:
        return True, f"Network error during validation: {exc}", True
