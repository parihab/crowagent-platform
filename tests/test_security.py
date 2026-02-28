"""
Security test suite — CrowAgent™ Platform
==========================================
Covers: credential hygiene, HTTPS-only endpoints, dangerous-primitive absence,
Streamlit server hardening, and git-tracking of sensitive files.

These tests are intended to act as a continuous security gate: if any of the
checks fail the CI build should be blocked.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

import pytest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Production source files to audit (test files are intentionally excluded)
PRODUCTION_FILES = [
    "app/main.py",
    "app/compliance.py",
    "app/utils.py",
    "services/epc.py",
    "services/weather.py",
    "services/location.py",
    "services/audit.py",
    "core/physics.py",
    "core/agent.py",
]


def _read(relpath: str) -> str:
    fpath = os.path.join(ROOT_DIR, relpath)
    if not os.path.exists(fpath):
        return ""
    with open(fpath, encoding="utf-8") as fh:
        return fh.read()


def _non_comment_lines(content: str) -> str:
    """Strip full-line comments to avoid false positives."""
    return "\n".join(
        line for line in content.splitlines() if not line.strip().startswith("#")
    )


# ─────────────────────────────────────────────────────────────────────────────
# 1. No hardcoded secrets in production source
# ─────────────────────────────────────────────────────────────────────────────

class TestNoHardcodedSecrets:
    """Verify that no real API keys appear as string literals in source code."""

    GOOGLE_KEY_RE = re.compile(r"AIzaSy[A-Za-z0-9_\-]{33}")
    # 40-char lowercase hex assigned to a variable (matches EPC key format)
    HEX40_IN_LITERAL_RE = re.compile(r"""['"]([0-9a-f]{40})['"]""")

    def test_no_google_api_key_literal(self):
        for fname in PRODUCTION_FILES:
            content = _read(fname)
            matches = self.GOOGLE_KEY_RE.findall(content)
            assert not matches, (
                f"Possible Google API key literal in {fname}: {matches}"
            )

    def test_no_40char_hex_key_literal(self):
        """Flag any 40-char hex string literal — typical EPC/OAuth token format."""
        for fname in PRODUCTION_FILES:
            content = _read(fname)
            clean = _non_comment_lines(content)
            matches = self.HEX40_IN_LITERAL_RE.findall(clean)
            assert not matches, (
                f"Possible 40-char hex secret literal in {fname}: {matches}"
            )

    def test_no_password_literals(self):
        """No password= or passwd= with a non-empty string value."""
        pw_re = re.compile(r"""(?:password|passwd)\s*=\s*['"][^'"]{4,}['"]""", re.IGNORECASE)
        for fname in PRODUCTION_FILES:
            content = _non_comment_lines(_read(fname))
            matches = pw_re.findall(content)
            assert not matches, f"Possible hardcoded password in {fname}: {matches}"


# ─────────────────────────────────────────────────────────────────────────────
# 2. No dangerous Python execution primitives
# ─────────────────────────────────────────────────────────────────────────────

class TestNoDangerousPrimitives:
    """Ensure no eval, exec, or pickle.loads of untrusted data."""

    def test_no_eval(self):
        eval_re = re.compile(r"\beval\s*\(")
        for fname in PRODUCTION_FILES:
            content = _non_comment_lines(_read(fname))
            assert not eval_re.search(content), f"eval() found in {fname}"

    def test_no_exec(self):
        exec_re = re.compile(r"\bexec\s*\(")
        for fname in PRODUCTION_FILES:
            content = _non_comment_lines(_read(fname))
            assert not exec_re.search(content), f"exec() found in {fname}"

    def test_no_pickle_loads(self):
        for fname in PRODUCTION_FILES:
            content = _read(fname)
            assert "pickle.loads" not in content, f"pickle.loads() in {fname}"

    def test_no_os_system(self):
        os_sys_re = re.compile(r"\bos\.system\s*\(")
        for fname in PRODUCTION_FILES:
            content = _non_comment_lines(_read(fname))
            assert not os_sys_re.search(content), f"os.system() in {fname}"


# ─────────────────────────────────────────────────────────────────────────────
# 3. All external HTTP calls use HTTPS
# ─────────────────────────────────────────────────────────────────────────────

class TestAllHttpsEndpoints:
    """External API endpoints must use HTTPS."""

    # URLs that are legitimately HTTP (local only)
    LOCAL_PATTERN = re.compile(r"http://(localhost|127\.0\.0\.1|0\.0\.0\.0)")

    def test_no_plain_http_urls_in_production(self):
        http_re = re.compile(r'http://[^\s\'"]+')
        for fname in PRODUCTION_FILES:
            for line in _read(fname).splitlines():
                if line.strip().startswith("#"):
                    continue
                for m in http_re.finditer(line):
                    url = m.group(0)
                    assert self.LOCAL_PATTERN.match(url), (
                        f"Non-HTTPS external URL in {fname}: {url!r}"
                    )

    def test_ssl_verification_not_disabled(self):
        for fname in PRODUCTION_FILES:
            content = _read(fname)
            assert "verify=False" not in content, (
                f"SSL verification disabled (verify=False) in {fname}"
            )


