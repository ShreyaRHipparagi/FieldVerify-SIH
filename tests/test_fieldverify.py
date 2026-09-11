"""
Automated Test Suite for FieldVerify AI Core Engine
Tests ArUco Homography, von Kries White-Balance, Screen Anti-Spoofing,
CIEDE2000 Delta-E, Reagent QR Expiry, ECDSA Crypto Signatures, SQLite DB, PDF Export,
Ambient Lighting Guard, NDPS Panchnama Generator, Inventory Alarms, and CFSL Reconciliation.
"""

import pytest
import os
import cv2
import numpy as np
import tempfile
import json

from fieldverify.core.optical import (
    ciede2000,
    srgb_to_lab,
    rectify_reference_card,
    calibrate_and_extract_color,
    detect_screen_spoofing,
    check_ambient_lighting
)
from fieldverify.core.reagent import (
    VALIDATED_REAGENT_LIBRARY,
    parse_reagent_qr_data
)
from fieldverify.core.crypto import (
    generate_evidentiary_certificate,
    verify_evidentiary_certificate
)
from fieldverify.core.db import (
    init_db,
    save_test_record,
    search_test_records
)
from fieldverify.core.pdf_generator import generate_evidentiary_pdf
from fieldverify.core.panchnama import generate_ndps_panchnama_text
from fieldverify.core.inventory import init_inventory_db, get_inventory_status, record_reagent_usage
from fieldverify.core.fsl import submit_fsl_confirmatory_report
from fieldverify.utils.sample_generator import create_synthetic_test_image


@pytest.fixture
def sample_cocaine_img():
    """Fixture providing synthetic Cocaine Scott reagent test image."""
    return create_synthetic_test_image(
        reagent_type="SCOTT_REAGENT",
        is_positive=True,
        is_multi_phase=False,
        is_screen_spoof=False
    )


@pytest.fixture
def sample_spoof_img():
    """Fixture providing synthetic Screen Re-photography spoof test image."""
    return create_synthetic_test_image(
        reagent_type="SCOTT_REAGENT",
        is_positive=True,
        is_multi_phase=False,
        is_screen_spoof=True
    )


def test_ciede2000_math():
    """Verifies CIEDE2000 color distance calculations."""
    lab1 = (30.0, 2.0, -52.0)
    lab2 = (30.0, 2.0, -52.0)
    assert ciede2000(lab1, lab2) == 0.0

    lab_near = (29.8, 1.9, -51.2)
    dE = ciede2000(lab1, lab_near)
    assert 0.0 < dE <= 2.5


def test_srgb_to_lab_conversion():
    """Tests sRGB to CIELAB conversion."""
    bgr_blue = (255, 0, 0)
    L, a, b = srgb_to_lab(bgr_blue)
    assert L > 0
    assert b < -20 # Blue channel should have negative b* value


def test_aruco_homography_rectification(sample_cocaine_img):
    """Tests 4-point ArUco marker detection and perspective warp."""
    rectified = rectify_reference_card(sample_cocaine_img)
    assert rectified.shape == (600, 1000, 3)


def test_optical_calibration_and_color_extraction(sample_cocaine_img):
    """Tests von Kries gain normalization and color measurement."""
    rectified = rectify_reference_card(sample_cocaine_img)
    res = calibrate_and_extract_color(rectified, is_multi_phase=False)

    assert "calibrated_pouch" in res
    assert "measured_lab" in res
    assert res["glare_percentage"] >= 0.0
    assert "k_R" in res["white_gains"]


def test_ambient_lighting_guard(sample_cocaine_img):
    """Verifies ambient illumination guard (lux estimation & recommendation)."""
    # Normal image
    res = check_ambient_lighting(sample_cocaine_img)
    assert res["status"] in ["OPTIMAL", "TOO_DARK", "TOO_BRIGHT"]
    assert res["estimated_lux"] > 0

    # Extremely dark simulation
    dark_img = np.zeros((400, 400, 3), dtype=np.uint8)
    res_dark = check_ambient_lighting(dark_img)
    assert res_dark["status"] == "TOO_DARK"
    assert res_dark["recommendation"] == "FLASHLIGHT_REQUIRED"


def test_screen_anti_spoofing_detection(sample_cocaine_img, sample_spoof_img):
    """Verifies Moiré FFT screen re-photography detection."""
    is_spoof_clean, _, _ = detect_screen_spoofing(sample_cocaine_img)
    is_spoof_dirty, _, _ = detect_screen_spoofing(sample_spoof_img)

    assert is_spoof_clean is False
    assert is_spoof_dirty is True


def test_reagent_qr_parsing():
    """Tests reagent batch lot and expiry parsing."""
    valid_qr = '{"reagent": "SCOTT_REAGENT", "lot": "SC-2026-0819", "exp": "2029-12-31"}'
    res_valid = parse_reagent_qr_data(valid_qr)
    assert res_valid["is_valid"] is True
    assert res_valid["is_expired"] is False
    assert res_valid["lot_number"] == "SC-2026-0819"

    expired_qr = '{"reagent": "SCOTT_REAGENT", "lot": "EXPIRED-123", "exp": "2020-01-01"}'
    res_expired = parse_reagent_qr_data(expired_qr)
    assert res_expired["is_valid"] is True
    assert res_expired["is_expired"] is True


