"""EPC data service integration layer based on OpenAPI Specification.
Provides a production-safe accessor for EPC-like building metadata with a
network-backed path (when configured) and a deterministic stub fallback.
Endpoints utilized:

GET /api/v1/domestic/search
GET /api/v1/non-domestic/search
"""

from __future__ import annotations

import os
import logging
import re
from typing import Any
from urllib.parse import quote

import requests
from requests import Response

import streamlit as st

class EPCFetchError(RuntimeError):
    """Raised when EPC lookup fails and stub data cannot be generated."""


logger = logging.getLogger(__name__)

EPC_API_URL_ENV = "EPC_API_URL"
EPC_API_KEY_ENV = "EPC_API_KEY"
EPC_USERNAME_ENV = "EPC_USERNAME"
EPC_USERNAME_DEFAULT = ""
# Keep EPC_USERNAME for backward compatibility; call sites now read from env dynamically.
EPC_USERNAME = EPC_USERNAME_DEFAULT
EPC_STRICT_NO_RECORDS_ENV = "EPC_STRICT_NO_RECORDS"
VALID_EPC_BANDS = {"A", "B", "C", "D", "E", "F", "G"}
UK_POSTCODE_RE = re.compile(r"\b([A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2})\b", re.IGNORECASE)

# Open Data Soft EPC endpoint — free, no API key required
_ODS_EPC_BASE = "https://api.opendatasoft.com/api/explore/v2.1/catalog/datasets"
_ODS_EPC_DOMESTIC = f"{_ODS_EPC_BASE}/d-epc-domestic/records"
_ODS_NON_DOMESTIC = f"{_ODS_EPC_BASE}/d-epc-non-domestic/records"


def _get_epc_username() -> str:
    """Return the EPC API username, preferring the EPC_USERNAME env var."""
    return os.getenv(EPC_USERNAME_ENV, EPC_USERNAME_DEFAULT)


def _request_epc(url: str, postcode: str, api_key: str, timeout_s: int) -> Response:
    """Request an EPC endpoint using required auth and headers."""
    return requests.get(url, timeout=timeout_s,
        params={"postcode": postcode, "size": 1},
        headers={"Accept": "application/json"},
        auth=(_get_epc_username(), api_key),
    )


