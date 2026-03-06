# ═══════════════════════════════════════════════════════════════════════════════
# CrowAgent™ Platform — AI Advisor Agent
# © 2026 Aparajita Parihar. All rights reserved.
#
# Independent research project. Not affiliated with any institution.
# Not licensed for commercial use without written permission of the author.
# Trademark rights reserved pending UK IPO registration — Class 42.
#
# Agentic AI module: tool-use loop powered by Google Gemini 1.5 Pro
# Free tier: 10 requests/min · 1,500 requests/day · No credit card required
# Get API key free at: https://aistudio.google.com
# ═══════════════════════════════════════════════════════════════════════════════

import json
import requests
import time
from typing import Any

import config.constants as constants
import core.physics as physics
from config.scenarios import SCENARIOS

# ─────────────────────────────────────────────────────────────────────────────
# API & MODEL CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
GEMINI_URL           = "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent"
GEMINI_FALLBACK_URLS = [
    GEMINI_URL,
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
]
MAX_OUTPUT_TOKENS    = 2000
MAX_AGENT_LOOPS      = 10

def build_system_prompt(segment: str, portfolio: list) -> str:
    """
    Builds a dynamic, context-aware system prompt for the AI Advisor.

    Args:
        segment: The active user segment (e.g., 'university_he').
        portfolio: A list of building data dictionaries.

    Returns:
        A formatted string to be used as the system prompt for the Gemini model.
    """
    # Guard against argument swapping (legacy compatibility)
    if isinstance(segment, list) and isinstance(portfolio, str):
        segment, portfolio = portfolio, segment

    # Ensure prompt always contains direct JSON context for deterministic grounding.
    segment_json = json.dumps(segment, ensure_ascii=False)
    portfolio_json = json.dumps(portfolio, ensure_ascii=False, default=str, indent=2)

    # 1. Dashboard Aggregation: Calculate totals from the portfolio.
    total_area = sum(b.get("floor_area_m2", 0) or 0 for b in portfolio)
    total_energy = sum(b.get("baseline_energy_mwh", 0) or 0 for b in portfolio)

    if portfolio:
        building_list = []
        for b in portfolio:
            name = b.get("name", "Unnamed Asset")
            area = b.get("floor_area_m2", 0) or 0
            energy = b.get("baseline_energy_mwh", 0) or 0
            building_list.append(
                f"- **{name}**: {area:,.0f} m², {energy:,.0f} MWh/yr"
            )
        portfolio_summary = (
            "**Portfolio Summary:**\n"
            f"- **Total Buildings:** {len(portfolio)}\n"
            f"- **Total Floor Area:** {total_area:,.0f} m²\n"
            f"- **Total Baseline Energy:** {total_energy:,.0f} MWh/yr\n\n"
            "**Building List:**\n" + "\n".join(building_list)
        )
    else:
        portfolio_summary = "**Portfolio Summary:**\n- No assets have been loaded. The portfolio is empty."

    # 2. Capabilities Awareness: Define what the AI can do.
    capabilities = """- **Dashboard Summary:** Synthesise portfolio data to provide a high-level overview of energy, and area.
- **Compliance Analysis:** Identify and explain regulatory compliance gaps (e.g., MEES, SECR) based on the user's specific business segment.
- **Financial ROI:** Calculate and compare the return on investment, payback periods, and cost-effectiveness of various retrofit scenarios.
- **Thermal Physics Modelling:** Use the integrated physics engine to run detailed thermal simulations for specific buildings and interventions."""

    # 3. Segment Lock & Core Instructions
    instructions = f"""**CRITICAL INSTRUCTIONS:**
1.  **Segment Focus:** Your advice **MUST** be strictly tailored to the user's active segment: **'{segment}'**. All compliance rules, regulations, and recommendations must be relevant to this segment only. Do not discuss rules for other segments.
2.  **2026 UK Compliance Baseline:** Follow current UK guidance with a **fabric-first** approach. Prioritise insulation and glazing upgrades (Part L alignment) before recommending mechanical systems (e.g., heat pumps), unless tool evidence proves a different order for a specific building.
3.  **MEES Cost Cap:** For PRS/MEES upgrade planning, cite and use the **£10,000** cost cap (not £3,500).
4.  **Regulatory Links (Mandatory):** When providing UK compliance advice, you **MUST** include relevant official references. Include these links when relevant:
    - EPC register: https://www.gov.uk/find-energy-certificate
    - MEES landlord guidance: https://www.gov.uk/guidance/domestic-private-rented-property-minimum-energy-efficiency-standard-landlord-guidance
    - Part L approved document: https://www.gov.uk/government/publications/conservation-of-fuel-and-power-approved-document-l
    Always prefer `gov.uk` or other official regulatory bodies.
5.  **Building-by-Building Analysis:** Analyse the portfolio asset-by-asset and clearly separate findings for each building before giving portfolio-level recommendations.
6.  **No Assumptions (Guardrail):** You **MUST NOT** invent, estimate, or assume any quantitative data (costs, energy savings, performance metrics). Your primary function is to execute the available tools to gather real data. If a user asks a question that requires a calculation, run the appropriate tool. If you cannot answer without a tool, state that you need to run a tool first.
7.  **Tool-First Workflow:** Always use your tools to gather evidence *before* formulating an answer. Your response should be a synthesis of the data returned by the tools.
8.  **Honesty and Transparency:** If a tool fails or the data is unavailable, state it clearly. Do not attempt to fill in the gaps.
"""

    # Combine all parts into the final system prompt
    return (
        "You are CrowAgent™, a world-class, physics-informed AI sustainability consultant for the UK built environment.\n\n"
        "## User Context\n"
        f"The user is operating in the **'{segment}'** segment. Your advice and analysis must be strictly confined to the regulations and commercial drivers of this sector.\n\n"
        "## Raw Runtime Context (JSON)\n"
        f"- segment: `{segment_json}`\n"
        f"- portfolio:\n```json\n{portfolio_json}\n```\n\n"
        f"## Portfolio Snapshot\n{portfolio_summary}\n\n"
        "## AI Capabilities\n"
        "You have the following capabilities:\n"
        f"{capabilities}\n\n"
        f"{instructions}"
    )

