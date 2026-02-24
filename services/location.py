# ═══════════════════════════════════════════════════════════════════════════════
# CrowAgent™ Platform — Location Management Module
# © 2026 Aparajita Parihar. All rights reserved.
#
# Provides:
#   • Curated city/region database with lat/lon coordinates
#   • Browser geolocation JS component (HTTPS only; requires user consent)
#   • Nearest-city resolver (Haversine) for GDPR-compliant coord→city mapping
#
# GDPR NOTE: Raw browser coordinates are never persisted. The geolocation
# flow resolves immediately to the nearest city name and discards raw coords.
# ═══════════════════════════════════════════════════════════════════════════════

from __future__ import annotations
import math
import streamlit.components.v1 as components

# ─────────────────────────────────────────────────────────────────────────────
# CITY DATABASE
# ~60 cities; UK-weighted for Net Zero / Part L use cases.
# mo_id = Met Office DataPoint site ID (UK cities where known).
# ─────────────────────────────────────────────────────────────────────────────
CITIES: dict[str, dict] = {
    # UK — South East & East
    "Reading, Berkshire":   {"lat": 51.4543, "lon": -0.9781, "country": "UK", "mo_id": "354230"},
    "London":               {"lat": 51.5074, "lon": -0.1278, "country": "UK", "mo_id": "310012"},
    "Brighton":             {"lat": 50.8225, "lon": -0.1372, "country": "UK", "mo_id": "310021"},
    "Southampton":          {"lat": 50.9097, "lon": -1.4044, "country": "UK", "mo_id": "310066"},
    "Portsmouth":           {"lat": 50.8198, "lon": -1.0880, "country": "UK"},
    "Oxford":               {"lat": 51.7520, "lon": -1.2577, "country": "UK"},
    "Cambridge":            {"lat": 52.2053, "lon":  0.1218, "country": "UK"},
    "Norwich":              {"lat": 52.6309, "lon":  1.2974, "country": "UK"},
    # UK — Midlands
    "Birmingham":           {"lat": 52.4862, "lon": -1.8904, "country": "UK", "mo_id": "310088"},
    "Coventry":             {"lat": 52.4068, "lon": -1.5197, "country": "UK"},
    "Leicester":            {"lat": 52.6369, "lon": -1.1398, "country": "UK"},
    "Nottingham":           {"lat": 52.9548, "lon": -1.1581, "country": "UK"},
    "Derby":                {"lat": 52.9225, "lon": -1.4746, "country": "UK"},
    # UK — North West & Yorkshire
    "Manchester":           {"lat": 53.4808, "lon": -2.2426, "country": "UK", "mo_id": "310120"},
    "Leeds":                {"lat": 53.8008, "lon": -1.5491, "country": "UK", "mo_id": "322049"},
    "Sheffield":            {"lat": 53.3811, "lon": -1.4701, "country": "UK"},
    "Liverpool":            {"lat": 53.4084, "lon": -2.9916, "country": "UK", "mo_id": "310105"},
    "Bradford":             {"lat": 53.7960, "lon": -1.7594, "country": "UK"},
    # UK — North East & Cumbria
    "Newcastle upon Tyne":  {"lat": 54.9783, "lon": -1.6178, "country": "UK"},
    "Sunderland":           {"lat": 54.9069, "lon": -1.3838, "country": "UK"},
    # UK — Scotland
    "Edinburgh":            {"lat": 55.9533, "lon": -3.1883, "country": "UK", "mo_id": "351490"},
    "Glasgow":              {"lat": 55.8642, "lon": -4.2518, "country": "UK", "mo_id": "310141"},
    "Aberdeen":             {"lat": 57.1497, "lon": -2.0943, "country": "UK"},
    "Dundee":               {"lat": 56.4620, "lon": -2.9707, "country": "UK"},
    # UK — Wales & Northern Ireland
    "Cardiff":              {"lat": 51.4816, "lon": -3.1791, "country": "UK"},
    "Swansea":              {"lat": 51.6214, "lon": -3.9436, "country": "UK"},
    "Belfast":              {"lat": 54.5973, "lon": -5.9301, "country": "UK"},
    # European
    "Paris":                {"lat": 48.8566, "lon":  2.3522, "country": "France"},
    "Berlin":               {"lat": 52.5200, "lon": 13.4050, "country": "Germany"},
    "Hamburg":              {"lat": 53.5753, "lon": 10.0153, "country": "Germany"},
    "Munich":               {"lat": 48.1351, "lon": 11.5820, "country": "Germany"},
    "Amsterdam":            {"lat": 52.3676, "lon":  4.9041, "country": "Netherlands"},
    "Brussels":             {"lat": 50.8503, "lon":  4.3517, "country": "Belgium"},
    "Madrid":               {"lat": 40.4168, "lon": -3.7038, "country": "Spain"},
    "Barcelona":            {"lat": 41.3851, "lon":  2.1734, "country": "Spain"},
    "Rome":                 {"lat": 41.9028, "lon": 12.4964, "country": "Italy"},
    "Milan":                {"lat": 45.4642, "lon":  9.1900, "country": "Italy"},
    "Stockholm":            {"lat": 59.3293, "lon": 18.0686, "country": "Sweden"},
    "Oslo":                 {"lat": 59.9139, "lon": 10.7522, "country": "Norway"},
    "Copenhagen":           {"lat": 55.6761, "lon": 12.5683, "country": "Denmark"},
    "Helsinki":             {"lat": 60.1699, "lon": 24.9384, "country": "Finland"},
    "Zurich":               {"lat": 47.3769, "lon":  8.5417, "country": "Switzerland"},
    "Vienna":               {"lat": 48.2082, "lon": 16.3738, "country": "Austria"},
    "Warsaw":               {"lat": 52.2297, "lon": 21.0122, "country": "Poland"},
    "Prague":               {"lat": 50.0755, "lon": 14.4378, "country": "Czechia"},
    "Lisbon":               {"lat": 38.7169, "lon": -9.1399, "country": "Portugal"},
    # Global
    "New York":             {"lat": 40.7128, "lon": -74.0060, "country": "USA"},
    "Chicago":              {"lat": 41.8781, "lon": -87.6298, "country": "USA"},
    "Los Angeles":          {"lat": 34.0522, "lon": -118.2437, "country": "USA"},
    "Toronto":              {"lat": 43.6532, "lon": -79.3832, "country": "Canada"},
    "Dubai":                {"lat": 25.2048, "lon": 55.2708,  "country": "UAE"},
    "Mumbai":               {"lat": 19.0760, "lon": 72.8777,  "country": "India"},
    "Singapore":            {"lat":  1.3521, "lon": 103.8198, "country": "Singapore"},
    "Hong Kong":            {"lat": 22.3193, "lon": 114.1694, "country": "Hong Kong"},
    "Tokyo":                {"lat": 35.6762, "lon": 139.6503, "country": "Japan"},
    "Sydney":               {"lat": -33.8688, "lon": 151.2093, "country": "Australia"},
    "Melbourne":            {"lat": -37.8136, "lon": 144.9631, "country": "Australia"},
}

