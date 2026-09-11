"""
Tests for fieldverify.utils.geo module
"""

import pytest
from fieldverify.utils.geo import (
    detect_network_location,
    geocode_search,
    reverse_geocode,
    generate_regional_corridors
)


def test_generate_regional_corridors():
    center_lat = 12.9753
    center_lon = 77.5910
    corridors = generate_regional_corridors(center_lat, center_lon)
    assert len(corridors) == 7
    for c in corridors:
        assert "id" in c
        assert "latitude" in c
        assert "longitude" in c
        assert "substance" in c
        assert "result" in c
        assert "weight_g" in c
        assert c["is_live_pin"] is False
        # Corridors should be within ~1 degree of center
        assert abs(c["latitude"] - center_lat) < 1.0
        assert abs(c["longitude"] - center_lon) < 1.0


def test_geocode_search_empty():
    assert geocode_search("") is None
    assert geocode_search("   ") is None


def test_detect_network_location_live_or_fallback():
    # Will either succeed if network is active, or return None gracefully
    loc = detect_network_location(timeout=5.0)
    if loc is not None:
        assert "lat" in loc
        assert "lon" in loc
        assert "display_name" in loc
        assert isinstance(loc["lat"], float)
        assert isinstance(loc["lon"], float)
