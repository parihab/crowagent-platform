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
from datetime import datetime, timezone

import streamlit as st

_LOG_KEY  = "_crowagent_audit_log"
_MAX_SIZE = 50   # cap entries to prevent unbounded memory growth


def _ensure_log() -> None:
    if _LOG_KEY not in st.session_state:
        st.session_state[_LOG_KEY] = []


def log_event(action: str, details: str) -> None:
    """
    Append an audit event to the in-session log.

    Parameters
    ----------
    action  : Short action label, e.g. "KEY_UPDATED", "PROVIDER_CHANGED"
    details : Human-readable description; must NOT contain raw API key material.
    """
    _ensure_log()
    entry: dict = {
        "ts":      datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "action":  action,
        "details": details,
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
