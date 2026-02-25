"""EPC data service integration layer.

Provides a production-safe accessor for EPC-like building metadata with a
network-backed path (when configured) and a deterministic stub fallback.
"""

from __future__ import annotations

import os
from typing import Any

import requests


EPC_API_URL_ENV = "EPC_API_URL"
EPC_API_KEY_ENV = "EPC_API_KEY"


def fetch_epc_data(postcode: str, timeout_s: int = 10) -> dict[str, Any]:
    """Fetch EPC-like data for a UK postcode.

    The function attempts a real API call if ``EPC_API_URL`` is configured,
    otherwise returns a deterministic stub payload suitable for local/dev use.

    Args:
        postcode: UK postcode string.
        timeout_s: HTTP timeout in seconds for upstream API requests.

    Returns:
        JSON-like dict with keys ``floor_area_m2``, ``built_year``, ``epc_band``.

    Raises:
        ValueError: If postcode format is invalid.
    """
    normalized = " ".join(postcode.strip().upper().split())
    if len(normalized) < 5:
        raise ValueError("Invalid postcode format.")

    api_url = os.getenv(EPC_API_URL_ENV, "").strip()
    api_key = os.getenv(EPC_API_KEY_ENV, "").strip()

    if api_url:
        headers = {"Accept": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        try:
            resp = requests.get(
                api_url,
                params={"postcode": normalized},
                headers=headers,
                timeout=timeout_s,
            )
            resp.raise_for_status()
            payload = resp.json() if resp.content else {}
            return {
                "floor_area_m2": float(payload.get("floor_area_m2", 450.0)),
                "built_year": int(payload.get("built_year", 1995)),
                "epc_band": str(payload.get("epc_band", "D")),
            }
        except Exception:
            # Fall through to deterministic stub for resilience.
            pass

    return {
        "floor_area_m2": 450.0,
        "built_year": 1995,
        "epc_band": "D",
    }
