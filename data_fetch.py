# data_fetch.py (OpenAQ v3)
import os
import time
import requests
import pandas as pd
from typing import Optional, Tuple, Dict, Any
from dotenv import load_dotenv

load_dotenv()
API_BASE = "https://api.openaq.org/v3"
API_KEY = os.getenv("OPENAQ_API_KEY", "").strip()

def _headers():
    if not API_KEY:
        # Still return a header object – the app will surface a helpful error
        return {}
    return {"X-API-Key": API_KEY}

def _empty_df() -> pd.DataFrame:
    return pd.DataFrame(columns=["datetime","value","unit","location","latitude","longitude","sensor_id","location_id"])

def fetch_locations_by_city(country_iso: Optional[str], city_like: str, parameter_name: str, limit: int = 100) -> Tuple[pd.DataFrame, Optional[str]]:
    """
    v3 has no direct ?city= filter. We:
    1) call /v3/locations with iso=XX (optional),
    2) client-filter results where 'locality' OR 'name' contains city_like (case-insensitive),
    3) keep only locations that have sensors for parameter_name.
    """
    if not API_KEY:
        return _empty_df(), "Missing OpenAQ API key. Set OPENAQ_API_KEY in .env."

    params: Dict[str, Any] = {
        "limit": limit
    }
    if country_iso:
        params["iso"] = country_iso

    try:
        r = requests.get(f"{API_BASE}/locations", params=params, headers=_headers(), timeout=30)
        if r.status_code != 200:
            return _empty_df(), f"/locations {r.status_code}: {r.text[:240]}"
        data = r.json()
    except requests.RequestException as e:
        return _empty_df(), f"Network error: {e}"

    locs = []
    city_like_low = (city_like or "").lower()
    for loc in data.get("results", []):
        locality = (loc.get("locality") or "").lower()
        name = (loc.get("name") or "").lower()
        sensors = loc.get("sensors") or []
        has_param = any((s.get("parameter", {}).get("name") == parameter_name) for s in sensors)
        if (city_like_low in locality or city_like_low in name) and has_param:
            locs.append({
                "location_id": loc.get("id"),
                "location_name": loc.get("name"),
                "locality": loc.get("locality"),
                "country": (loc.get("country") or {}).get("code"),
                "timezone": loc.get("timezone"),
                "sensors": sensors
            })

    if not locs:
        return _empty_df(), "No matching locations with that city + parameter. Try adjusting city text or country ISO."

    return pd.DataFrame(locs), None

def fetch_sensors_for_location(location_id: int, parameter_name: str) -> Tuple[pd.DataFrame, Optional[str]]:
    """
    v3: list sensors under a location, filter by parameter name (e.g., 'pm25').
    """
    if not API_KEY:
        return _empty_df(), "Missing OpenAQ API key. Set OPENAQ_API_KEY in .env."

    try:
        # docs: GET /v3/locations/{locations_id}/sensors
        r = requests.get(f"{API_BASE}/locations/{location_id}/sensors", headers=_headers(), timeout=30)
        if r.status_code != 200:
            return _empty_df(), f"/locations/{location_id}/sensors {r.status_code}: {r.text[:240]}"
        data = r.json()
    except requests.RequestException as e:
        return _empty_df(), f"Network error: {e}"

    rows = []
    for s in data.get("results", []):
        param = (s.get("parameter") or {}).get("name")
        if param == parameter_name:
            rows.append({
                "sensor_id": s.get("id"),
                "parameter": param,
                "units": (s.get("parameter") or {}).get("units"),
                "location_id": s.get("location", {}).get("id")
            })

    if not rows:
        return _empty_df(), "No sensors for that parameter at this location."
    return pd.DataFrame(rows), None

