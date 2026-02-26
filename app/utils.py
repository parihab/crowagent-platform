"""Utility helpers used across the CrowAgent application.

Keeping non-Streamlit logic in a separate module makes it easier to test
without spinning up a full Streamlit runtime.
"""

import requests


def validate_gemini_key(key: str) -> tuple[bool, str, bool]:
    """Check formatting and optionally call the validation API.

    Returns a tuple `(is_valid, html_message, warn_flag)` where:

    * ``is_valid`` indicates whether the key should be considered usable.
    * ``html_message`` is an HTML snippet suitable for display in the UI.
    * ``warn_flag`` is True if the key was accepted but a warning was raised
      (e.g. network failure) so that callers may treat it as "valid for now"
      but not discard the possibility of re-checking later.
    """
    prefix = "AI" + "za"
    if not key.startswith(prefix):
        return False, "<div class='val-err'>❌ Invalid key format</div>", False

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