# Ordered groups for a clean grouped display in the UI
CITY_GROUPS: list[tuple[str, list[str]]] = [
    ("UK — South East & East", [
        "Reading, Berkshire", "London", "Brighton", "Southampton",
        "Portsmouth", "Oxford", "Cambridge", "Norwich",
    ]),
    ("UK — Midlands", [
        "Birmingham", "Coventry", "Leicester", "Nottingham", "Derby",
    ]),
    ("UK — North West & Yorkshire", [
        "Manchester", "Leeds", "Sheffield", "Liverpool", "Bradford",
    ]),
    ("UK — North East & Scotland", [
        "Newcastle upon Tyne", "Sunderland", "Edinburgh", "Glasgow",
        "Aberdeen", "Dundee",
    ]),
    ("UK — Wales & Northern Ireland", [
        "Cardiff", "Swansea", "Belfast",
    ]),
    ("Europe", [
        "Paris", "Berlin", "Hamburg", "Munich", "Amsterdam", "Brussels",
        "Madrid", "Barcelona", "Rome", "Milan", "Stockholm", "Oslo",
        "Copenhagen", "Helsinki", "Zurich", "Vienna", "Warsaw", "Prague", "Lisbon",
    ]),
    ("Global", [
        "New York", "Chicago", "Los Angeles", "Toronto",
        "Dubai", "Mumbai", "Singapore", "Hong Kong", "Tokyo",
        "Sydney", "Melbourne",
    ]),
]


def city_options() -> list[str]:
    """Flat ordered list of all city keys, grouped for visual clarity in selectbox."""
    result: list[str] = []
    for _, cities in CITY_GROUPS:
        result.extend(cities)
    return result


def city_meta(city_key: str) -> dict:
    """Return metadata dict for a city key. Raises KeyError if not found."""
    return CITIES[city_key]


