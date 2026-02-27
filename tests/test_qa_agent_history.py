"""
QA Test Suite — core/agent.py
================================
Tests for DEF-005 (agent history bounding) and DEF-009 (max-loop error surfacing).

Uses mocked Gemini API calls to avoid network dependency.
"""
from __future__ import annotations

import os
import sys
import pytest

_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

import core.agent as agent


# ─────────────────────────────────────────────────────────────────────────────
# DEF-009 REGRESSION: max-loop error surfacing
# ─────────────────────────────────────────────────────────────────────────────

class TestMaxLoopErrorSurfacing:
    """When max loops is hit and summarisation also fails, error should be returned."""

    def _make_fn_call_response(self, fn_name: str = "run_scenario"):
        """Build a mock Gemini response that contains a function call."""
        return {
            "candidates": [{
                "content": {
                    "role": "model",
                    "parts": [{
                        "functionCall": {
                            "name": fn_name,
                            "args": {
                                "building_name": "Greenfield Library",
                                "scenario_name": "Baseline (No Intervention)",
                            }
                        }
                    }]
                },
                "finishReason": "STOP",
            }]
        }

    def _make_text_response(self, text: str = "Summary here."):
        return {
            "candidates": [{
                "content": {
                    "role": "model",
                    "parts": [{"text": text}]
                },
                "finishReason": "STOP",
            }]
        }

    def _make_error_response(self, error: str = "API error"):
        return {"error": error}

    def test_error_surfaced_when_summarisation_fails(self, monkeypatch):
        """When max loops AND summarisation fail, error key must be non-None."""
        call_count = {"n": 0}

        def mock_call_gemini(api_key, messages, use_tools=True):
            call_count["n"] += 1
            if use_tools:
                # Always return a function call to consume loops
                return self._make_fn_call_response()
            else:
                # Summarisation call fails
                return self._make_error_response("Quota exceeded")

        monkeypatch.setattr(agent, "_call_gemini", mock_call_gemini)
        monkeypatch.setattr(agent, "MAX_AGENT_LOOPS", 2)

        from core.physics import BUILDINGS, SCENARIOS, calculate_thermal_load

        result = agent.run_agent(
            api_key="fake",
            user_message="Test question",
            conversation_history=[],
            buildings=BUILDINGS,
            scenarios=SCENARIOS,
            calculate_fn=calculate_thermal_load,
            current_context={"building": "Greenfield Library"},
        )

        assert result["error"] is not None, (
            "Expected error to be surfaced when summarisation fails, got None"
        )
        assert "Max loops" in result["error"] or "summarisation" in result["error"].lower(), (
            f"Error message doesn't explain max-loop failure: {result['error']}"
        )

    def test_no_error_when_summarisation_succeeds(self, monkeypatch):
        """When summarisation succeeds, error should be None."""
        call_count = {"n": 0}

        def mock_call_gemini(api_key, messages, use_tools=True):
            call_count["n"] += 1
            if use_tools:
                return self._make_fn_call_response()
            else:
                return self._make_text_response("Here is my summary.")

        monkeypatch.setattr(agent, "_call_gemini", mock_call_gemini)
        monkeypatch.setattr(agent, "MAX_AGENT_LOOPS", 2)

        from core.physics import BUILDINGS, SCENARIOS, calculate_thermal_load

        result = agent.run_agent(
            api_key="fake",
            user_message="Test question",
            conversation_history=[],
            buildings=BUILDINGS,
            scenarios=SCENARIOS,
            calculate_fn=calculate_thermal_load,
            current_context={"building": "Greenfield Library"},
        )

        assert result["error"] is None
        assert "Here is my summary" in result["answer"]


# ─────────────────────────────────────────────────────────────────────────────
# DEF-005: History bounding (tested at app layer via simulate)
# ─────────────────────────────────────────────────────────────────────────────

