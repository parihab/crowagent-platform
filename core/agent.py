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
from typing import Any

# ─────────────────────────────────────────────────────────────────────────────
# API & MODEL CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
GEMINI_URL           = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
MAX_OUTPUT_TOKENS    = 2000
MAX_AGENT_LOOPS      = 10

# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM PROMPT
# The agent's identity, knowledge, and behavioural rules
# ─────────────────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are the CrowAgent™ AI Advisor — an expert sustainability \
engineer embedded inside the CrowAgent™ Platform, a physics-informed campus \
thermal intelligence system.

YOUR ROLE:
You help university estate managers make evidence-based, cost-effective \
sustainability investment decisions. You reason about buildings, run \
physics simulations using your tools, and translate technical outputs \
into clear, actionable recommendations.

YOUR TOOLS — use them proactively, do not just answer from memory:
• run_scenario: Run the PINN thermal model for one building + one intervention
• compare_all_buildings: Run all buildings through one scenario simultaneously
• find_best_for_budget: Exhaustively find the highest-ROI intervention within a budget
• get_building_info: Retrieve full specifications for a building
• rank_all_scenarios: Rank every intervention for a building by a chosen metric

PHYSICS CONSTANTS (cite these in your answers):
• Carbon intensity: 0.20482 kgCO₂e/kWh (BEIS 2023)
• UK HE electricity cost: £0.28/kWh (HESA 2022-23)
• Heating set-point: 21°C (UK Building Regulations Part L)
• Heating season: 5,800 hours/yr (CIBSE Guide A)
• Solar irradiance (Reading): 950 kWh/m²/yr (PVGIS)

BEHAVIOUR RULES:
1. ALWAYS use tools to get real numbers — never invent figures
2. When asked about multiple buildings or scenarios, call the tool for each one
3. Cite the data source for every number you quote
4. Give a specific recommendation, not a list of options
5. Keep answers concise — 3–5 sentences maximum unless asked for detail
6. If a question is outside your scope (not about campus energy/sustainability),
   politely say so in one sentence

PLATFORM CONTEXT:
Buildings: Greenfield Library, Greenfield Arts Building, Greenfield Science Block
(Greenfield University is a FICTIONAL institution used for demonstration only.
 All building data is derived from published UK HE sector averages — not real buildings.)
Scenarios: Baseline, Solar Glass, Green Roof, Enhanced Insulation, Combined Package

MANDATORY DISCLAIMER — include a brief version in EVERY response:
Always end recommendations with one of these phrases (adapt as appropriate):
"⚠️ These figures are indicative only. Verify with a qualified energy surveyor before investment."
OR
"⚠️ Model outputs based on simplified physics — commission a site survey before proceeding."