# ─────────────────────────────────────────────────────────────────────────────
# TOOL SCHEMAS — sent to Gemini so it knows what tools exist and how to call them
# ─────────────────────────────────────────────────────────────────────────────
AGENT_TOOLS = [
    {
        "name": "run_scenario",
        "description": (
            "Run the CrowAgent™ physics thermal model for one specific building "
            "and one specific intervention scenario. Returns energy, carbon, cost "
            "saving, payback period, and all U-values."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "building_name": {
                    "type": "string",
                    "description": "The name of the building to analyze. Must be one of the currently active buildings in the portfolio.",
                },
                "scenario_name": {
                    "type": "string",
                    "description": (
                        "One of: 'Baseline (No Intervention)', "
                        "'Solar Glass Installation', 'Green Roof Installation', "
                        "'Enhanced Insulation Upgrade', "
                        "'Combined Package (All Interventions)'"
                    ),
                },
                "temperature_c": {
                    "type": "number",
                    "description": "External ambient temperature in °C. Default 10.5 (UK annual average).",
                },
            },
            "required": ["building_name", "scenario_name"],
        },
    },
    {
        "name": "compare_all_buildings",
        "description": (
            "Run a single scenario across ALL three campus buildings simultaneously. "
            "Returns ranked results showing which building benefits most from the intervention."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "scenario_name": {
                    "type": "string",
                    "description": (
                        "One of: 'Solar Glass Installation', 'Green Roof Installation', "
                        "'Enhanced Insulation Upgrade', 'Combined Package (All Interventions)'"
                    ),
                },
                "temperature_c": {
                    "type": "number",
                    "description": "External temperature °C. Default 10.5.",
                },
            },
            "required": ["scenario_name"],
        },
    },
    {
        "name": "find_best_for_budget",
        "description": (
            "Exhaustively search all building + scenario combinations to find "
            "the single best investment within a given budget. Ranks by "
            "cost-per-tonne-CO₂e (best value for Net Zero spending)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "budget_gbp": {
                    "type": "number",
                    "description": "Maximum available capital budget in GBP.",
                },
                "temperature_c": {
                    "type": "number",
                    "description": "External temperature °C. Default 10.5.",
                },
            },
            "required": ["budget_gbp"],
        },
    },
    {
        "name": "get_building_info",
        "description": (
            "Retrieve the full technical specification for a building: "
            "floor area, U-values, glazing ratio, baseline energy, occupancy hours."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "building_name": {
                    "type": "string",
                    "description": "The name of the building to retrieve info for.",
                },
            },
            "required": ["building_name"],
        },
    },
    {
        "name": "rank_all_scenarios",
        "description": (
            "Run all five scenarios for one building and rank them by a chosen metric. "
            "Useful for 'what's the best intervention for Building X?' questions."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "building_name": {
                    "type": "string",
                    "description": "The name of the building to rank scenarios for.",
                },
                "rank_by": {
                    "type": "string",
                    "description": (
                        "Metric to rank by. One of: "
                        "'carbon_saving' (most CO₂ reduction), "
                        "'annual_saving_gbp' (most £ saved per year), "
                        "'payback_years' (fastest payback), "
                        "'cost_per_tonne' (best £/tCO₂e value)"
                    ),
                },
                "temperature_c": {
                    "type": "number",
                    "description": "External temperature °C. Default 10.5.",
                },
            },
            "required": ["building_name"],
        },
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# TOOL EXECUTOR
# Receives a function name + args from Gemini → calls the real Python function
# → returns a JSON-serialisable result dict
# ─────────────────────────────────────────────────────────────────────────────
def execute_tool(
    name: str,
    args: dict,
    buildings: dict,
    scenarios: dict,
    calculate_fn=None,
    tariff: float = constants.DEFAULT_ELECTRICITY_TARIFF_GBP_PER_KWH,
) -> dict[str, Any]:
    """
    Execute a named tool with given args.
    buildings and scenarios are injected from the main app.
    Calls core.physics directly.
    """
    temp = float(args.get("temperature_c", 10.5))
    weather = {"temperature_c": temp, "wind_speed_mph": 9.2}
    calc = calculate_fn or physics.calculate_thermal_load

    # ── Tool: run_scenario ────────────────────────────────────────────────────
    if name == "run_scenario":
        bname = args["building_name"]
        sname = args["scenario_name"]
        if bname not in buildings:
            return {"error": f"Building '{bname}' not found. "
                    f"Available: {list(buildings.keys())}"}
        if sname not in scenarios:
            return {"error": f"Scenario '{sname}' not found. "
                    f"Available: {list(scenarios.keys())}"}
        try:
            result = calc(
                buildings[bname], scenarios[sname], weather, tariff
            )
        except Exception as exc:
            return {"error": f"Scenario calculation failed for '{bname}' / '{sname}': {exc}"}
        result["building"] = bname
        result["scenario"] = sname
        result["temperature_c"] = temp
        result["install_cost_gbp"] = scenarios[sname]["install_cost_gbp"]
        if result.get("annual_saving_gbp", 0) > 0 and scenarios[sname]["install_cost_gbp"] > 0:
            result["cost_per_tonne_co2"] = round(
                scenarios[sname]["install_cost_gbp"]
                / max(result["carbon_saving_t"], 0.01), 1
            )
        return result

    # ── Tool: compare_all_buildings ───────────────────────────────────────────
    elif name == "compare_all_buildings":
        sname = args["scenario_name"]
        if sname not in scenarios:
            return {"error": f"Scenario '{sname}' not found."}
        rows = []
        for bname, bdata in buildings.items():
            try:
                r = calc(
                    bdata, scenarios[sname], weather, tariff
                )
            except Exception:
                continue
            cost = scenarios[sname]["install_cost_gbp"]
            rows.append({
                "building":           bname,
                "scenario":           sname,
                "energy_saving_mwh":  r["energy_saving_mwh"],
                "energy_saving_pct":  r["energy_saving_pct"],
                "carbon_saving_t":    r["carbon_saving_t"],
                "annual_saving_gbp":  r["annual_saving_gbp"],
                "install_cost_gbp":   cost,
                "payback_years":      r["payback_years"],
                "cost_per_tonne_co2": round(cost / max(r["carbon_saving_t"], 0.01), 1)
                                      if cost > 0 else None,
            })
        rows.sort(key=lambda x: x["carbon_saving_t"], reverse=True)
        return {"scenario": sname, "results": rows, "temperature_c": temp}

    # ── Tool: find_best_for_budget ────────────────────────────────────────────
    elif name == "find_best_for_budget":
        budget = float(args["budget_gbp"])
        candidates = []
        for bname, bdata in buildings.items():
            for sname, sdata in scenarios.items():
                if sdata["install_cost_gbp"] <= 0:
                    continue
                if sdata["install_cost_gbp"] > budget:
                    continue
                try:
                    r = calc(
                        bdata, sdata, weather, tariff
                    )
                except Exception:
                    continue
                if r["carbon_saving_t"] <= 0:
                    continue
                candidates.append({
                    "building":           bname,
                    "scenario":           sname,
                    "install_cost_gbp":   sdata["install_cost_gbp"],
                    "carbon_saving_t":    r["carbon_saving_t"],
                    "annual_saving_gbp":  r["annual_saving_gbp"],
                    "payback_years":      r["payback_years"],
                    "energy_saving_mwh":  r["energy_saving_mwh"],
                    "cost_per_tonne_co2": round(
                        sdata["install_cost_gbp"] / max(r["carbon_saving_t"], 0.01), 1
                    ),
                })
        if not candidates:
            return {"error": f"No scenarios fit within £{budget:,.0f} budget."}
        candidates.sort(key=lambda x: x["cost_per_tonne_co2"])
        return {
            "budget_gbp": budget,
            "top_recommendation": candidates[0],
            "all_options_ranked": candidates[:5],
            "temperature_c": temp,
        }

    # ── Tool: get_building_info ───────────────────────────────────────────────
    elif name == "get_building_info":
        bname = args["building_name"]
        if bname not in buildings:
            return {"error": f"Building '{bname}' not found."}
        b = buildings[bname]
        baseline_carbon = round(b["baseline_energy_mwh"] * 1000 * constants.CI_ELECTRICITY / 1000, 1)
        return {
            "building":              bname,
            "floor_area_m2":         b["floor_area_m2"],
            "height_m":              b["height_m"],
            "glazing_ratio_pct":     b["glazing_ratio"] * 100,
            "u_value_wall_wm2k":     b["u_value_wall"],
            "u_value_roof_wm2k":     b["u_value_roof"],
            "u_value_glazing_wm2k":  b["u_value_glazing"],
            "baseline_energy_mwh":   b["baseline_energy_mwh"],
            "baseline_carbon_t_co2": baseline_carbon,
            "baseline_cost_gbp_yr":  round(b["baseline_energy_mwh"] * 1000 * constants.DEFAULT_ELECTRICITY_TARIFF_GBP_PER_KWH, 0),
            "occupancy_hours_yr":    b["occupancy_hours"],
            "built_year":            b["built_year"],
            "description":           b.get("description", ""),
        }

    # ── Tool: rank_all_scenarios ──────────────────────────────────────────────
    elif name == "rank_all_scenarios":
        bname = args["building_name"]
        rank_by = args.get("rank_by", "cost_per_tonne")
        if bname not in buildings:
            return {"error": f"Building '{bname}' not found."}
        rows = []
        for sname, sdata in scenarios.items():
            try:
                r = calc(
                    buildings[bname], sdata, weather, tariff
                )
            except Exception:
                continue
            cost = sdata["install_cost_gbp"]
            cpt = round(cost / max(r["carbon_saving_t"], 0.01), 1) if cost > 0 else None
            rows.append({
                "scenario":           sname,
                "carbon_saving_t":    r["carbon_saving_t"],
                "annual_saving_gbp":  r["annual_saving_gbp"],
                "install_cost_gbp":   cost,
                "payback_years":      r["payback_years"],
                "energy_saving_mwh":  r["energy_saving_mwh"],
                "cost_per_tonne_co2": cpt,
            })
        sort_map = {
            "carbon_saving":     lambda x: -(x["carbon_saving_t"] or 0),
            "annual_saving_gbp": lambda x: -(x["annual_saving_gbp"] or 0),
            "payback_years":     lambda x:  (x["payback_years"] or 999),
            "cost_per_tonne":    lambda x:  (x["cost_per_tonne_co2"] or 999),
        }
        key_fn = sort_map.get(rank_by, sort_map["cost_per_tonne"])
        rows.sort(key=key_fn)
        return {
            "building":  bname,
            "ranked_by": rank_by,
            "scenarios": rows,
        }

    elif name == "list_buildings":
        return {"buildings": sorted(list(buildings.keys()))}

    return {"error": f"Unknown tool: {name}"}