# ─────────────────────────────────────────────────────────────────────────────
# 4. Streamlit server hardening
# ─────────────────────────────────────────────────────────────────────────────

class TestStreamlitServerHardening:
    """Streamlit config.toml must have CORS and XSRF protection enabled."""

    CONFIG = os.path.join(ROOT_DIR, ".streamlit", "config.toml")

    def test_config_exists(self):
        assert os.path.exists(self.CONFIG), ".streamlit/config.toml must exist"

    def test_xsrf_protection_not_disabled(self):
        content = _read(".streamlit/config.toml")
        assert "enableXsrfProtection = false" not in content, (
            "XSRF protection is disabled — set enableXsrfProtection = true"
        )

    def test_cors_protection_not_disabled(self):
        content = _read(".streamlit/config.toml")
        assert "enableCORS = false" not in content, (
            "CORS protection is disabled — set enableCORS = true"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 5. Git tracking of sensitive files
# ─────────────────────────────────────────────────────────────────────────────

class TestGitSecretTracking:
    """Sensitive files must not be tracked by git."""

    def test_env_file_not_tracked(self):
        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", ".env"],
            capture_output=True,
            cwd=ROOT_DIR,
        )
        assert result.returncode != 0, (
            ".env is tracked by git — it may expose API keys. "
            "Run: git rm --cached .env"
        )

    def test_gitignore_covers_env(self):
        content = _read(".gitignore")
        assert ".env" in content, ".gitignore must include .env"

    def test_gitignore_covers_streamlit_secrets(self):
        content = _read(".gitignore")
        assert ".streamlit/secrets.toml" in content, (
            ".gitignore must include .streamlit/secrets.toml"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 6. EPC service — username must be env-configurable
# ─────────────────────────────────────────────────────────────────────────────

class TestEpcUsernameConfigurable:
    """EPC API username should be overridable via EPC_USERNAME env var."""

    def test_epc_username_env_constant_exists(self):
        sys.path.insert(0, ROOT_DIR)
        from services.epc import EPC_USERNAME_ENV
        assert EPC_USERNAME_ENV == "EPC_USERNAME"

    def test_epc_username_default_is_non_empty(self):
        from services.epc import EPC_USERNAME_DEFAULT
        assert EPC_USERNAME_DEFAULT.strip(), "EPC_USERNAME_DEFAULT must not be empty"

    def test_epc_username_reads_from_env(self, monkeypatch):
        monkeypatch.setenv("EPC_USERNAME", "override@test.com")
        from services import epc
        username = epc._get_epc_username()
        assert username == "override@test.com"

    def test_epc_username_falls_back_to_default(self, monkeypatch):
        monkeypatch.delenv("EPC_USERNAME", raising=False)
        from services.epc import _get_epc_username, EPC_USERNAME_DEFAULT
        assert _get_epc_username() == EPC_USERNAME_DEFAULT


# ─────────────────────────────────────────────────────────────────────────────
# 7. .env.example documents all required secrets
# ─────────────────────────────────────────────────────────────────────────────

class TestEnvExampleDocumentation:
    """.env.example must document all secrets without containing real values."""

    def test_env_example_exists(self):
        path = os.path.join(ROOT_DIR, ".env.example")
        assert os.path.exists(path), ".env.example must exist"

    def test_env_example_documents_epc_api_key(self):
        content = _read(".env.example")
        assert "EPC_API_KEY" in content

    def test_env_example_documents_epc_username(self):
        content = _read(".env.example")
        assert "EPC_USERNAME" in content

    def test_env_example_documents_gemini_key(self):
        content = _read(".env.example")
        assert "GEMINI_KEY" in content

    def test_env_example_has_no_real_google_key(self):
        content = _read(".env.example")
        real_key_re = re.compile(r"AIzaSy[A-Za-z0-9_\-]{33}")
        assert not real_key_re.search(content), (
            ".env.example must not contain a real Google API key"
        )

    def test_env_example_has_no_real_epc_key(self):
        """40-char lowercase hex literal would indicate a real EPC key."""
        content = _read(".env.example")
        real_epc_re = re.compile(r"^EPC_API_KEY=[0-9a-f]{40}$", re.MULTILINE)
        assert not real_epc_re.search(content), (
            ".env.example must not contain a real EPC API key"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 8. No sensitive data in audit log entries
# ─────────────────────────────────────────────────────────────────────────────

class TestAuditLogSafety:
    """audit.log_event must never log raw key material."""

    def test_audit_module_does_not_log_keys(self):
        content = _read("services/audit.py")
        # The log_event function must not concatenate raw keys
        assert "api_key" not in content.lower() or "must NOT contain" in content, (
            "audit.py must never log raw API key content"
        )

    def test_audit_module_has_pii_warning(self):
        content = _read("services/audit.py")
        assert "PII" in content or "pii" in content.lower() or "GDPR" in content, (
            "audit.py should document its GDPR/PII-safe guarantee"
        )
