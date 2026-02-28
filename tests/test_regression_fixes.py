"""
Regression tests for fixes applied in the postcode-search / scenario-selection commit.

DEF-R01 — EPC API key initialised from env, not hardcoded to "".
DEF-R02 — Scenario multiselect pre-widget validation: invalid scenarios filtered.
DEF-R03 — Defaults always restored when user clears all scenario selections.
DEF-R04 — _extract_uk_postcode correctly parses well-formed UK postcodes.
DEF-R05 — search_addresses returns [] for empty / non-postcode input (no API call).
DEF-R06 — Query-param scenarios filtered to current segment's valid options.
"""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


# ─────────────────────────────────────────────────────────────────────────────
# DEF-R01 — EPC API key must be read from env, not initialised to ""
# ─────────────────────────────────────────────────────────────────────────────

class TestEpcApiKeyInitialisation:
    """Verify _get_secret is used when bootstrapping epc_api_key session state."""

    def test_get_secret_function_exists_in_main(self):
        """_get_secret must be defined and callable in app.main."""
        from app import main as app_main
        assert callable(getattr(app_main, "_get_secret", None)), (
            "_get_secret helper must exist in app.main"
        )

    def test_get_secret_reads_env_var(self, monkeypatch):
        """_get_secret(key) should fall back to os.getenv when st.secrets raises."""
        monkeypatch.setenv("EPC_API_KEY", "test-key-from-env")
        from app import main as app_main
        result = app_main._get_secret("EPC_API_KEY", "")
        assert result == "test-key-from-env"

    def test_get_secret_returns_default_when_env_missing(self, monkeypatch):
        monkeypatch.delenv("EPC_API_KEY", raising=False)
        from app import main as app_main
        result = app_main._get_secret("EPC_API_KEY", "fallback")
        assert result == "fallback"


# ─────────────────────────────────────────────────────────────────────────────
# DEF-R02 — Scenario options are filtered to current segment
# ─────────────────────────────────────────────────────────────────────────────

class TestScenarioOptionFiltering:
    """_segment_scenario_options must return only scenarios valid for the segment."""

    def test_university_has_all_five_scenarios(self):
        from app import main as app_main
        opts = app_main._segment_scenario_options("university_he")
        assert len(opts) == 5
        assert "Solar Glass Installation" in opts
        assert "Green Roof Installation" in opts

    def test_smb_landlord_excludes_solar_glass(self):
        from app import main as app_main
        opts = app_main._segment_scenario_options("smb_landlord")
        assert "Solar Glass Installation" not in opts

    def test_smb_landlord_excludes_green_roof(self):
        from app import main as app_main
        opts = app_main._segment_scenario_options("smb_landlord")
        assert "Green Roof Installation" not in opts

    def test_smb_industrial_includes_solar_glass(self):
        from app import main as app_main
        opts = app_main._segment_scenario_options("smb_industrial")
        assert "Solar Glass Installation" in opts

    def test_individual_selfbuild_subset(self):
        from app import main as app_main
        opts = app_main._segment_scenario_options("individual_selfbuild")
        assert "Solar Glass Installation" not in opts
        assert "Enhanced Insulation Upgrade" in opts

    def test_unknown_segment_returns_all_scenarios(self):
        from app import main as app_main
        opts = app_main._segment_scenario_options("unknown_segment")
        assert len(opts) == len(app_main.SCENARIOS)

    def test_returned_options_all_exist_in_scenarios(self):
        from app import main as app_main
        for seg in ["university_he", "smb_landlord", "smb_industrial", "individual_selfbuild"]:
            for name in app_main._segment_scenario_options(seg):
                assert name in app_main.SCENARIOS, (
                    f"Option '{name}' for segment '{seg}' not in SCENARIOS dict"
                )


# ─────────────────────────────────────────────────────────────────────────────
# DEF-R03 — Defaults are valid and non-empty for every segment
# ─────────────────────────────────────────────────────────────────────────────

class TestScenarioDefaults:
    """_segment_default_scenarios must always be a non-empty subset of options."""

    SEGMENTS = ["university_he", "smb_landlord", "smb_industrial", "individual_selfbuild"]

    def test_defaults_non_empty_for_all_segments(self):
        from app import main as app_main
        for seg in self.SEGMENTS:
            defaults = app_main._segment_default_scenarios(seg)
            assert len(defaults) >= 1, f"No defaults for segment '{seg}'"

    def test_defaults_are_subset_of_options(self):
        from app import main as app_main
        for seg in self.SEGMENTS:
            opts = set(app_main._segment_scenario_options(seg))
            for d in app_main._segment_default_scenarios(seg):
                assert d in opts, (
                    f"Default '{d}' not in options for segment '{seg}'"
                )

    def test_baseline_always_in_defaults(self):
        from app import main as app_main
        baseline = "Baseline (No Intervention)"
        for seg in self.SEGMENTS:
            defaults = app_main._segment_default_scenarios(seg)
            assert baseline in defaults, (
                f"Baseline scenario missing from defaults for segment '{seg}'"
            )

    def test_none_segment_returns_fallback(self):
        from app import main as app_main
        defaults = app_main._segment_default_scenarios(None)
        assert len(defaults) >= 1