def _request_epc_search(url: str, postcode: str, api_key: str, limit: int, timeout_s: int) -> Response:
    """Search an EPC endpoint for address rows in a postcode."""
    return requests.get(url, timeout=timeout_s,
        params={"postcode": postcode, "size": max(1, min(limit, 50))},
        headers={"Accept": "application/json"},
        auth=(_get_epc_username(), api_key),
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


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_epc_data(
    postcode: str,
    timeout_s: int = 10,
    api_key: str | None = None,
    base_url: str | None = None,
) -> dict[str, Any]:
    """Fetch real EPC data for a UK postcode utilizing the OpenData API."""
    normalized = postcode.strip().upper()
    if len(normalized.replace(" ", "")) < 5:
        raise ValueError("Invalid postcode format.")

    strict_no_records = os.getenv(EPC_STRICT_NO_RECORDS_ENV, "").strip().lower() in {"1", "true", "yes"}

    final_base_url = (base_url or os.getenv(EPC_API_URL_ENV, "https://epc.opendatacommunities.org/api/v1")).rstrip("/")
    final_api_key = api_key or os.getenv(EPC_API_KEY_ENV, "")
    if not final_api_key:
        return _stub("EPC API key not configured; using deterministic estimate.")

    endpoints = [
        f"{final_base_url}/domestic/search",
        f"{final_base_url}/non-domestic/search",
    ]
    had_transport_error = False

    for url in endpoints:
        is_domestic = "domestic/search" in url
        try:
            resp = _request_epc(url=url, postcode=normalized, api_key=final_api_key, timeout_s=timeout_s)
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
        except (requests.RequestException, ValueError, TypeError) as e:
            logger.warning("EPC API fetch failed for %s: %s", url, e)
            had_transport_error = True
            continue

    if had_transport_error and not strict_no_records:
        return _stub("EPC API request failed; using deterministic estimate.")

    if strict_no_records:
        raise EPCFetchError(f"No EPC records found for postcode: {postcode}")
    return _stub(f"No EPC records found for postcode: {postcode}; using deterministic estimate.")


def search_addresses(postcode: str) -> list[dict]:
    """
    Search for addresses at a UK postcode.
    Returns list of dicts: {address, postcode, source,
                            floor_area_m2, epc_rating,
                            built_year, property_type}

    Attempt order:
    1. UK EPC Open Data API (api.opendatasoft.com) — free, no key
    2. Nominatim OSM geocoding as address fallback
    3. If both fail: return generate_stub_addresses(postcode)

    Wraps ALL network calls in try/except.
    Timeout: 6 seconds for EPC, 5 seconds for Nominatim.
    Never raises. Always returns a list (may be stubs).
    """
    normalized = _normalize_postcode(str(postcode or "").strip())
    if not normalized:
        return []

    # ── Attempt 1: opendatasoft.com EPC open dataset (no key required) ────────
    try:
        results = _search_ods_epc(normalized, timeout_s=6)
        if results:
            return results
    except Exception:
        pass

    # ── Attempt 2: Nominatim OSM geocoding ────────────────────────────────────
    try:
        results = _search_nominatim(normalized, timeout_s=5)
        if results:
            return results
    except Exception:
        pass

    # ── Attempt 3: Stub fallback ───────────────────────────────────────────────
    return generate_stub_addresses(normalized)


def _search_ods_epc(postcode: str, timeout_s: int = 6) -> list[dict]:
    """
    Query the opendatasoft.com EPC open datasets for addresses in a postcode.
    Returns list of address dicts or empty list on failure.
    """
    out: list[dict] = []
    seen: set[str] = set()

    for endpoint in (_ODS_EPC_DOMESTIC, _ODS_NON_DOMESTIC):
        try:
            resp = requests.get(
                endpoint,
                timeout=timeout_s,
                params={
                    "where": f'postcode="{postcode}"',
                    "limit": 10,
                    "select": (
                        "address1,address2,address3,postcode,"
                        "current_energy_rating,total_floor_area,"
                        "construction_age_band,property_type,"
                        "uprn,latitude,longitude"
                    ),
                },
                headers={"Accept": "application/json"},
            )
            resp.raise_for_status()
            payload = resp.json() if resp.content else {}
            records = payload.get("results", []) if isinstance(payload, dict) else []

            for rec in records:
                if not isinstance(rec, dict):
                    continue
                parts = [
                    str(rec.get("address1") or "").strip(),
                    str(rec.get("address2") or "").strip(),
                    str(rec.get("address3") or "").strip(),
                    str(rec.get("postcode") or postcode).strip().upper(),
                ]
                address = ", ".join(p for p in parts if p)
                if not address or address in seen:
                    continue
                seen.add(address)

                epc_rating = _normalize_band(rec.get("current_energy_rating"))
                if epc_rating == "Unknown":
                    epc_rating = None

                floor_area = None
                raw_fa = rec.get("total_floor_area")
                if raw_fa is not None:
                    try:
                        v = float(raw_fa)
                        floor_area = v if v > 0 else None
                    except (TypeError, ValueError):
                        floor_area = None

                built_year = None
                raw_age = rec.get("construction_age_band")
                if raw_age:
                    built_year = _parse_age_band(str(raw_age))

                out.append({
                    "address": address,
                    "postcode": _normalize_postcode(str(rec.get("postcode") or postcode)),
                    "source": "epc_opendata",
                    "floor_area_m2": floor_area,
                    "epc_rating": epc_rating,
                    "built_year": built_year,
                    "property_type": str(rec.get("property_type") or "").strip() or None,
                    "uprn": str(rec.get("uprn") or "").strip() or None,
                    "latitude": _to_float(rec.get("latitude"), None),
                    "longitude": _to_float(rec.get("longitude"), None),
                })
                if len(out) >= 8:
                    return out
        except (requests.Timeout, requests.ConnectionError, Exception):
            continue

    return out


def _search_nominatim(postcode: str, timeout_s: int = 5) -> list[dict]:
    """
    Use Nominatim OSM geocoding as an address fallback.
    Returns list of address dicts or empty list on failure.
    """
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            timeout=timeout_s,
            params={
                "q": postcode,
                "countrycodes": "gb",
                "format": "jsonv2",
                "addressdetails": 1,
                "limit": 6,
            },
            headers={"User-Agent": "CrowAgentPlatform/2.0"},
        )
        resp.raise_for_status()
        rows = resp.json() if resp.content else []
    except (requests.Timeout, requests.ConnectionError, Exception):
        return []

    out: list[dict] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        disp = str(row.get("display_name", "")).strip()
        if not disp:
            continue
        address_detail = row.get("address") if isinstance(row.get("address"), dict) else {}
        pc = _normalize_postcode(str(address_detail.get("postcode", "") or postcode))
        out.append({
            "address": disp,
            "postcode": pc or postcode,
            "source": "nominatim",
            "floor_area_m2": None,
            "epc_rating": None,
            "built_year": None,
            "property_type": None,
            "uprn": None,
            "latitude": _to_float(row.get("lat"), None),
            "longitude": _to_float(row.get("lon"), None),
        })
    return out


