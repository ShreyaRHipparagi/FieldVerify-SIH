"""
FieldVerify AI - Geospatial Intelligence & Geolocation Engine
Provides robust IP-based location auto-detection, forward geocoding, and reverse geocoding
using free and open-source OpenStreetMap (Nominatim) services and reliable IP APIs.
"""

import requests
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger("fieldverify.geo")

NOMINATIM_HEADERS = {
    "User-Agent": "FieldVerify-AI-LawEnforcement-App/1.0"
}


def detect_network_location(timeout: float = 4.0) -> Optional[Dict[str, Any]]:
    """
    Auto-detect the device's public network location via IP geolocation APIs.
    Returns dict with keys: lat, lon, city, region, country, display_name.
    Falls back gracefully if network is unavailable.
    """
    # Primary provider: ip-api.com (fast, reliable, free for non-commercial)
    try:
        resp = requests.get("http://ip-api.com/json/", timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "success":
                city = data.get("city", "")
                region = data.get("regionName", "")
                country = data.get("country", "")
                loc_parts = [p for p in [city, region, country] if p]
                return {
                    "lat": round(float(data["lat"]), 4),
                    "lon": round(float(data["lon"]), 4),
                    "city": city,
                    "region": region,
                    "country": country,
                    "display_name": ", ".join(loc_parts) or "Detected Field Location",
                    "provider": "ip-api"
                }
    except Exception as e:
        logger.debug(f"ip-api lookup failed: {e}")

    # Fallback provider: ipapi.co
    try:
        resp = requests.get("https://ipapi.co/json/", timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            lat = data.get("latitude")
            lon = data.get("longitude")
            if lat is not None and lon is not None:
                city = data.get("city", "")
                region = data.get("region", "")
                country = data.get("country_name", "")
                loc_parts = [p for p in [city, region, country] if p]
                return {
                    "lat": round(float(lat), 4),
                    "lon": round(float(lon), 4),
                    "city": city,
                    "region": region,
                    "country": country,
                    "display_name": ", ".join(loc_parts) or "Detected Field Location",
                    "provider": "ipapi.co"
                }
    except Exception as e:
        logger.debug(f"ipapi.co lookup failed: {e}")

    return None


def geocode_search(query: str, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
    """
    Forward geocode a location name, landmark, or address using OpenStreetMap Nominatim.
    Returns dict with keys: lat, lon, display_name.
    """
    query = (query or "").strip()
    if not query:
        return None

    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": query,
        "format": "json",
        "limit": 1,
        "addressdetails": 1
    }

    try:
        resp = requests.get(url, params=params, headers=NOMINATIM_HEADERS, timeout=timeout)
        if resp.status_code == 200:
            results = resp.json()
            if results and len(results) > 0:
                item = results[0]
                return {
                    "lat": round(float(item["lat"]), 4),
                    "lon": round(float(item["lon"]), 4),
                    "display_name": item.get("display_name", query)
                }
    except Exception as e:
        logger.warning(f"OSM Nominatim geocode error: {e}")

    return None


def reverse_geocode(lat: float, lon: float, timeout: float = 5.0) -> Optional[str]:
    """
    Reverse geocode latitude and longitude coordinates into a human-readable address / checkpoint name
    using OpenStreetMap Nominatim.
    """
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        "lat": lat,
        "lon": lon,
        "format": "json"
    }

    try:
        resp = requests.get(url, params=params, headers=NOMINATIM_HEADERS, timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            address = data.get("address", {})
            parts = []
            for key in ["road", "suburb", "neighbourhood", "city", "town", "county", "state"]:
                val = address.get(key)
                if val and val not in parts:
                    parts.append(val)
            if parts:
                return ", ".join(parts[:3])
            return data.get("display_name", f"Checkpoint ({lat:.4f}, {lon:.4f})")
    except Exception as e:
        logger.warning(f"OSM Nominatim reverse geocode error: {e}")

    return None


def generate_regional_corridors(center_lat: float, center_lon: float) -> List[Dict[str, Any]]:
    """
    Generate realistic intelligence interdiction checkpoints clustered around
    the active officer's operational area (within ~15-60 km along major transit arteries).
    """
    offsets = [
        {"dlat": 0.045, "dlon": -0.038, "name_suffix": "North Toll Plaza", "substance": "SCOTT_REAGENT", "result": "POSITIVE", "weight": 350.0, "officer": "PATROL-01"},
        {"dlat": -0.052, "dlon": 0.041, "name_suffix": "South Transit Ring Road", "substance": "MARQUIS_OPIATE", "result": "POSITIVE", "weight": 520.0, "officer": "PATROL-02"},
        {"dlat": 0.082, "dlon": 0.065, "name_suffix": "Interstate Highway Checkpost", "substance": "DUQUENOIS_LEVINE", "result": "POSITIVE", "weight": 1100.0, "officer": "PATROL-03"},
        {"dlat": -0.071, "dlon": -0.062, "name_suffix": "Expressway Interchange Post", "substance": "MARQUIS_AMPHETAMINE", "result": "POSITIVE", "weight": 420.0, "officer": "PATROL-04"},
        {"dlat": 0.021, "dlon": 0.078, "name_suffix": "Cargo Logistics Depot", "substance": "SCOTT_REAGENT", "result": "POSITIVE", "weight": 190.0, "officer": "PATROL-05"},
        {"dlat": -0.035, "dlon": -0.025, "name_suffix": "Railway Parcel Hub Checkpoint", "substance": "MARQUIS_OPIATE", "result": "POSITIVE", "weight": 640.0, "officer": "PATROL-06"},
        {"dlat": 0.015, "dlon": -0.055, "name_suffix": "Border Flying Squad Intercept", "substance": "SCOTT_REAGENT", "result": "NEGATIVE", "weight": 0.0, "officer": "PATROL-07"}
    ]
    corridors = []
    for i, off in enumerate(offsets, start=1):
        corridors.append({
            "id": f"INTEL-{i:02d}",
            "latitude": round(center_lat + off["dlat"], 4),
            "longitude": round(center_lon + off["dlon"], 4),
            "substance": off["substance"],
            "result": off["result"],
            "weight_g": off["weight"],
            "location": f"Sector #{i} {off['name_suffix']}",
            "officer": off["officer"],
            "is_live_pin": False
        })
    return corridors
