"""
Automated Test Suite for FieldVerify AI Core Engine
Tests ArUco Homography, von Kries White-Balance, Screen Anti-Spoofing,
CIEDE2000 Delta-E, Reagent QR Expiry, ECDSA Crypto Signatures, SQLite DB, PDF Export,
Ambient Lighting Guard, NDPS Panchnama Generator, Inventory Alarms, and CFSL Reconciliation.
"""

import sys
import os
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
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


def test_negative_blank_sample_no_false_glare():
    """Verifies that a clear / negative blank test liquid does not cause false glare failure."""
    blank_img = create_synthetic_test_image(reagent_type="SCOTT_REAGENT", is_positive=False)
    rectified = rectify_reference_card(blank_img)
    res = calibrate_and_extract_color(rectified, is_multi_phase=False)

    assert res["glare_percentage"] < 35.0
    de = ciede2000(res["measured_lab"], VALIDATED_REAGENT_LIBRARY["SCOTT_REAGENT"]["target_lab"])
    assert de >= VALIDATED_REAGENT_LIBRARY["SCOTT_REAGENT"]["min_negative_delta_e"]


def test_duquenois_levine_multiphase_organic_extraction():
    """Verifies Duquenois-Levine multi-phase liquid layer extraction and positive classification."""
    dl_img = create_synthetic_test_image(reagent_type="DUQUENOIS_LEVINE", is_positive=True, is_multi_phase=True)
    rectified = rectify_reference_card(dl_img)
    res = calibrate_and_extract_color(rectified, is_multi_phase=True)

    assert res["is_multi_phase"] is True
    assert res["phase_boundary_y"] is not None
    assert 100 <= res["phase_boundary_y"] <= 200

    target = VALIDATED_REAGENT_LIBRARY["DUQUENOIS_LEVINE"]["target_lab"]
    de = ciede2000(res["measured_lab"], target)
    assert de <= VALIDATED_REAGENT_LIBRARY["DUQUENOIS_LEVINE"]["max_positive_delta_e"]


def test_all_four_synthetic_demo_samples_classify_positive():
    """Verifies that all 4 certified chemical reagent positive samples classify as POSITIVE."""
    reagents = ["SCOTT_REAGENT", "MARQUIS_OPIATE", "MARQUIS_AMPHETAMINE", "DUQUENOIS_LEVINE"]
    for rk in reagents:
        is_mp = (rk == "DUQUENOIS_LEVINE")
        img = create_synthetic_test_image(reagent_type=rk, is_positive=True, is_multi_phase=is_mp)
        rectified = rectify_reference_card(img)
        res = calibrate_and_extract_color(rectified, is_multi_phase=is_mp)
        target = VALIDATED_REAGENT_LIBRARY[rk]["target_lab"]
        de = ciede2000(res["measured_lab"], target)
        max_pos = VALIDATED_REAGENT_LIBRARY[rk]["max_positive_delta_e"]
        assert de <= max_pos, f"{rk} failed positive classification: dE={de} > {max_pos}"