def test_ecdsa_crypto_sealing_and_tamper_detection(sample_cocaine_img):
    """Tests SHA-256 dual hashing, ECDSA signing, evidence bag binding, and tamper detection."""
    rectified = rectify_reference_card(sample_cocaine_img)
    res = calibrate_and_extract_color(rectified)

    _, raw_bytes = cv2.imencode(".png", sample_cocaine_img)
    _, roi_bytes = cv2.imencode(".png", res["calibrated_pouch"])

    meta = {
        "test_id": "FV-TEST-001",
        "officer_id": "SI-TEST-99",
        "fir_case_ref": "FIR-001",
        "reagent_type": "SCOTT_REAGENT",
        "measured_lab": {"L": res["measured_lab"][0], "a": res["measured_lab"][1], "b": res["measured_lab"][2]},
        "delta_e00": 1.5,
        "outcome": "POSITIVE",
        "evidence_bag_barcode": "BAG-NCB-2026-01",
        "estimated_weight_g": 250.0,
        "witness_1_name": "Ramesh Kumar",
        "witness_2_name": "Amit Sen"
    }

    cert = generate_evidentiary_certificate(raw_bytes.tobytes(), roi_bytes.tobytes(), meta)

    # 1. Authentic Verification
    is_valid, msg = verify_evidentiary_certificate(cert)
    assert is_valid is True
    assert "SIGNATURE_VALID" in msg
    assert cert["evidence_bag_barcode"] == "BAG-NCB-2026-01"

    # 2. Tampered Payload Verification
    tampered_cert = dict(cert)
    tampered_cert["outcome"] = "NEGATIVE" # Modification simulation
    is_valid_tampered, tampered_msg = verify_evidentiary_certificate(tampered_cert)
    assert is_valid_tampered is False
    assert "TAMPER_DETECTED" in tampered_msg


def test_ndps_panchnama_generation():
    """Verifies statutory NDPS Panchnama seizure memo formatting."""
    data = {
        "test_id": "FV-20260910-PANCH",
        "fir_case_ref": "FIR-2026/GHY-99",
        "officer_name": "SI Rajesh Barua",
        "officer_badge_id": "AS-CID-9942",
        "police_station": "NCB Guwahati",
        "seizure_location": "Guwahati Toll Plaza",
        "gps_coords": (26.1445, 91.7362),
        "suspected_substance": "White crystalline powder (Cocaine)",
        "presumptive_result": "POSITIVE FOR COCAINE",
        "delta_e": 1.84,
        "estimated_weight_g": 350.0,
        "evidence_bag_barcode": "BAG-NCB-2026-9912",
        "witness_1_name": "Ramesh Kumar",
        "witness_1_address": "Kamrup",
        "witness_2_name": "Amit Sen",
        "witness_2_address": "Guwahati",
        "raw_hash": "a1b2c3d4e5",
        "roi_hash": "f6e7d8c9b0",
        "ecdsa_sig": "3045022100abcde"
    }
    memo = generate_ndps_panchnama_text(data)
    assert "MEMORANDUM OF SEIZURE (PANCHNAMA)" in memo
    assert "BAG-NCB-2026-9912" in memo
    assert "Ramesh Kumar" in memo
    assert "350.00 grams" in memo


def test_reagent_inventory_manager():
    """Verifies reagent stock tracking and expiry calculation."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        db_path = tmp_db.name

    try:
        init_inventory_db(db_path)
        items = get_inventory_status(db_path)
        assert len(items) >= 4
        # Verify status flags exist
        for it in items:
            assert "status_flags" in it
            assert isinstance(it["days_left"], int)

        # Decrement stock test
        initial_qty = items[0]["quantity_in_stock"]
        record_reagent_usage(items[0]["reagent_code"], db_path=db_path)
        updated_items = get_inventory_status(db_path)
        assert updated_items[0]["quantity_in_stock"] == initial_qty - 1
    finally:
        try:
            if os.path.exists(db_path):
                os.remove(db_path)
        except Exception:
            pass


def test_cfsl_lab_reconciliation():
    """Verifies CFSL lab confirmatory report submission and status update."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        db_path = tmp_db.name

    try:
        init_db(db_path)

        dummy_cert = {
            "test_id": "FV-FSL-TEST-01",
            "timestamp_utc": "2026-09-10T12:00:00Z",
            "officer_badge_id": "SI-OFFICER",
            "fir_case_ref": "FIR-FSL-01",
            "gps": {"lat": 26.14, "lon": 91.73},
            "location_name": "Test Post",
            "reagent_type": "SCOTT_REAGENT",
            "batch_lot": "LOT-01",
            "measured_lab": {"L": 30.0, "a": 2.0, "b": -52.0},
            "delta_e00": 1.2,
            "outcome": "POSITIVE",
            "anti_spoof_status": "PASS",
            "evidence_bag_barcode": "BAG-FSL-01",
            "estimated_weight_g": 500.0,
            "witness_1_name": "W1",
            "witness_2_name": "W2",
            "ambient_lux": 450.0,
            "fsl_status": "PENDING_LAB",
            "sha256_raw_image": "hashraw123",
            "sha256_calibrated_roi": "hashroi123",
            "digital_signature": "sig123"
        }
        save_test_record(dummy_cert, db_path=db_path)

        # Submit CFSL confirmatory testing
        res = submit_fsl_confirmatory_report(
            test_id="FV-FSL-TEST-01",
            chemist_id="CFSL-884",
            chemist_name="Dr. Sharma",
            lab_name="CFSL New Delhi",
            analytical_method="GC-MS",
            molecular_identification="Cocaine Base (C17H21NO4)",
            purity_percentage=88.5,
            fsl_verdict="CONFIRMED_POSITIVE",
            remarks="Spectral retention matched analytical standard",
            db_path=db_path
        )

        assert res["success"] is True

        records = search_test_records(search_query="FV-FSL-TEST-01", db_path=db_path)
        assert len(records) == 1
        assert records[0]["fsl_status"] == "CONFIRMED_POSITIVE"
        assert records[0]["fsl_confirmed_substance"] == "Cocaine Base (C17H21NO4)"
    finally:
        try:
            if os.path.exists(db_path):
                os.remove(db_path)
        except Exception:
            pass