def nearest_city(lat: float, lon: float) -> str:
    """
    Return the city key nearest to (lat, lon) using the Haversine formula.
    Used to resolve browser geolocation coordinates to a city/region label.

    GDPR: raw coordinates are discarded after this call; only the city name
    is stored in session state, resolving to a city/region resolution.
    """
    def _haversine(la1: float, lo1: float, la2: float, lo2: float) -> float:
        R = 6_371.0
        dlat = math.radians(la2 - la1)
        dlon = math.radians(lo2 - lo1)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(la1))
            * math.cos(math.radians(la2))
            * math.sin(dlon / 2) ** 2
        )
        return R * 2 * math.asin(math.sqrt(a))

    return min(
        CITIES,
        key=lambda c: _haversine(lat, lon, CITIES[c]["lat"], CITIES[c]["lon"]),
    )


# ─────────────────────────────────────────────────────────────────────────────
# BROWSER GEOLOCATION COMPONENT
#
# Renders a button that invokes navigator.geolocation.getCurrentPosition().
# On success, appends ?geo_lat=X&geo_lon=Y to the parent page URL, causing
# Streamlit to re-run with those query params available via st.query_params.
#
# Requirements:
#   • HTTPS deployment (geolocation blocked on plain HTTP by browsers)
#   • User must grant the browser permission prompt
#   • Component is embedded in a same-origin iframe via st.components.v1.html
# ─────────────────────────────────────────────────────────────────────────────
_GEO_HTML = """\
<style>
  body { margin:0; background:transparent; font-family:'Segoe UI',sans-serif; }
  #geo-btn {
    background:#0D2640; border:1px solid #00C2A8; color:#00C2A8;
    font-size:0.82rem; font-weight:600; padding:5px 14px; border-radius:4px;
    cursor:pointer; width:100%; box-sizing:border-box; letter-spacing:0.3px;
  }
  #geo-btn:hover:not(:disabled) { background:#00C2A8; color:#071A2F; }
  #geo-btn:disabled { opacity:0.6; cursor:default; }
  #geo-status { font-size:0.73rem; color:#8FBCCE; margin-top:5px; line-height:1.45; }
</style>
<button id="geo-btn" onclick="detectLocation()">&#128205; Detect My Location</button>
<div id="geo-status">Requires browser permission &mdash; HTTPS only</div>
<script>
function detectLocation() {
  var btn    = document.getElementById('geo-btn');
  var status = document.getElementById('geo-status');
  if (!navigator.geolocation) {
    status.innerHTML = '&#9888; Geolocation not supported in this browser.';
    return;
  }
  btn.disabled = true;
  btn.textContent = '\u23f3 Detecting\u2026';
  status.innerHTML = 'Waiting for browser permission\u2026';
  navigator.geolocation.getCurrentPosition(
    function(pos) {
      var lat = pos.coords.latitude.toFixed(4);
      var lon = pos.coords.longitude.toFixed(4);
      status.innerHTML = '\u2713 Located: ' + lat + ', ' + lon + ' \u2014 loading\u2026';

      // Try to update the parent URL so that a refresh preserves the choice.
      // If this fails we still send the coords back to Python below.
      try {
        var url = new URL(window.parent.location.href);
        url.searchParams.set('geo_lat', lat);
        url.searchParams.set('geo_lon', lon);
        window.parent.location.href = url.toString();
      } catch(e) {
        status.innerHTML = '\u26a0 Cannot auto-update. Coordinates: ' + lat + ', ' + lon
          + '<br/>Enter them manually below.';
        btn.disabled = false;
        // use HTML entity for pushpin to avoid Python surrogate issues
        btn.textContent = '📍 Detect My Location';
      }

      // always notify Streamlit of the coordinates so Python can handle them
      try {
        const Streamlit = window.parent.Streamlit || window.parent.streamlit;
        Streamlit.setComponentValue({lat: lat, lon: lon});
      } catch(_ignored) {
        // gracefully ignore if API isn't available
      }
    },
    function(err) {
      var msgs = {1:'Permission denied',2:'Position unavailable',3:'Request timed out'};
      status.innerHTML = '\u274c ' + (msgs[err.code] || err.message)
                        + ' (try again or enter coords manually)';
      btn.disabled = false;
      btn.textContent = '📍 Detect My Location';
    },
    { timeout: 20000, maximumAge: 300000 }
  );
}
</script>
"""


def render_geo_detect() -> any:
    """Embed the browser geolocation button as a Streamlit HTML component.

    The HTML/JS snippet will call ``Streamlit.setComponentValue`` with a
    dictionary containing ``lat``/``lon`` once the browser has successfully
    obtained a position.  The return value from ``components.html`` is
    propagated back to the caller, allowing the main app to react without
    relying solely on query parameters.
    """
    return components.html(_GEO_HTML, height=68)