def test_reference_card_roi_swatch_sampling_accuracy():
    """Verifies that rectified reference card aligns White and Gray patches accurately."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_card:
        card_path = tmp_card.name

    try:
        from fieldverify.utils.card_generator import generate_reference_card
        generate_reference_card(card_path)
        card = cv2.imread(card_path)
        rectified = rectify_reference_card(card)

        # 95% White Patch ROI: x=150, y=450, w=80, h=80
        white_patch = rectified[450:530, 150:230]
        white_mean = np.mean(white_patch, axis=(0, 1))
        # Target 242 within 3% tolerance
        assert np.all(white_mean >= 235.0), f"White patch misaligned: mean={white_mean}"

        # 18% Gray Patch ROI: x=250, y=450, w=80, h=80
        light_res = check_ambient_lighting(card, rectified_card=rectified)
        assert light_res["status"] == "OPTIMAL"
        assert light_res["recommendation"] == "PROCEED"
        assert 350.0 <= light_res["estimated_lux"] <= 550.0
    finally:
        try:
            if os.path.exists(card_path):
                os.remove(card_path)
        except Exception:
            pass


def test_ciede2000_properties_and_invariants():
    """Verifies mathematical properties and invariants of CIEDE2000 metric."""
    lab_a = (50.0, 20.0, -30.0)
    lab_b = (60.0, -10.0, 40.0)

    # Invariant 1: Identity of indiscernibles
    assert ciede2000(lab_a, lab_a) == 0.0
    assert ciede2000(lab_b, lab_b) == 0.0

    # Invariant 2: Symmetry: dE(a, b) == dE(b, a)
    assert ciede2000(lab_a, lab_b) == ciede2000(lab_b, lab_a)

    # Invariant 3: Non-negativity
    assert ciede2000(lab_a, lab_b) > 0.0

    # Invariant 4: Achromatic / zero chroma stability
    neutral_1 = (50.0, 0.0, 0.0)
    neutral_2 = (75.0, 0.0, 0.0)
    dE_neutral = ciede2000(neutral_1, neutral_2)
    assert dE_neutral > 0.0
    assert ciede2000(neutral_1, neutral_2) == ciede2000(neutral_2, neutral_1)


def test_reagent_qr_parsing_edge_cases():
    """Verifies QR parser handles same-day expiry, malformed dates, invalid payloads."""
    from datetime import datetime, timezone
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # 1. Same-day expiration: kit expiring today is NOT expired
    qr_today = f'{{"reagent": "SCOTT_REAGENT", "lot": "LOT-TODAY", "exp": "{today_str}"}}'
    res_today = parse_reagent_qr_data(qr_today)
    assert res_today["is_valid"] is True
    assert res_today["is_expired"] is False

    # 2. Malformed date format is rejected
    qr_malformed = '{"reagent": "SCOTT_REAGENT", "lot": "LOT-BAD", "exp": "2026-13-45"}'
    res_malformed = parse_reagent_qr_data(qr_malformed)
    assert res_malformed["is_valid"] is False
    assert "Invalid expiry date format" in res_malformed["error"]

    # 3. Unrecognized reagent rejected
    qr_unknown = '{"reagent": "UNKNOWN_CHEMICAL", "lot": "LOT-1", "exp": "2028-01-01"}'
    res_unknown = parse_reagent_qr_data(qr_unknown)
    assert res_unknown["is_valid"] is False
    assert "Unrecognized reagent type" in res_unknown["error"]

    # 4. None and empty payload
    assert parse_reagent_qr_data(None)["is_valid"] is False
    assert parse_reagent_qr_data("")["is_valid"] is False
    assert parse_reagent_qr_data("[1, 2, 3]")["is_valid"] is False


def test_panchnama_robustness_with_edge_cases():
    """Verifies panchnama generation handles None, dict GPS, and negative coordinates."""
    # Dict GPS coords
    res_dict_gps = generate_ndps_panchnama_text({
        "gps_coords": {"lat": 26.1445, "lon": 91.7362},
        "test_id": "FV-20260911-001"
    })
    assert "26.14450° N, 91.73620° E" in res_dict_gps

    # Negative coordinates (South, West)
    res_neg_gps = generate_ndps_panchnama_text({
        "gps_coords": (-15.7890, -47.9250),
        "test_id": "FV-20260911-002"
    })
    assert "15.78900° S, 47.92500° W" in res_neg_gps

    # None and empty inputs
    res_empty = generate_ndps_panchnama_text({})
    assert "MEMORANDUM OF SEIZURE (PANCHNAMA)" in res_empty

    res_none = generate_ndps_panchnama_text(None)
    assert "MEMORANDUM OF SEIZURE (PANCHNAMA)" in res_none

    res_nulls = generate_ndps_panchnama_text({
        "test_id": None,
        "gps_coords": None,
        "estimated_weight_g": None,
        "delta_e": None,
        "ecdsa_sig": None
    })
    assert "MEMORANDUM OF SEIZURE (PANCHNAMA)" in res_nulls


def test_pdf_affidavit_robustness_with_sparse_cert():
    """Verifies PDF affidavit generator handles incomplete or None metadata."""
    sparse_cert = {
        "test_id": "FV-SPARSE-001",
        "timestamp_utc": None,
        "officer_badge_id": None,
        "gps": None,
        "measured_lab": None,
        "sha256_raw_image": None,
        "ecdsa_signature_hex": None
    }
    pdf_bytes = generate_evidentiary_pdf(sparse_cert)
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")


def test_crypto_verification_edge_cases():
    """Verifies crypto verification with legacy field names and tampered signatures."""
    raw_img = b"raw_test_image_bytes_123"
    roi_img = b"roi_test_image_bytes_456"
    cert = generate_evidentiary_certificate(raw_img, roi_img, {"test_id": "FV-CRYPTO-TEST"})

    # 1. Authentic
    is_valid, _ = verify_evidentiary_certificate(cert)
    assert is_valid is True

    # 2. Tampered signature (invalid hex)
    bad_sig_cert = dict(cert)
    bad_sig_cert["ecdsa_signature_hex"] = "not-a-valid-hex-signature"
    is_valid_bad, msg = verify_evidentiary_certificate(bad_sig_cert)
    assert is_valid_bad is False

    # 3. Missing signature
    no_sig_cert = dict(cert)
    del no_sig_cert["ecdsa_signature_hex"]
    is_valid_no, msg_no = verify_evidentiary_certificate(no_sig_cert)
    assert is_valid_no is False
    assert "Missing ECDSA signature" in msg_no

    # 4. Support legacy digital_signature key
    legacy_cert = dict(cert)
    legacy_cert["digital_signature"] = legacy_cert.pop("ecdsa_signature_hex")
    is_valid_leg, _ = verify_evidentiary_certificate(legacy_cert)
    assert is_valid_leg is True


def test_inventory_non_negative_invariants():
    """Verifies inventory quantity never becomes negative upon repeated usage."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        db_path = tmp_db.name

    try:
        init_inventory_db(db_path)
        items = get_inventory_status(db_path)
        code = items[0]["reagent_code"]
        qty = items[0]["quantity_in_stock"]

        # Decrement more times than in stock
        for _ in range(qty + 5):
            record_reagent_usage(code, db_path=db_path)

        updated = get_inventory_status(db_path)
        item_updated = next(it for it in updated if it["reagent_code"] == code)
        assert item_updated["quantity_in_stock"] == 0
        assert "LOW_STOCK" in item_updated["status_flags"]
    finally:
        try:
            if os.path.exists(db_path):
                os.remove(db_path)
        except Exception:
            pass


