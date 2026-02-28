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
from urllib.parse import quote

import requests
from requests import Response

EPC_API_URL_ENV = "EPC_API_URL"
EPC_API_KEY_ENV = "EPC_API_KEY"
EPC_USERNAME_ENV = "EPC_USERNAME"
EPC_USERNAME_DEFAULT = "crowagent.platform@gmail.com"
# Keep EPC_USERNAME for backward compatibility; call sites now read from env dynamically.
EPC_USERNAME = EPC_USERNAME_DEFAULT
EPC_STRICT_NO_RECORDS_ENV = "EPC_STRICT_NO_RECORDS"
VALID_EPC_BANDS = {"A", "B", "C", "D", "E", "F", "G"}
UK_POSTCODE_RE = re.compile(r"\b([A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2})\b", re.IGNORECASE)


def _get_epc_username() -> str:
    """Return the EPC API username, preferring the EPC_USERNAME env var."""
    return os.getenv(EPC_USERNAME_ENV, EPC_USERNAME_DEFAULT)


def _request_epc(url: str, postcode: str, api_key: str, timeout_s: int) -> Response:
    """Request an EPC endpoint using required auth and headers."""
    return requests.get(
        url,
        params={"postcode": postcode, "size": 1},
        headers={"Accept": "application/json"},
        auth=(_get_epc_username(), api_key),
        timeout=timeout_s,
    )


def _request_epc_search(url: str, postcode: str, api_key: str, limit: int, timeout_s: int) -> Response:
    """Search an EPC endpoint for address rows in a postcode."""
    return requests.get(
        url,
        params={"postcode": postcode, "size": max(1, min(limit, 50))},
        headers={"Accept": "application/json"},
        auth=(_get_epc_username(), api_key),
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


def _normalize_postcode(value: str) -> str:
    cleaned = str(value or "").strip().upper()
    match = UK_POSTCODE_RE.search(cleaned)
    if not match:
        return ""
    compact = re.sub(r"\s+", "", match.group(1).upper())
    if len(compact) < 5:
        return ""
    return f"{compact[:-3]} {compact[-3:]}"


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

    strict_no_records = os.getenv(EPC_STRICT_NO_RECORDS_ENV, "").strip().lower() in {"1", "true", "yes"}
    if strict_no_records:
        raise ValueError(f"No EPC records found for postcode: {postcode}")
    return _stub(f"No EPC records found for postcode: {postcode}; using deterministic estimate.")


def search_addresses(query: str, limit: int = 5, timeout_s: int = 8) -> list[dict[str, Any]]:
    """Search UK addresses for picker UX via EPC API with resilient fallbacks."""
    q = str(query or "").strip()
    postcode = _normalize_postcode(q)
    if not postcode:
        return []

    out: list[dict[str, Any]] = []
    seen_labels: set[str] = set()

    api_key = os.getenv(EPC_API_KEY_ENV, "").strip()
    base_url = os.getenv(EPC_API_URL_ENV, "https://epc.opendatacommunities.org/api/v1").rstrip("/")

    if api_key:
        for endpoint in ("domestic/search", "non-domestic/search"):
            try:
                resp = _request_epc_search(
                    url=f"{base_url}/{endpoint}",
                    postcode=postcode,
                    api_key=api_key,
                    limit=limit,
                    timeout_s=timeout_s,
                )
                resp.raise_for_status()
                rows = (resp.json() or {}).get("rows", []) if resp.content else []
            except (requests.RequestException, ValueError, TypeError, AttributeError):
                continue

            for row in rows:
                if not isinstance(row, dict):
                    continue
                parts = [
                    str(row.get("address") or "").strip(),
                    str(row.get("address1") or "").strip(),
                    str(row.get("address2") or "").strip(),
                    str(row.get("address3") or "").strip(),
                    str(row.get("postcode") or postcode).strip().upper(),
                ]
                label = ", ".join([p for p in parts if p])
                if not label:
                    continue
                if label in seen_labels:
                    continue
                seen_labels.add(label)
                out.append(
                    {
                        "label": label,
                        "lat": _to_float(row.get("latitude"), None),
                        "lon": _to_float(row.get("longitude"), None),
                        "postcode": _normalize_postcode(str(row.get("postcode") or postcode)),
                    }
                )
                if len(out) >= limit:
                    return out

    if out:
        return out

    # Fallback for environments without EPC key or empty EPC results.
    # findthatpostcode often resolves full UK postcode metadata quickly.
    try:
        encoded_pc = quote(postcode.replace(" ", ""))
        resp = requests.get(
            f"https://findthatpostcode.uk/postcodes/{encoded_pc}.json",
            timeout=timeout_s,
        )
        resp.raise_for_status()
        payload = resp.json() if resp.content else {}
        data = payload.get("data") if isinstance(payload, dict) else {}
        result_postcode = _normalize_postcode(str((data or {}).get("postcode") or postcode))
        if result_postcode:
            return [
                {
                    "label": f"{result_postcode}, UK",
                    "lat": _to_float((data or {}).get("lat"), None),
                    "lon": _to_float((data or {}).get("lon"), None),
                    "postcode": result_postcode,
                }
            ]
    except (requests.RequestException, ValueError, TypeError, AttributeError):
        pass

    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": postcode, "countrycodes": "gb", "format": "jsonv2", "addressdetails": 1, "limit": limit},
            headers={"User-Agent": "CrowAgentPlatform/2.0"},
            timeout=timeout_s,
        )
        resp.raise_for_status()
        rows = resp.json() if resp.content else []
    except (requests.RequestException, ValueError, TypeError):
        return []

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
                "lat": _to_float(row.get("lat"), None),
                "lon": _to_float(row.get("lon"), None),
                "postcode": _normalize_postcode(str(address.get("postcode", "") or postcode)),
            }
        )
    return out