ACCURACY LIMITATIONS you must be aware of:
1. The physics model uses simplified steady-state assumptions — real buildings are more complex
2. Energy prices may change — financial figures assume constant £0.28/kWh
3. Installation costs are typical ranges — actual quotes may vary significantly
4. You are an AI and can make mistakes — never present results as definitive
5. This platform is a working prototype — results are indicative only
"""


# ─────────────────────────────────────────────────────────────────────────────
# TOOL SCHEMAS — sent to Gemini so it knows what tools exist and how to call them
# ─────────────────────────────────────────────────────────────────────────────
TOOL_DECLARATIONS = [
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
                    "description": (
                        "One of: 'Greenfield Library', "
                        "'Greenfield Arts Building', 'Greenfield Science Block'"
                    ),
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
                    "description": (
                        "One of: 'Greenfield Library', "
                        "'Greenfield Arts Building', 'Greenfield Science Block'"
                    ),
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
                    "description": (
                        "One of: 'Greenfield Library', "
                        "'Greenfield Arts Building', 'Greenfield Science Block'"
                    ),
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
    calculate_fn,
) -> dict[str, Any]:
    """
    Execute a named tool with given args.
    buildings, scenarios, calculate_fn are injected from the main app
    so this module stays decoupled from Streamlit.
    """
    temp = float(args.get("temperature_c", 10.5))
    weather = {"temperature_c": temp, "wind_speed_mph": 9.2}

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
        result = calculate_fn(buildings[bname], scenarios[sname], weather)
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
            r = calculate_fn(bdata, scenarios[sname], weather)
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
                r = calculate_fn(bdata, sdata, weather)
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
        baseline_carbon = round(b["baseline_energy_mwh"] * 1000 * 0.20482 / 1000, 1)
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
            "baseline_cost_gbp_yr":  round(b["baseline_energy_mwh"] * 1000 * 0.28, 0),
            "occupancy_hours_yr":    b["occupancy_hours"],
            "built_year":            b["built_year"],
            "description":           b["description"],
        }

    # ── Tool: rank_all_scenarios ──────────────────────────────────────────────
    elif name == "rank_all_scenarios":
        bname = args["building_name"]
        rank_by = args.get("rank_by", "cost_per_tonne")
        if bname not in buildings:
            return {"error": f"Building '{bname}' not found."}
        rows = []
        for sname, sdata in scenarios.items():
            r = calculate_fn(buildings[bname], sdata, weather)
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

    return {"error": f"Unknown tool: {name}"}


# ─────────────────────────────────────────────────────────────────────────────
# GEMINI API CALL
# ─────────────────────────────────────────────────────────────────────────────
def _call_gemini(api_key: str, messages: list, use_tools: bool = True) -> dict:
    """
    Single Gemini API call. Returns the raw response dict.
    messages format: [{"role": "user"|"model", "parts": [...]}]
    """
    payload: dict = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": messages,
        "generationConfig": {
            "maxOutputTokens": MAX_OUTPUT_TOKENS,
            "temperature": 0.2,   # low = consistent, factual answers
            "topP": 0.8,
        },
    }
    if use_tools:
        payload["tools"] = [{"function_declarations": TOOL_DECLARATIONS}]
        payload["tool_config"] = {
            "function_calling_config": {"mode": "AUTO"}
        }

    try:
        resp = requests.post(
            GEMINI_URL,
            params={"key": api_key},
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )
    except requests.exceptions.Timeout:
        return {"error": "Gemini API request timed out (30 s). Check your connection and retry."}
    except requests.exceptions.ConnectionError:
        return {"error": "Could not connect to Gemini API. Check your internet connection."}
    except requests.exceptions.RequestException as exc:
        return {"error": f"Gemini API request failed: {exc}"}

    if resp.status_code != 200:
        error_msg = "Unknown error"
        try:
            error_data = resp.json()
            error_msg = error_data.get('error', {}).get('message', resp.text[:200])
        except Exception:
            error_msg = resp.text[:200]
        
        # Enhanced error messages for common issues
        if "404" in str(resp.status_code) or "not found" in error_msg.lower():
            error_msg = (
                f"Model not available. Please ensure your API key is valid. "
                f"Error: {error_msg}"
            )
        elif "401" in str(resp.status_code) or "unauthorized" in error_msg.lower():
            error_msg = "Invalid API key. Please check and try again."
        elif "403" in str(resp.status_code) or "permission" in error_msg.lower():
            error_msg = "API key doesn't have permission. Check your Google Cloud Console."
        
        return {"error": f"Gemini API error {resp.status_code}: {error_msg}"}
    return resp.json()


# ─────────────────────────────────────────────────────────────────────────────
# AGENTIC LOOP
# Think → Call tools → Observe results → Think again → Final answer
# ─────────────────────────────────────────────────────────────────────────────
def run_agent(
    api_key: str,
    user_message: str,
    conversation_history: list,
    buildings: dict,
    scenarios: dict,
    calculate_fn,
    current_context: dict | None = None,
) -> dict:
    """
    Run the full agentic loop for one user turn.

    Returns:
        {
          "answer": str,           # final text response
          "tool_calls": list,      # list of {name, args, result} dicts
          "error": str | None,     # error message if something failed
          "loops": int,            # how many iterations the agent took
        }
    """
    # Build the working message list for this turn
    # Include conversation history + new user message
    messages = list(conversation_history)

    # Inject current dashboard context if provided
    ctx_text = ""
    if current_context:
        ctx_text = (
            f"\n\n[CURRENT DASHBOARD STATE]\n"
            f"Selected building: {current_context.get('building', 'unknown')}\n"
            f"Active scenarios: {current_context.get('scenarios', [])}\n"
            f"Current temperature: {current_context.get('temperature_c', 10.5)}°C\n"
        )

    messages.append({
        "role": "user",
        "parts": [{"text": user_message + ctx_text}]
    })

    tool_calls_log = []
    loops = 0

    while loops < MAX_AGENT_LOOPS:
        loops += 1
        response = _call_gemini(api_key, messages, use_tools=True)

        # Handle API error
        if "error" in response:
            return {
                "answer": None,
                "tool_calls": tool_calls_log,
                "error": response["error"],
                "loops": loops,
                "updated_history": messages,
            }

        candidates = response.get("candidates", [])
        if not candidates:
            return {
                "answer": "I couldn't generate a response. Please try again.",
                "tool_calls": tool_calls_log,
                "error": "No candidates in Gemini response",
                "loops": loops,
                "updated_history": messages,
            }

        content = candidates[0].get("content", {})
        parts   = content.get("parts", [])

        # Check for function calls in the response
        function_calls = [p for p in parts if "functionCall" in p]
        text_parts     = [p for p in parts if "text" in p]

        # ── If there are function calls → execute them ──
        if function_calls:
            # Add model's message (containing function calls) to history
            messages.append({"role": "model", "parts": parts})

            # Execute each function call and collect results
            function_results = []
            for fc_part in function_calls:
                fc   = fc_part["functionCall"]
                name = fc["name"]
                fargs = fc.get("args", {})

                # Execute the tool
                result = execute_tool(
                    name, fargs, buildings, scenarios, calculate_fn
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
                "role": "user",
                "parts": function_results,
            })
            # Loop continues — agent sees results and decides next step

        # ── If there's a text response → we're done ──
        elif text_parts:
            final_text = " ".join(p["text"] for p in text_parts if p.get("text"))
            # Add model's final response to history
            messages.append({"role": "model", "parts": parts})
            return {
                "answer": final_text.strip(),
                "tool_calls": tool_calls_log,
                "error": None,
                "loops": loops,
                "updated_history": messages,
            }

        else:
            # Unexpected response structure
            return {
                "answer": "I received an unexpected response. Please try again.",
                "tool_calls": tool_calls_log,
                "error": "No text or function_call in response parts",
                "loops": loops,
                "updated_history": messages,
            }

    # Hit max loops — ask Gemini to summarise what it found so far
    messages.append({
        "role": "user",
        "parts": [{"text": "Please summarise your findings so far in 3 sentences."}]
    })
    final_resp = _call_gemini(api_key, messages, use_tools=False)
    if "error" not in final_resp:
        parts = final_resp.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        text = " ".join(p.get("text", "") for p in parts)
        return {
            "answer": text.strip() or "Analysis complete — see tool results above.",
            "tool_calls": tool_calls_log,
            "error": None,
            "loops": loops,
            "updated_history": messages,
        }

    return {
        "answer": "Reached maximum reasoning steps. See tool results above.",
        "tool_calls": tool_calls_log,
        "error": None,
        "loops": loops,
        "updated_history": messages,
    }


# ─────────────────────────────────────────────────────────────────────────────
# SUGGESTED STARTER QUESTIONS
# Shown in the UI when conversation is empty
# ─────────────────────────────────────────────────────────────────────────────
STARTER_QUESTIONS = [
    "Which building should we upgrade first if we have £100,000?",
    "What's the fastest payback intervention across all buildings?",
    "How much CO₂ would a green roof save on the Science Block?",
    "Compare solar glass across all three buildings",
    "What's the cheapest way to reach a 30% carbon reduction?",
    "Explain the physics behind the insulation upgrade calculation",
    "Which single intervention gives the best cost per tonne of CO₂?",
    "If energy prices rise to £0.40/kWh, does that change the best option?",
]