def test_fsl_lab_reconciliation_missing_record():
    """Verifies submitting FSL report for non-existent record handles safely."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        db_path = tmp_db.name

    try:
        init_db(db_path)
        res = submit_fsl_confirmatory_report(
            test_id="NON_EXISTENT_ID_999",
            chemist_id="CH-01",
            chemist_name="Dr. Chemist",
            lab_name="CFSL",
            analytical_method="GC-MS",
            molecular_identification="None",
            purity_percentage=99.0,
            fsl_verdict="CONFIRMED_POSITIVE",
            db_path=db_path
        )
        assert res["success"] is False
        assert "not found" in res["message"]
    finally:
        try:
            if os.path.exists(db_path):
                os.remove(db_path)
        except Exception:
            pass


def test_optical_spoofing_rejects_none_input():
    """Verifies detect_screen_spoofing raises ValueError on None/invalid input."""
    with pytest.raises(ValueError, match="Invalid image input"):
        detect_screen_spoofing(None)
    with pytest.raises(ValueError, match="Invalid image input"):
        detect_screen_spoofing(np.array([]))


def test_optical_ambient_rejects_none_input():
    """Verifies check_ambient_lighting raises ValueError on None/invalid input."""
    with pytest.raises(ValueError, match="Invalid image input"):
        check_ambient_lighting(None)
    with pytest.raises(ValueError, match="Invalid image input"):
        check_ambient_lighting(np.array([]))


def test_optical_rectify_rejects_insufficient_markers():
    """Verifies rectify_reference_card raises ValueError when < 4 ArUco markers found."""
    # Plain black image has no ArUco markers
    no_marker_img = np.zeros((600, 1000, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="Could not find all 4 corner ArUco"):
        rectify_reference_card(no_marker_img)


def test_optical_calibrate_rejects_none_image():
    """Verifies calibrate_and_extract_color raises ValueError on None input."""
    with pytest.raises(ValueError, match="Invalid rectified image"):
        calibrate_and_extract_color(None)


def test_db_search_with_result_filter():
    """Verifies search_test_records correctly filters by result outcome."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        db_path = tmp_db.name
    try:
        init_db(db_path)
        for outcome, tid in [("POSITIVE", "FV-FILTER-POS"), ("NEGATIVE", "FV-FILTER-NEG")]:
            cert = {
                "test_id": tid, "timestamp_utc": "2026-09-10T12:00:00Z",
                "officer_badge_id": "SI-FILTER", "fir_case_ref": "FIR-FILTER",
                "gps": {"lat": 26.14, "lon": 91.73}, "location_name": "Test",
                "reagent_type": "SCOTT_REAGENT", "batch_lot": "LOT-F",
                "measured_lab": {"L": 30.0, "a": 2.0, "b": -52.0},
                "delta_e00": 1.2, "outcome": outcome, "anti_spoof_status": "PASS",
                "evidence_bag_barcode": "BAG-F", "estimated_weight_g": 100.0,
                "witness_1_name": "W1", "witness_2_name": "W2",
                "ambient_lux": 450.0, "fsl_status": "PENDING_LAB",
                "sha256_raw_image": "hash1", "sha256_calibrated_roi": "hash2",
                "digital_signature": "sig"
            }
            save_test_record(cert, db_path=db_path)
        pos_only = search_test_records(result_filter="POSITIVE", db_path=db_path)
        assert len(pos_only) == 1
        assert pos_only[0]["result"] == "POSITIVE"
        all_recs = search_test_records(result_filter="ALL", db_path=db_path)
        assert len(all_recs) == 2
    finally:
        try:
            os.remove(db_path)
        except Exception:
            pass