# ─────────────────────────────────────────────────────────────────────────────
# GEMINI API CALL
# ─────────────────────────────────────────────────────────────────────────────
def _call_gemini(
    api_key: str,
    messages: list,
    system_prompt: str,
    use_tools: bool = True,
) -> dict:
    """
    Single Gemini API call with schema fallbacks for API-version differences.
    messages format: [{"role": "user"|"model", "parts": [...]}]
    """
    # API Key validation and sanitization for debugging
    if not api_key or not isinstance(api_key, str):
        print("--- GEMINI API DEBUG ---")
        print("CRITICAL: API key is missing or not a string.")
        print("--- END DEBUG ---")
        return {"error": "Gemini API key is missing."}

    clean_api_key = api_key.strip()
    if len(clean_api_key) != 39:
        print("--- GEMINI API DEBUG ---")
        print(f"WARNING: API key length is {len(clean_api_key)}, expected 39. Key might be truncated.")
        print(f"Key used: '{clean_api_key[:5]}...{clean_api_key[-4:]}'")
        print("--- END DEBUG ---")
    if not clean_api_key.startswith("AIza"):
        print("--- GEMINI API DEBUG ---")
        print("WARNING: API key does not start with 'AIza'. It may be invalid.")
        print(f"Key prefix: '{clean_api_key[:4]}'")
        print("--- END DEBUG ---")

    # Primary payload for REST API (camelCase keys required)
    payload_camel: dict = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": messages,
        "generationConfig": {
            "maxOutputTokens": MAX_OUTPUT_TOKENS,
            "temperature": 0.2,
            "topP": 0.8,
        },
    }
    if use_tools:
        payload_camel["tools"] = [{"functionDeclarations": AGENT_TOOLS}]
        payload_camel["toolConfig"] = {
            "functionCallingConfig": {"mode": "AUTO"}
        }

    # Final fallback: no top-level system/tool fields at all.
    # We inject the system prompt into the first user message to avoid schema mismatches.
    merged_messages = list(messages)
    if merged_messages and merged_messages[0].get("role") == "user":
        first_parts = merged_messages[0].get("parts", [])
        first_text = first_parts[0].get("text", "") if first_parts else ""
        merged_messages[0] = {
            "role": "user",
            "parts": [{"text": f"[SYSTEM INSTRUCTIONS]\n{system_prompt}\n\n[USER MESSAGE]\n{first_text}"}],
        }
    payload_minimal = {
        "contents": merged_messages,
        "generationConfig": {
            "maxOutputTokens": MAX_OUTPUT_TOKENS,
            "temperature": 0.2,
            "topP": 0.8,
        },
    }

    attempts = [payload_camel, payload_minimal]
    last_error = None

    for url in GEMINI_FALLBACK_URLS:
        for idx, payload in enumerate(attempts, start=1):
            try:
                resp = requests.post(
                    url,
                    timeout=30,
                    headers={"Content-Type": "application/json", "x-goog-api-key": clean_api_key},
                    json=payload,
                )
            except requests.exceptions.Timeout:
                last_error = "Gemini API request timed out (30 s). Check your connection and retry."
                continue
            except requests.exceptions.ConnectionError:
                last_error = "Could not connect to Gemini API. Check your internet connection."
                continue
            except requests.exceptions.RequestException as exc:
                last_error = f"Gemini API request failed: {exc}"
                continue

            if resp.status_code == 200:
                return resp.json()

            # Parse error and decide whether to retry schema or fallback endpoint/model.
            try:
                error_data = resp.json()
                error_msg = error_data.get("error", {}).get("message", resp.text[:200])
            except Exception:
                error_msg = resp.text[:200]

            last_error = f"Gemini API error {resp.status_code} ({url}): {error_msg}"
            lower = error_msg.lower()
            schema_mismatch = (
                "unknown name" in lower
                or "cannot find field" in lower
                or "invalid json payload" in lower
            )
            model_not_found = (
                resp.status_code == 404
                and ("is not found" in lower or "not supported for generatecontent" in lower)
            )

            if schema_mismatch and idx < len(attempts):
                continue

            # Try next model/endpoint if this one is unavailable.
            if model_not_found:
                break

            return {"error": last_error}

    return {"error": last_error or "Gemini API request failed across all endpoint/model fallbacks."}


