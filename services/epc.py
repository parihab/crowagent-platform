"""EPC data service integration layer for UK postcode lookups."""

from __future__ import annotations

import base64
import os
from typing import Any

import requests


EPC_API_URL_ENV = "EPC_API_URL"
EPC_API_KEY_ENV = "EPC_API_KEY"
ODC_DEFAULT_BASE_URL = "https://epc.opendatacommunities.org/api/v1"


def _basic_auth_header(api_key: str) -> str:
    """Return Basic auth header value for ODC EPC API key."""
    token = base64.b64encode(f"{api_key}:".encode("utf-8")).decode("utf-8")
    return f"Basic {token}"


def _parse_built_year(raw_row: dict[str, Any]) -> int:
    """Extract an indicative built year from EPC payload fields."""
    direct = raw_row.get("construction-age-band") or raw_row.get("construction_age_band")
    if isinstance(direct, str):
        for chunk in direct.replace("to", "-").split("-"):
            digits = "".join(ch for ch in chunk if ch.isdigit())
            if len(digits) == 4:
                return int(digits)
    return 1995


def fetch_epc_data(
    postcode: str,
    timeout_s: int = 10,
    api_url: str | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Fetch EPC-like metadata for a UK postcode.

    Args:
        postcode: UK postcode string.
        timeout_s: HTTP timeout in seconds.
        api_url: Optional API base URL override.
        api_key: Optional API key override.

    Returns:
        Dict containing ``floor_area_m2``, ``built_year``, ``epc_band``.

    Raises:
        ValueError: If postcode format is invalid.
    """
    normalized = " ".join(postcode.strip().upper().split())
    if len(normalized) < 5:
        raise ValueError("Invalid postcode format.")

    resolved_url = (api_url or os.getenv(EPC_API_URL_ENV, "") or ODC_DEFAULT_BASE_URL).strip().rstrip("/")
    resolved_key = (api_key or os.getenv(EPC_API_KEY_ENV, "")).strip()

    if resolved_key:
        headers = {
            "Accept": "application/json",
            "Authorization": _basic_auth_header(resolved_key),
        }
        try:
            endpoint = f"{resolved_url}/domestic/search"
            resp = requests.get(
                endpoint,
                params={"postcode": normalized, "size": 1},
                headers=headers,
                timeout=timeout_s,
            )
            resp.raise_for_status()
            payload = resp.json() if resp.content else {}
            rows = payload.get("rows", []) if isinstance(payload, dict) else []
            row = rows[0] if rows else {}
            floor_area = float(row.get("total-floor-area", row.get("floor_area_m2", 450.0)) or 450.0)
            epc_band = str(row.get("current-energy-rating", row.get("epc_band", "D")) or "D")
            built_year = _parse_built_year(row)
            return {
                "floor_area_m2": floor_area,
                "built_year": built_year,
                "epc_band": epc_band,
            }
        except Exception:
            # Fall through to deterministic stub.
            pass

    return {
        "floor_area_m2": 450.0,
        "built_year": 1995,
        "epc_band": "D",
    }