def test_sqlite_db_ledger():
    """Tests SQLite DB audit ledger insertion and query filters."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        db_path = tmp_db.name

    try:
        init_db(db_path)

        dummy_cert = {
            "test_id": "FV-DB-TEST-99",
            "timestamp_utc": "2026-09-09T12:00:00Z",
            "officer_badge_id": "SI-DB-OFFICER",
            "fir_case_ref": "FIR-DB-123",
            "gps": {"lat": 26.14, "lon": 91.73},
            "location_name": "Test Checkpoint",
            "reagent_type": "SCOTT_REAGENT",
            "batch_lot": "LOT-99",
            "measured_lab": {"L": 30.0, "a": 2.0, "b": -52.0},
            "delta_e00": 1.2,
            "outcome": "POSITIVE",
            "anti_spoof_status": "PASS",
            "evidence_bag_barcode": "BAG-0099",
            "estimated_weight_g": 100.0,
            "witness_1_name": "W1",
            "witness_2_name": "W2",
            "ambient_lux": 450.0,
            "fsl_status": "PENDING_LAB",
            "sha256_raw_image": "abc123raw",
            "sha256_calibrated_roi": "xyz456roi",
            "digital_signature": "sig123hex"
        }

        save_test_record(dummy_cert, db_path=db_path)
        records = search_test_records(officer_id="SI-DB-OFFICER", db_path=db_path)

        assert len(records) == 1
        assert records[0]["id"] == "FV-DB-TEST-99"
        assert records[0]["result"] == "POSITIVE"

    finally:
        try:
            if os.path.exists(db_path):
                os.remove(db_path)
        except Exception:
            pass


def test_pdf_affidavit_generation():
    """Verifies Section 63 BSA PDF affidavit generation."""
    dummy_cert = {
        "test_id": "FV-PDF-TEST-77",
        "timestamp_utc": "2026-09-09T12:00:00Z",
        "officer_badge_id": "SI-PDF-OFFICER",
        "fir_case_ref": "FIR-PDF-777",
        "gps": {"lat": 26.14, "lon": 91.73},
        "location_name": "Guwahati Toll Plaza",
        "reagent_type": "SCOTT_REAGENT",
        "batch_lot": "LOT-SC-2026",
        "measured_lab": {"L": 29.8, "a": 1.9, "b": -51.2},
        "delta_e00": 1.84,
        "outcome": "POSITIVE",
        "anti_spoof_status": "PASS",
        "sha256_raw_image": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "sha256_calibrated_roi": "7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069",
        "ecdsa_signature_hex": "3045022100e4b8f000112233445566778899aabbccddeeff00112233445566778899"
    }

    pdf_bytes = generate_evidentiary_pdf(dummy_cert)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 2000
    assert pdf_bytes.startswith(b"%PDF")


if __name__ == "__main__":
    print("Running Extended FieldVerify Test Suite...")
    sample_cocaine = create_synthetic_test_image(reagent_type="SCOTT_REAGENT", is_positive=True)
    sample_spoof = create_synthetic_test_image(reagent_type="SCOTT_REAGENT", is_positive=True, is_screen_spoof=True)

    test_ciede2000_math()
    test_srgb_to_lab_conversion()
    test_aruco_homography_rectification(sample_cocaine)
    test_optical_calibration_and_color_extraction(sample_cocaine)
    test_ambient_lighting_guard(sample_cocaine)
    test_screen_anti_spoofing_detection(sample_cocaine, sample_spoof)
    test_reagent_qr_parsing()
    test_ecdsa_crypto_sealing_and_tamper_detection(sample_cocaine)
    test_ndps_panchnama_generation()
    test_reagent_inventory_manager()
    test_cfsl_lab_reconciliation()
    test_sqlite_db_ledger()
    test_pdf_affidavit_generation()
    print("ALL 13 TESTS PASSED SUCCESSFULLY!")
