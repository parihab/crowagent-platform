"""Utility helpers used across the CrowAgent application.

Keeping non-Streamlit logic in a separate module makes it easier to test
without spinning up a full Streamlit runtime.
"""

from __future__ import annotations

from typing import Any

import requests


# ─────────────────────────────────────────────────────────────────────────────
# API KEY VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

def validate_gemini_key(key: str) -> tuple[bool, str, bool]:
    """Check formatting and optionally call the validation API.

    Returns a tuple ``(is_valid, html_message, warn_flag)`` where:

    * ``is_valid`` indicates whether the key should be considered usable.
    * ``html_message`` is an HTML snippet suitable for display in the UI.
    * ``warn_flag`` is True if the key was accepted but a warning was raised
      (e.g. network failure) so that callers may treat it as "valid for now"
      but not discard the possibility of re-checking later.

    Security guards applied before any network call:
    • Leading/trailing whitespace is stripped.
    • Keys containing newline or carriage-return characters are rejected
      (log-injection prevention).
    • Keys containing null bytes are rejected.
    """
    # ── Security guards ───────────────────────────────────────────────────────
    key = key.strip()
    if "\n" in key or "\r" in key:
        return False, "<div class='val-err'>❌ Key contains invalid line-break characters</div>", False
    if "\x00" in key:
        return False, "<div class='val-err'>❌ Key contains invalid null bytes</div>", False

    # ── Format check ──────────────────────────────────────────────────────────
    prefix = "AI" + "za"
    if not key.startswith(prefix):
        return False, "<div class='val-err'>❌ Invalid key format</div>", False

    # ── Live validation ───────────────────────────────────────────────────────
    warn = False
    try:
        test_url = (
            "https://generativelanguage.googleapis.com/v1/models/"
            "gemini-1.5-pro:generateContent"
        )
        payload = {
            "contents": [{"parts": [{"text": "test"}]}],
            "generationConfig": {"maxOutputTokens": 10},
        }
        resp = requests.post(test_url, params={"key": key}, json=payload, timeout=10)
        if resp.status_code == 200:
            return True, "<div class='val-ok'>✓ Gemini AI Advisor ready</div>", False
        elif resp.status_code == 401:
            return False, "<div class='val-err'>❌ Invalid API key</div>", False
        elif resp.status_code == 403:
            return False, "<div class='val-err'>❌ API key blocked (check permissions in Google Cloud)</div>", False
        else:
            return True, "<div class='val-ok'>✓ Key format valid (will test on first use)</div>", False
    except requests.exceptions.Timeout:
        return True, "<div class='val-warn'>⚠ Validation timed out — key saved, will test on first use</div>", True
    except requests.exceptions.ConnectionError:
        return True, "<div class='val-warn'>⚠ No internet connection — key saved, will test on first use</div>", True
    except Exception:
        return True, "<div class='val-warn'>⚠ Validation error — key saved, will test on first use</div>", True


# ─────────────────────────────────────────────────────────────────────────────
# NUMERIC SAFETY HELPERS
# Sourced from: app/main.py — copied here to enable reuse across tab modules.
# Original copies remain in main.py until Batch 5 removes them.
# ─────────────────────────────────────────────────────────────────────────────

def _safe_number(value: Any, default: float = 0.0) -> float:
    """Coerce a potentially-missing or malformed value to float.

    Returns ``default`` for ``None``, non-numeric strings, and any value that
    cannot be converted by ``float()``.  Never raises.
    """
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_nested_number(container: dict, *keys: str, default: float = 0.0) -> float:
    """Safely traverse a nested dict and return the leaf value as a float.

    Returns ``default`` if any key is absent or if the leaf cannot be
    coerced to float.  Never raises.

    Example::

        _safe_nested_number(result, "thermal", "annual_energy_mwh", default=0.0)
    """
    current: Any = container
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current.get(key)
    return _safe_number(current, default=default)


# ─────────────────────────────────────────────────────────────────────────────
# POSTCODE EXTRACTION
# Sourced from: app/main.py — copied here to centralise address sanitisation.
# Original copy remains in main.py until Batch 5 removes it.
# ─────────────────────────────────────────────────────────────────────────────

def _extract_uk_postcode(text: str) -> str:
    """Extract the most likely UK postcode token from free-form address text.

    Applies a lightweight heuristic suitable for extracting a postcode from
    EPC address strings or user-typed inputs.

    Returns the postcode string (uppercased, space-separated) or ``""`` if no
    candidate is found.

    Note: Always sanitise the result through the UK postcode regex in
    services/epc.py before passing to external APIs.
    """
    raw = " ".join((text or "").upper().split())
    if not raw:
        return ""
    parts = [p.strip(",") for p in raw.split()]
    # Try two-token candidates first (e.g. "RG1 2AB")
    for i in range(len(parts) - 1):
        cand = f"{parts[i]} {parts[i + 1]}"
        if 5 <= len(cand) <= 8 and any(ch.isdigit() for ch in cand):
            return cand
    # Fall back to single-token candidates (e.g. compact form without space)
    for token in parts:
        if 5 <= len(token) <= 8 and any(ch.isdigit() for ch in token):
            return token
    return ""