def generate_stub_addresses(postcode: str) -> list[dict]:
    """
    Generate 6 realistic stub addresses from a postcode.
    Used when all APIs fail. Mark source="manual_entry".
    Names are derived intelligently from the postcode area.
    Returns with floor_area_m2=None, epc_rating=None,
    built_year=None, property_type=None so the UI knows
    to show the manual entry form for these fields.
    """
    pc = str(postcode or "").strip().upper()
    # Extract area prefix (e.g. "RG1" from "RG1 6SP")
    area = pc.split(" ")[0] if " " in pc else pc[:3]
    # Derive a plausible town name from common UK area codes
    _AREA_TOWNS: dict[str, str] = {
        "RG": "Reading", "OX": "Oxford", "GU": "Guildford",
        "SL": "Slough", "HP": "Hemel Hempstead", "MK": "Milton Keynes",
        "SW": "London", "SE": "London", "EC": "London", "WC": "London",
        "N": "London", "E": "London", "W": "London", "NW": "London",
        "B": "Birmingham", "M": "Manchester", "L": "Liverpool",
        "LS": "Leeds", "BS": "Bristol", "EH": "Edinburgh", "CF": "Cardiff",
    }
    prefix = re.match(r"^([A-Z]{1,2})", area)
    prefix_str = prefix.group(1) if prefix else ""
    town = _AREA_TOWNS.get(prefix_str, _AREA_TOWNS.get(prefix_str[:1], ""))
    town = town or f"{area} Area"

    stubs = [
        f"Unit 1, {area} Business Centre, {town}",
        f"12 Station Road, {town}, {pc}",
        f"Ground Floor, Apex House, {town}, {area}",
        f"{area} Enterprise Park — Building A",
        f"4 Commerce Way, {town}, {pc}",
        f"Riverside House, {town}, {area}",
    ]

    return [
        {
            "address": addr,
            "postcode": pc,
            "source": "manual_entry",
            "floor_area_m2": None,
            "epc_rating": None,
            "built_year": None,
            "property_type": None,
            "uprn": None,
            "latitude": None,
            "longitude": None,
        }
        for addr in stubs
    ]


def get_epc_details(uprn: str) -> dict | None:
    """
    Fetch detailed EPC record for a UPRN from the EPC API.
    Returns dict with epc_rating, floor_area_m2, built_year,
    property_type, or None on failure.
    """
    if not uprn:
        return None

    api_key = os.getenv(EPC_API_KEY_ENV, "")
    base_url = os.getenv(EPC_API_URL_ENV, "https://epc.opendatacommunities.org/api/v1").rstrip("/")

    endpoints = [
        f"{base_url}/domestic/search",
        f"{base_url}/non-domestic/search",
    ]

    for url in endpoints:
        is_domestic = "domestic/search" in url
        try:
            auth = (_get_epc_username(), api_key) if api_key else None
            resp = requests.get(
                url,
                timeout=8,
                params={"uprn": uprn, "size": 1},
                headers={"Accept": "application/json"},
                auth=auth,
            )
            resp.raise_for_status()
            payload = resp.json() if resp.content else {}
            rows = payload.get("rows", []) if isinstance(payload, dict) else []
            if not rows:
                continue
            data = rows[0] if isinstance(rows[0], dict) else {}
            if is_domestic:
                return {
                    "epc_rating": _normalize_band(data.get("current-energy-rating")),
                    "floor_area_m2": _to_float(data.get("total-floor-area"), 150.0) or None,
                    "built_year": _parse_age_band(str(data.get("construction-age-band", ""))),
                    "property_type": str(data.get("property-type", "")).strip() or None,
                }
            else:
                return {
                    "epc_rating": _normalize_band(data.get("asset-rating-band")),
                    "floor_area_m2": _to_float(data.get("floor-area"), 150.0) or None,
                    "built_year": None,
                    "property_type": str(data.get("property-type", "")).strip() or None,
                }
        except (requests.Timeout, requests.ConnectionError, Exception):
            continue

    # Try opendatasoft as fallback (no key required)
    try:
        resp = requests.get(
            _ODS_EPC_DOMESTIC,
            timeout=6,
            params={
                "where": f'uprn="{uprn}"',
                "limit": 1,
                "select": "current_energy_rating,total_floor_area,construction_age_band,property_type",
            },
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        payload = resp.json() if resp.content else {}
        records = payload.get("results", []) if isinstance(payload, dict) else []
        if records and isinstance(records[0], dict):
            rec = records[0]
            epc_rating = _normalize_band(rec.get("current_energy_rating"))
            floor_area = _to_float(rec.get("total_floor_area"), 0.0) or None
            built_year = _parse_age_band(str(rec.get("construction_age_band") or ""))
            return {
                "epc_rating": epc_rating if epc_rating != "Unknown" else None,
                "floor_area_m2": floor_area,
                "built_year": built_year or None,
                "property_type": str(rec.get("property_type") or "").strip() or None,
            }
    except (requests.Timeout, requests.ConnectionError, Exception):
        pass

    return None
