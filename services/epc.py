"""EPC data service integration layer based on OpenAPI Specification.
Provides a production-safe accessor for EPC-like building metadata with a
network-backed path (when configured) and a deterministic stub fallback.
Endpoints utilized:

GET /api/v1/domestic/search
GET /api/v1/non-domestic/search
"""

from __future__ import annotations

import os
import re
from typing import Any

import requests
from requests import Response

EPC_API_URL_ENV = "EPC_API_URL"
EPC_API_KEY_ENV = "EPC_API_KEY"
EPC_USERNAME = "crowagent.platform@gmail.com"
VALID_EPC_BANDS = {"A", "B", "C", "D", "E", "F", "G"}


def _request_epc(url: str, postcode: str, api_key: str, timeout_s: int) -> Response:
    """Request an EPC endpoint using required auth and headers."""
    return requests.get(
        url,
        params={"postcode": postcode, "size": 1},
        headers={"Accept": "application/json"},
        auth=(EPC_USERNAME, api_key),
        timeout=timeout_s,
    )


def _parse_age_band(age_band: str) -> int:
    """Extract a representative year from a construction age band string."""
    if not age_band:
        return 1990
    matches = re.findall(r"\d{4}", age_band)
    if matches:
        return int(matches[-1])
    return 1990


def _to_float(value: Any, default: float) -> float:
    try:
        out = float(value)
        return out
    except (TypeError, ValueError):
        return default


def _normalize_band(raw: Any) -> str:
    band = str(raw or "Unknown").upper().replace("+", "").replace("-", "")
    return band if band in VALID_EPC_BANDS else "Unknown"


def _stub(reason: str) -> dict[str, Any]:
    return {
        "floor_area_m2": 150.0,
        "built_year": 1995,
        "epc_band": "D",
        "_is_stub": True,
        "_stub_reason": reason,
    }


def fetch_epc_data(postcode: str, timeout_s: int = 10) -> dict[str, Any]:
    """Fetch real EPC data for a UK postcode utilizing the OpenData API."""
    normalized = postcode.strip().upper()
    if len(normalized.replace(" ", "")) < 5:
        raise ValueError("Invalid postcode format.")

    base_url = os.getenv(EPC_API_URL_ENV, "https://epc.opendatacommunities.org/api/v1").rstrip("/")
    api_key = os.getenv(EPC_API_KEY_ENV, "").strip()
    if not api_key:
        return _stub("EPC API key not configured; using deterministic estimate.")

    endpoints = [
        f"{base_url}/domestic/search",
        f"{base_url}/non-domestic/search",
    ]
    had_transport_error = False

    for url in endpoints:
        is_domestic = "domestic/search" in url
        try:
            resp = _request_epc(url=url, postcode=normalized, api_key=api_key, timeout_s=timeout_s)
            resp.raise_for_status()
            payload = resp.json() if resp.content else {}

            # Backward-compatible support for direct normalized payloads in tests/mocks.
            if isinstance(payload, dict) and {"floor_area_m2", "built_year", "epc_band"}.issubset(payload):
                return {
                    "floor_area_m2": _to_float(payload.get("floor_area_m2"), 150.0),
                    "built_year": int(payload.get("built_year", 1990) or 1990),
                    "epc_band": _normalize_band(payload.get("epc_band")),
                    "_is_stub": False,
                    "_stub_reason": "",
                }

            rows = payload.get("rows", []) if isinstance(payload, dict) else []
            if not rows:
                continue

            data = rows[0] if isinstance(rows[0], dict) else {}
            if is_domestic:
                floor_area = _to_float(data.get("total-floor-area"), 150.0)
                built_year = _parse_age_band(str(data.get("construction-age-band", "")))
                epc_band = _normalize_band(data.get("current-energy-rating"))
            else:
                floor_area = _to_float(data.get("floor-area"), 150.0)
                built_year = 1990
                epc_band = _normalize_band(data.get("asset-rating-band"))

            return {
                "floor_area_m2": floor_area if floor_area > 0 else 150.0,
                "built_year": built_year,
                "epc_band": epc_band,
                "_is_stub": False,
                "_stub_reason": "",
            }
        except (requests.RequestException, ValueError, TypeError):
            had_transport_error = True
            continue

    if had_transport_error:
        return _stub("EPC API request failed; using deterministic estimate.")
    raise ValueError(f"No EPC records found for postcode: {postcode}")


def search_addresses(query: str, limit: int = 5, timeout_s: int = 8) -> list[dict[str, Any]]:
    """Search UK addresses for picker UX using Nominatim (fallback-safe)."""
    q = query.strip()
    if len(q) < 3:
        return []

    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": q, "countrycodes": "gb", "format": "jsonv2", "addressdetails": 1, "limit": limit},
            headers={"User-Agent": "CrowAgentPlatform/2.0"},
            timeout=timeout_s,
        )
        resp.raise_for_status()
        rows = resp.json() if resp.content else []
    except (requests.RequestException, ValueError, TypeError):
        return []

    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        disp = str(row.get("display_name", "")).strip()
        if not disp:
            continue
        address = row.get("address") if isinstance(row.get("address"), dict) else {}
        out.append(
            {
                "label": disp,
                "lat": _to_float(row.get("lat"), 0.0),
                "lon": _to_float(row.get("lon"), 0.0),
                "postcode": str(address.get("postcode", "")).upper().strip(),
            }
        )
    return out