def test_fsl_invalid_purity_string_fallback():
    """Verifies FSL purity_percentage handles invalid string inputs gracefully."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        db_path = tmp_db.name
    try:
        init_db(db_path)
        cert = {
            "test_id": "FV-PURITY-TEST", "timestamp_utc": "2026-09-10T12:00:00Z",
            "officer_badge_id": "SI-P", "fir_case_ref": "FIR-P",
            "gps": {"lat": 26.14, "lon": 91.73}, "location_name": "Test",
            "reagent_type": "SCOTT_REAGENT", "batch_lot": "LOT-P",
            "measured_lab": {"L": 30.0, "a": 2.0, "b": -52.0},
            "delta_e00": 1.2, "outcome": "POSITIVE", "anti_spoof_status": "PASS",
            "evidence_bag_barcode": "BAG-P", "estimated_weight_g": 100.0,
            "witness_1_name": "W1", "witness_2_name": "W2",
            "ambient_lux": 450.0, "fsl_status": "PENDING_LAB",
            "sha256_raw_image": "hash1", "sha256_calibrated_roi": "hash2",
            "digital_signature": "sig"
        }
        save_test_record(cert, db_path=db_path)
        res = submit_fsl_confirmatory_report(
            test_id="FV-PURITY-TEST", chemist_id="CH-P", chemist_name="Dr. P",
            lab_name="CFSL", analytical_method="GC-MS", molecular_identification="Test",
            purity_percentage="not_a_number", fsl_verdict="CONFIRMED_POSITIVE",
            db_path=db_path
        )
        assert res["success"] is True
    finally:
        try:
            os.remove(db_path)
        except Exception:
            pass


def test_pdf_negative_outcome_badge():
    """Verifies PDF generation for NEGATIVE and INCONCLUSIVE outcomes."""
    for outcome in ["NEGATIVE", "INCONCLUSIVE"]:
        cert = {
            "test_id": f"FV-{outcome}-001", "timestamp_utc": "2026-09-10T12:00:00Z",
            "officer_badge_id": "SI-01", "fir_case_ref": "FIR-01",
            "gps": {"lat": 26.14, "lon": 91.73},
            "measured_lab": {"L": 50.0, "a": 0.0, "b": 0.0},
            "delta_e00": 25.0, "outcome": outcome,
            "sha256_raw_image": "abc123", "sha256_calibrated_roi": "def456",
            "ecdsa_signature_hex": "3045022100aabbcc"
        }
        pdf_bytes = generate_evidentiary_pdf(cert)
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes.startswith(b"%PDF")
        assert len(pdf_bytes) > 2000


def test_generate_all_demo_samples_creates_files():
    """Verifies generate_all_demo_samples creates all 5 expected demo images."""
    from fieldverify.utils.sample_generator import generate_all_demo_samples
    with tempfile.TemporaryDirectory() as tmp_dir:
        generate_all_demo_samples(tmp_dir)
        expected_files = [
            "cocaine_scott_positive.png",
            "heroin_marquis_positive.png",
            "cannabis_duquenois_multiphase.png",
            "negative_blank_test.png",
            "screen_spoof_attempt.png"
        ]
        for fname in expected_files:
            fpath = os.path.join(tmp_dir, fname)
            assert os.path.exists(fpath), f"Missing demo file: {fname}"
            img = cv2.imread(fpath)
            assert img is not None, f"Unreadable demo file: {fname}"
            assert img.shape[0] > 100 and img.shape[1] > 100


def test_pdf_disk_write_mode():
    """Verifies PDF generation can write to disk via output_pdf_path."""
    cert = {
        "test_id": "FV-DISK-WRITE", "timestamp_utc": "2026-09-10T12:00:00Z",
        "officer_badge_id": "SI-01", "fir_case_ref": "FIR-01",
        "gps": {"lat": 26.14, "lon": 91.73},
        "measured_lab": {"L": 30.0, "a": 2.0, "b": -52.0},
        "delta_e00": 1.5, "outcome": "POSITIVE",
        "sha256_raw_image": "abc123", "sha256_calibrated_roi": "def456",
        "ecdsa_signature_hex": "3045022100aabbcc"
    }
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        pdf_path = tmp.name
    try:
        result = generate_evidentiary_pdf(cert, output_pdf_path=pdf_path)
        assert result == pdf_path or isinstance(result, bytes)
        assert os.path.exists(pdf_path)
        assert os.path.getsize(pdf_path) > 2000
        with open(pdf_path, "rb") as f:
            assert f.read(4) == b"%PDF"
    finally:
        try:
            os.remove(pdf_path)
        except Exception:
            pass


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

    test_negative_blank_sample_no_false_glare()
    test_duquenois_levine_multiphase_organic_extraction()
    test_all_four_synthetic_demo_samples_classify_positive()
    test_reference_card_roi_swatch_sampling_accuracy()
    test_ciede2000_properties_and_invariants()
    test_reagent_qr_parsing_edge_cases()
    test_panchnama_robustness_with_edge_cases()
    test_pdf_affidavit_robustness_with_sparse_cert()
    test_crypto_verification_edge_cases()
    test_inventory_non_negative_invariants()
    test_fsl_lab_reconciliation_missing_record()

    test_optical_spoofing_rejects_none_input()
    test_optical_ambient_rejects_none_input()
    test_optical_rectify_rejects_insufficient_markers()
    test_optical_calibrate_rejects_none_image()
    test_db_search_with_result_filter()
    test_fsl_invalid_purity_string_fallback()
    test_pdf_negative_outcome_badge()
    test_generate_all_demo_samples_creates_files()
    test_pdf_disk_write_mode()

    print("ALL 33 TESTS PASSED SUCCESSFULLY!")
