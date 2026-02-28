# ═══════════════════════════════════════════════════════════════════════════════
# CrowAgent™ Platform — In-Session Audit Log
# © 2026 Aparajita Parihar. All rights reserved.
#
# Logs configuration changes (API key updates, provider changes, location).
# Storage: st.session_state ONLY — never persisted to disk or any database.
# GDPR-safe: entries contain no PII; log is cleared on browser/session close.
#
# Governance requirement: key configuration changes must be traceable with
# timestamp and actor identity for regulated enterprise customers.
# ═══════════════════════════════════════════════════════════════════════════════

from __future__ import annotations
import re
from datetime import datetime, timezone

import streamlit as st

_LOG_KEY  = "_crowagent_audit_log"
_MAX_SIZE = 50   # cap entries to prevent unbounded memory growth

# Regex to find UK postcodes for redaction
UK_POSTCODE_RE = re.compile(r"\b([A-Z]{1,2}\d[A-Z\d]?)\s*(\d[A-Z]{2})\b", re.IGNORECASE)
# Regex to detect accidental API key leakage
API_KEY_PATTERN = re.compile(r'[A-Za-z0-9_\-]{30,}')


def _ensure_log() -> None:
    if _LOG_KEY not in st.session_state:
        st.session_state[_LOG_KEY] = []


def _redact_postcode(text: str) -> str:
    """Replace full postcodes with their outward code + '***'."""
    return UK_POSTCODE_RE.sub(r"\1 ***", str(text))


def _assert_no_key(value: str) -> None:
    """Raise ValueError if a string appears to contain an API key."""
    if API_KEY_PATTERN.search(value):
        raise ValueError("Audit log details must not contain API key material.")


def log_event(action: str, details: str) -> None:
    """
    Append an audit event to the in-session log.

    Parameters
    ----------
    action  : Short action label, e.g. "KEY_UPDATED", "PROVIDER_CHANGED"
    details : Human-readable description; must NOT contain raw API key material.
              Postcodes will be automatically redacted.
    """
    _ensure_log()
    _assert_no_key(action)
    _assert_no_key(details)

    entry: dict = {
        "ts":      datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "action":  action,
        "details": _redact_postcode(details),
    }
    st.session_state[_LOG_KEY].append(entry)
    if len(st.session_state[_LOG_KEY]) > _MAX_SIZE:
        st.session_state[_LOG_KEY] = st.session_state[_LOG_KEY][-_MAX_SIZE:]


def get_log(n: int = 10) -> list[dict]:
    """Return the last *n* audit log entries, most recent first."""
    _ensure_log()
    return list(reversed(st.session_state[_LOG_KEY][-n:]))


def clear_log() -> None:
    """Wipe the entire in-session log (e.g. on explicit admin action)."""
    st.session_state[_LOG_KEY] = []