def _invoke_gemini_with_compat(
    api_key: str,
    messages: list,
    system_prompt: str,
    use_tools: bool = True,
) -> dict:
    """Compatibility wrapper retained for legacy call sites."""
    return _call_gemini(
        api_key=api_key,
        messages=messages,
        system_prompt=system_prompt,
        use_tools=use_tools,
    )


# ─────────────────────────────────────────────────────────────────────────────
# AGENTIC LOOP
# Think → Call tools → Observe results → Think again → Final answer
# Yields status updates for UI transparency.
# ─────────────────────────────────────────────────────────────────────────────
def run_agent_turn(
    user_message: str,
    segment: str,
    portfolio: list,
    api_key: str,
    status_widget=None,
) -> str:
    """
    Run the full agentic loop for one user turn.
    Returns the AI's final text response as a string.
    Raises RuntimeError on unrecoverable API errors.
    """
    # Build context-aware system prompt from segment and portfolio
    system_prompt = build_system_prompt(segment=segment, portfolio=portfolio)

    # Convert portfolio list to building registry dict for tool execution
    building_registry = {b["name"]: b for b in portfolio}
    scenario_registry = SCENARIOS
    tariff = constants.DEFAULT_ELECTRICITY_TARIFF_GBP_PER_KWH

    # Build initial message list for this turn
    messages: list = []

    # Inject available buildings context to help the agent know valid tool arguments
    b_names = list(building_registry.keys())
    b_list = ", ".join(f"'{name}'" for name in b_names)
    ctx_text = f"\n\n[System Context: Active buildings: {b_list}]" if b_names else ""

    messages.append({
        "role": "user",
        "parts": [{"text": user_message + ctx_text}]
    })

    tool_calls_log = []
    loops = 0

    if status_widget:
        status_widget.update(label="⚙️ Connecting to Gemini API...")

    while loops < MAX_AGENT_LOOPS:
        loops += 1
        response = _invoke_gemini_with_compat(api_key, messages, system_prompt, use_tools=True)

        # Handle API error
        if "error" in response:
            raise RuntimeError(response["error"])

        candidates = response.get("candidates", [])
        if not candidates:
            raise RuntimeError("No candidates in Gemini response")

        content = candidates[0].get("content", {})
        parts   = content.get("parts", [])

        # Check for function calls in the response
        function_calls = [p for p in parts if "functionCall" in p]
        text_parts     = [p for p in parts if "text" in p]

        # ── If there are function calls → execute them ──
        if function_calls:
            # Add model's message (containing function calls) to history
            messages.append({"role": "model", "parts": parts})

            if status_widget:
                status_widget.update(label="🔬 Running thermal simulation...")

            # Execute each function call and collect results
            function_results = []
            for fc_part in function_calls:
                fc    = fc_part["functionCall"]
                name  = fc["name"]
                fargs = fc.get("args", {})

                # Execute the tool
                result = execute_tool(
                    name=name,
                    args=fargs,
                    buildings=building_registry,
                    scenarios=scenario_registry,
                    calculate_fn=physics.calculate_thermal_load,
                    tariff=tariff,
                )

                tool_calls_log.append({
                    "name": name,
                    "args": fargs,
                    "result": result,
                })

                function_results.append({
                    "functionResponse": {
                        "name": name,
                        "response": {"result": result},
                    }
                })

            # Add function results back into the conversation
            messages.append({
                "role": "function",
                "parts": function_results,
            })
            # Loop continues — agent sees results and decides next step

        # ── If there's a text response → we're done ──
        elif text_parts:
            final_text = " ".join(p["text"] for p in text_parts if p.get("text"))
            # Add model's final response to history
            messages.append({"role": "model", "parts": parts})

            if status_widget:
                status_widget.update(label="📝 Generating recommendation...")

            return final_text.strip()

        else:
            # Unexpected response structure
            return "I received an unexpected response. Please try again."

    # Hit max loops — ask Gemini to summarise what it found so far
    if status_widget:
        status_widget.update(label="📝 Generating recommendation...")

    messages.append({
        "role": "user",
        "parts": [{"text": "Please summarise your findings so far in 3 sentences."}]
    })
    final_resp = _invoke_gemini_with_compat(api_key, messages, system_prompt, use_tools=False)
    summarisation_error = final_resp.get("error")
    if not summarisation_error:
        parts = final_resp.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        text = " ".join(p.get("text", "") for p in parts)
        return text.strip() or "Analysis complete — see tool results above."

    # Summarisation itself failed — surface the error so the UI can display it
    return "Reached maximum reasoning steps. See tool results above."