def fetch_daily_for_sensor(sensor_id: int, date_from: str, date_to: str) -> Tuple[pd.DataFrame, Optional[str]]:
    """
    v3 daily averages for one sensor:
    GET /v3/sensors/{sensor_id}/days?datetime_from=...&datetime_to=...
    """
    if not API_KEY:
        return _empty_df(), "Missing OpenAQ API key. Set OPENAQ_API_KEY in .env."

    params = {
        "datetime_from": f"{date_from}T00:00:00Z",
        "datetime_to":   f"{date_to}T23:59:59Z",
        "limit": 1000
    }
    try:
        r = requests.get(f"{API_BASE}/sensors/{sensor_id}/days", params=params, headers=_headers(), timeout=30)
        if r.status_code != 200:
            return _empty_df(), f"/sensors/{sensor_id}/days {r.status_code}: {r.text[:240]}"
        data = r.json()
    except requests.RequestException as e:
        return _empty_df(), f"Network error: {e}"

    rows = []
    for res in data.get("results", []):
        # v3: value is daily mean; parameter object has units & name
        value = res.get("value")
        param = (res.get("parameter") or {}).get("name")
        units = (res.get("parameter") or {}).get("units")
        period = res.get("period") or {}
        dt_from = (period.get("datetimeFrom") or {}).get("utc")
        # Use the 'to' timestamp or from—daily mean for that day
        rows.append({
            "datetime": dt_from,
            "value": value,
            "unit": units,
            "location": None,     # not provided here; optional
            "latitude": None,
            "longitude": None,
            "sensor_id": sensor_id,
        })

    if not rows:
        return _empty_df(), "No daily values for this sensor & period."

    df = pd.DataFrame(rows)
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True, errors="coerce")
    df = df.dropna(subset=["datetime"]).sort_values("datetime").reset_index(drop=True)
    return df, None

def fetch_city_parameter_daily(country_iso: Optional[str],
                               city_like: str,
                               parameter_name: str,
                               date_from: str,
                               date_to: str) -> Tuple[pd.DataFrame, Optional[str]]:
    """
    High level: find locations that match city & parameter → pick a few sensors → concat daily series.
    """
    locs, err = fetch_locations_by_city(country_iso, city_like, parameter_name)
    if err:
        return _empty_df(), err

    # pick up to 3 sensors across the first few locations to build a representative city series
    daily_frames = []
    picked = 0
    for _, loc in locs.iterrows():
        sensors_df, serr = fetch_sensors_for_location(int(loc["location_id"]), parameter_name)
        if serr:
            # just continue; maybe another location has sensors
            continue
        for _, srow in sensors_df.head(3).iterrows():
            sd, derr = fetch_daily_for_sensor(int(srow["sensor_id"]), date_from, date_to)
            if derr:
                continue
            sd["location_id"] = loc["location_id"]
            sd["location"] = loc["location_name"]
            daily_frames.append(sd)
            picked += 1
            if picked >= 5:  # cap requests a bit
                break
        if picked >= 5:
            break

    if not daily_frames:
        return _empty_df(), "Found locations, but could not fetch daily series for sensors in this period."

    df = pd.concat(daily_frames, ignore_index=True)
    return df, None

# ---- City & Sensor picker helpers (v3) ----
def list_cities(country_iso: str, parameter_name: str, limit: int = 200):
    """
    Returns a sorted list of unique city/locality names in a country that have the given parameter sensors.
    """
    if not API_KEY:
        return [], "Missing OpenAQ API key. Set OPENAQ_API_KEY in .env."
    params = {"iso": country_iso, "limit": limit}
    try:
        r = requests.get(f"{API_BASE}/locations", params=params, headers=_headers(), timeout=30)
        if r.status_code != 200:
            return [], f"/locations {r.status_code}: {r.text[:240]}"
        data = r.json()
    except requests.RequestException as e:
        return [], f"Network error: {e}"

    names = set()
    for loc in data.get("results", []):
        sensors = loc.get("sensors") or []
        has_param = any((s.get("parameter", {}).get("name") == parameter_name) for s in sensors)
        if has_param:
            # prefer 'locality'; fall back to location 'name'
            nm = (loc.get("locality") or loc.get("name") or "").strip()
            if nm:
                names.add(nm)
    out = sorted(names)
    if not out:
        return [], "No cities with that pollutant in this country."
    return out, None

def list_sensors_in_city(country_iso: str, city_like: str, parameter_name: str, limit: int = 200):
    """
    Returns a list of (sensor_id, label) for sensors that match city & parameter.
    """
    locs_df, err = fetch_locations_by_city(country_iso, city_like, parameter_name, limit=limit)
    if err:
        return [], err
    sensors = []
    for _, loc in locs_df.iterrows():
        s_df, s_err = fetch_sensors_for_location(int(loc["location_id"]), parameter_name)
        if s_err or s_df.empty:
            continue
        for _, row in s_df.iterrows():
            label = f"{loc['location_name']} • {row['parameter']} • sensor {row['sensor_id']}"
            sensors.append((int(row["sensor_id"]), label))
    if not sensors:
        return [], "No sensors found for that city + pollutant."
    return sensors, None