class TestAgentLoopTermination:
    """Agent must always return within MAX_AGENT_LOOPS iterations."""

    def test_loop_terminates_within_max(self, monkeypatch):
        call_count = {"n": 0}

        def mock_call_gemini(api_key, messages, use_tools=True):
            call_count["n"] += 1
            if use_tools:
                return {
                    "candidates": [{
                        "content": {
                            "role": "model",
                            "parts": [{"functionCall": {
                                "name": "run_scenario",
                                "args": {
                                    "building_name": "Greenfield Library",
                                    "scenario_name": "Baseline (No Intervention)",
                                }
                            }}]
                        },
                        "finishReason": "STOP",
                    }]
                }
            else:
                return {
                    "candidates": [{
                        "content": {"role": "model", "parts": [{"text": "Done."}]},
                        "finishReason": "STOP",
                    }]
                }

        monkeypatch.setattr(agent, "_call_gemini", mock_call_gemini)
        original_max = agent.MAX_AGENT_LOOPS
        monkeypatch.setattr(agent, "MAX_AGENT_LOOPS", 5)

        from core.physics import BUILDINGS, SCENARIOS, calculate_thermal_load

        result = agent.run_agent(
            api_key="fake",
            user_message="What is the thermal load?",
            conversation_history=[],
            buildings=BUILDINGS,
            scenarios=SCENARIOS,
            calculate_fn=calculate_thermal_load,
            current_context={"building": "Greenfield Library"},
        )

        # 5 tool calls + 1 summarisation = 6 total
        assert call_count["n"] <= agent.MAX_AGENT_LOOPS + 2
        assert "answer" in result
        assert "loops" in result

    def test_successful_answer_terminates_early(self, monkeypatch):
        """A text response from Gemini should terminate the loop immediately."""
        call_count = {"n": 0}

        def mock_call_gemini(api_key, messages, use_tools=True):
            call_count["n"] += 1
            return {
                "candidates": [{
                    "content": {"role": "model", "parts": [{"text": "The answer is X."}]},
                    "finishReason": "STOP",
                }]
            }

        monkeypatch.setattr(agent, "_call_gemini", mock_call_gemini)

        from core.physics import BUILDINGS, SCENARIOS, calculate_thermal_load

        result = agent.run_agent(
            api_key="fake",
            user_message="Quick question",
            conversation_history=[],
            buildings=BUILDINGS,
            scenarios=SCENARIOS,
            calculate_fn=calculate_thermal_load,
            current_context={},
        )

        assert call_count["n"] == 1, "Should have terminated after first text response"
        assert result["answer"] == "The answer is X."
        assert result["error"] is None


# ─────────────────────────────────────────────────────────────────────────────
# Tool execution
# ─────────────────────────────────────────────────────────────────────────────

class TestToolExecution:
    """Known tool names must execute without crashing.

    Tool names are: run_scenario, compare_all_buildings, find_best_for_budget,
    get_building_info, list_buildings, list_scenarios.
    """

    def _call_tool(self, tool_name: str, args: dict):
        from core.physics import BUILDINGS, SCENARIOS, calculate_thermal_load
        # execute_tool signature: (name, args, buildings, scenarios, calculate_fn)
        return agent.execute_tool(
            name=tool_name,
            args=args,
            buildings=BUILDINGS,
            scenarios=SCENARIOS,
            calculate_fn=calculate_thermal_load,
        )

    def test_run_scenario_known_building(self):
        result = self._call_tool("run_scenario", {
            "building_name": "Greenfield Library",
            "scenario_name": "Baseline (No Intervention)",
        })
        assert "error" not in result
        assert "scenario_energy_mwh" in result

    def test_run_scenario_unknown_building_returns_error(self):
        result = self._call_tool("run_scenario", {
            "building_name": "Fake Building",
            "scenario_name": "Baseline (No Intervention)",
        })
        assert "error" in result

    def test_compare_all_buildings_returns_dict(self):
        result = self._call_tool("compare_all_buildings", {
            "scenario_name": "Baseline (No Intervention)",
        })
        assert isinstance(result, dict)
        assert "results" in result

    def test_unknown_tool_returns_error(self):
        result = self._call_tool("nonexistent_tool", {})
        assert "error" in result

    def test_find_best_for_budget_returns_recommendation(self):
        result = self._call_tool("find_best_for_budget", {
            "budget_gbp": 500000,
        })
        # Should return a dict with top_recommendation or error
        assert isinstance(result, dict)

    def test_get_building_info_known_building(self):
        result = self._call_tool("get_building_info", {
            "building_name": "Greenfield Library",
        })
        assert "error" not in result
        assert "building" in result

    def test_list_buildings_returns_list(self):
        result = self._call_tool("list_buildings", {})
        assert isinstance(result, (dict, list))