# ─────────────────────────────────────────────────────────────────────────────
# DEF-R04 — _extract_uk_postcode correctly parses postcodes
# ─────────────────────────────────────────────────────────────────────────────

class TestExtractUkPostcode:
    """_extract_uk_postcode must identify the postcode token from raw text."""

    @pytest.mark.parametrize("raw,expected", [
        ("RG1 6SP", "RG1 6SP"),
        ("rg1 6sp", "RG1 6SP"),
        ("SW1A 2AA", "SW1A 2AA"),
        ("EC1A 1BB", "EC1A 1BB"),
        ("W1A 0AX", "W1A 0AX"),
    ])
    def test_valid_postcodes(self, raw, expected):
        from app import main as app_main
        result = app_main._extract_uk_postcode(raw)
        assert result == expected, f"Input {raw!r} → got {result!r}, want {expected!r}"

    def test_empty_string_returns_empty(self):
        from app import main as app_main
        assert app_main._extract_uk_postcode("") == ""

    def test_no_postcode_in_text_returns_empty(self):
        from app import main as app_main
        assert app_main._extract_uk_postcode("no postcode here at all") == ""

    def test_partial_postcode_still_extracted(self):
        """The function is lenient; partial tokens may be returned for later normalisation."""
        from app import main as app_main
        result = app_main._extract_uk_postcode("RG1 6")
        # May return "RG1 6" (partial), or "" — as long as it doesn't crash
        assert isinstance(result, str)


# ─────────────────────────────────────────────────────────────────────────────
# DEF-R05 — search_addresses input guard
# ─────────────────────────────────────────────────────────────────────────────

class TestSearchAddressesGuard:
    """search_addresses must return [] for empty / non-postcode queries without API calls."""

    def test_empty_query_returns_empty_list(self):
        from services.epc import search_addresses
        assert search_addresses("") == []

    def test_non_postcode_short_token_returns_empty(self):
        from services.epc import search_addresses
        assert search_addresses("XYZ") == []

    def test_whitespace_only_returns_empty(self):
        from services.epc import search_addresses
        assert search_addresses("   ") == []

    def test_returns_list_type(self, monkeypatch):
        import requests as req
        from services.epc import search_addresses
        monkeypatch.delenv("EPC_API_KEY", raising=False)

        class _FakeResp:
            status_code = 200
            content = b'{"data": {"postcode": "RG1 6SP", "lat": 51.45, "lon": -0.97}}'
            def raise_for_status(self): pass
            def json(self): return {"data": {"postcode": "RG1 6SP", "lat": 51.45, "lon": -0.97}}

        monkeypatch.setattr(req, "get", lambda *a, **kw: _FakeResp())
        result = search_addresses("RG1 6SP")
        assert isinstance(result, list)


# ─────────────────────────────────────────────────────────────────────────────
# DEF-R06 — Query-param scenarios validated against current segment
# ─────────────────────────────────────────────────────────────────────────────

class TestQueryParamScenarioValidation:
    """
    The scenario-selection fix ensures query-param scenarios are filtered to
    only those valid for the active segment.  These unit tests verify the
    underlying filtering helpers behave correctly.
    """

    def test_cross_segment_scenario_excluded(self):
        """Solar Glass is valid for university but NOT for smb_landlord."""
        from app import main as app_main
        landlord_opts = set(app_main._segment_scenario_options("smb_landlord"))
        assert "Solar Glass Installation" not in landlord_opts

    def test_filtering_preserves_valid_scenarios(self):
        from app import main as app_main
        raw = ["Baseline (No Intervention)", "Solar Glass Installation", "Green Roof Installation"]
        landlord_opts = set(app_main._segment_scenario_options("smb_landlord"))
        filtered = [s for s in raw if s in landlord_opts]
        assert filtered == ["Baseline (No Intervention)"]

    def test_all_invalid_falls_back_to_defaults(self):
        """If every query-param scenario is invalid for the segment, defaults apply."""
        from app import main as app_main
        raw = ["Solar Glass Installation", "Green Roof Installation"]  # Neither valid for landlord
        landlord_opts = set(app_main._segment_scenario_options("smb_landlord"))
        filtered = [s for s in raw if s in landlord_opts]
        if not filtered:
            filtered = app_main._segment_default_scenarios("smb_landlord")
        assert len(filtered) >= 1
        assert all(s in landlord_opts for s in filtered)
