"""
Tests for fieldverify.utils.barcode module
"""

import pytest
import numpy as np
import cv2
from fieldverify.utils.barcode import (
    scan_barcode_or_qr_from_image,
    generate_barcode_qr_image,
    validate_evidence_bag_barcode
)


def test_generate_and_scan_qr_roundtrip():
    payload = '{"reagent": "SCOTT_REAGENT", "lot": "SC-2026-9999", "exp": "2027-12-31"}'
    qr_img = generate_barcode_qr_image(payload)
    assert isinstance(qr_img, np.ndarray)
    assert qr_img.shape[0] > 50 and qr_img.shape[1] > 50

    scan_res = scan_barcode_or_qr_from_image(qr_img)
    assert scan_res["found"] is True
    assert scan_res["text"] == payload
    assert scan_res["code_type"] == "QR"


def test_scan_evidence_bag_barcode():
    bag_no = "BAG-NCB-2026-9912"
    qr_img = generate_barcode_qr_image(bag_no)
    scan_res = scan_barcode_or_qr_from_image(qr_img)
    assert scan_res["found"] is True
    assert scan_res["text"] == bag_no


def test_scan_empty_or_invalid_image():
    res = scan_barcode_or_qr_from_image(None)
    assert res["found"] is False
    assert res["text"] == ""

    blank_img = np.zeros((100, 100, 3), dtype=np.uint8)
    res2 = scan_barcode_or_qr_from_image(blank_img)
    assert res2["found"] is False


def test_validate_evidence_bag_barcode():
    v1 = validate_evidence_bag_barcode("BAG-NCB-2026-9912")
    assert v1["is_valid"] is True
    assert v1["barcode"] == "BAG-NCB-2026-9912"

    v2 = validate_evidence_bag_barcode("")
    assert v2["is_valid"] is False

    v3 = validate_evidence_bag_barcode("N/A")
    assert v3["is_valid"] is False
