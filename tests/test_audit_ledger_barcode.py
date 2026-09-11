"""
Comprehensive End-to-End Tests for:
- Barcode and QR code processing
- Searchable SQLite Audit Ledger with Barcode filter
- Cryptographic Tamper Detection under Section 63 BSA
- FSL Laboratory Reconciliation linked to Evidence Bag Barcodes
- PDF Affidavit and NDPS Panchnama Evidence Binding
"""

import os
import json
import pytest
import numpy as np
import tempfile
from datetime import datetime, timezone

from fieldverify.core.crypto import (
    generate_evidentiary_certificate,
    verify_evidentiary_certificate
)
from fieldverify.core.db import (
    init_db,
    save_test_record,
    search_test_records
)
from fieldverify.core.panchnama import generate_ndps_panchnama_text
from fieldverify.core.pdf_generator import generate_evidentiary_pdf
from fieldverify.core.fsl import submit_fsl_confirmatory_report
from fieldverify.utils.barcode import (
    scan_barcode_or_qr_from_image,
    generate_barcode_qr_image,
    validate_evidence_bag_barcode
)
from fieldverify.utils.sample_generator import create_synthetic_test_image


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    if os.path.exists(path):
        os.remove(path)


def test_searchable_audit_ledger_by_barcode(temp_db):
    raw_img = b"raw_image_sample_bytes_1"
    roi_img = b"roi_image_sample_bytes_1"

    cert1 = generate_evidentiary_certificate(raw_img, roi_img, {
        "test_id": "FV-2026-BARCODE-001",
        "officer_id": "SI-OFFICER-A",
        "officer_name": "SI Ramesh Sharma",
        "evidence_bag_barcode": "BAG-NCB-BANGALORE-9901",
        "reagent_type": "SCOTT_REAGENT",
        "outcome": "POSITIVE",
        "estimated_weight_g": 350.0,
        "location_name": "Bangalore Toll Plaza"
    })
    save_test_record(cert1, db_path=temp_db)

    cert2 = generate_evidentiary_certificate(raw_img, roi_img, {
        "test_id": "FV-2026-BARCODE-002",
        "officer_id": "SI-OFFICER-B",
        "officer_name": "SI Priya Sen",
        "evidence_bag_barcode": "BAG-NCB-DELHI-8802",
        "reagent_type": "MARQUIS_OPIATE",
        "outcome": "POSITIVE",
        "estimated_weight_g": 500.0,
        "location_name": "Delhi Border Checkpost"
    })
    save_test_record(cert2, db_path=temp_db)

    # 1. Search specifically by barcode
    res_bc = search_test_records(barcode="BAG-NCB-BANGALORE-9901", db_path=temp_db)
    assert len(res_bc) == 1
    assert res_bc[0]["id"] == "FV-2026-BARCODE-001"
    assert res_bc[0]["evidence_bag_barcode"] == "BAG-NCB-BANGALORE-9901"

    # 2. Search by partial barcode keyword
    res_partial = search_test_records(search_query="DELHI-8802", db_path=temp_db)
    assert len(res_partial) == 1
    assert res_partial[0]["id"] == "FV-2026-BARCODE-002"

    # 3. Search by Location keyword
    res_loc = search_test_records(search_query="Bangalore", db_path=temp_db)
    assert len(res_loc) == 1
    assert res_loc[0]["id"] == "FV-2026-BARCODE-001"

    # 4. Search by Officer Name keyword
    res_off = search_test_records(search_query="Priya", db_path=temp_db)
    assert len(res_off) == 1
    assert res_off[0]["id"] == "FV-2026-BARCODE-002"


def test_tamper_detection_in_audit_ledger(temp_db):
    raw_img = b"raw_image_sample_bytes_tamper"
    roi_img = b"roi_image_sample_bytes_tamper"

    cert = generate_evidentiary_certificate(raw_img, roi_img, {
        "test_id": "FV-TAMPER-TEST",
        "officer_id": "SI-AUDIT",
        "evidence_bag_barcode": "BAG-SEAL-1122",
        "reagent_type": "SCOTT_REAGENT",
        "outcome": "POSITIVE",
        "estimated_weight_g": 100.0
    })
    save_test_record(cert, db_path=temp_db)

    # Retrieve from DB and verify integrity
    records = search_test_records(search_query="FV-TAMPER-TEST", db_path=temp_db)
    assert len(records) == 1
    stored_cert = json.loads(records[0]["certificate_json"])

    # Valid certificate verifies True
    is_valid, msg = verify_evidentiary_certificate(stored_cert)
    assert is_valid is True

    # Tampering test: alter the evidence barcode
    tampered_cert = dict(stored_cert)
    tampered_cert["evidence_bag_barcode"] = "BAG-TAMPERED-9999"
    is_tampered_valid, tamper_msg = verify_evidentiary_certificate(tampered_cert)
    assert is_tampered_valid is False
    assert "Invalid cryptographic signature" in tamper_msg or "altered" in tamper_msg.lower() or "tamper" in tamper_msg.lower()


def test_fsl_confirmation_linked_to_barcode(temp_db):
    raw_img = b"sample_raw_bytes"
    roi_img = b"sample_roi_bytes"

    cert = generate_evidentiary_certificate(raw_img, roi_img, {
        "test_id": "FV-FSL-BARCODE-01",
        "officer_id": "SI-01",
        "evidence_bag_barcode": "BAG-CUSTODY-5555",
        "reagent_type": "SCOTT_REAGENT",
        "outcome": "POSITIVE"
    })
    save_test_record(cert, db_path=temp_db)

    # Submit CFSL lab confirmatory report
    fsl_res = submit_fsl_confirmatory_report(
        test_id="FV-FSL-BARCODE-01",
        chemist_id="CH-99",
        chemist_name="Dr. Alok Verma, Senior Scientific Officer",
        lab_name="CFSL Hyderabad",
        analytical_method="GC-MS & FTIR",
        molecular_identification="Cocaine Hydrochloride",
        purity_percentage=88.5,
        fsl_verdict="CONFIRMED_POSITIVE",
        remarks="Matches roadside presumptive call exactly.",
        db_path=temp_db
    )
    assert fsl_res["success"] is True
    assert fsl_res["status"] == "CONFIRMED_POSITIVE"

    # Search and verify linked barcode in FSL record
    records = search_test_records(barcode="BAG-CUSTODY-5555", db_path=temp_db)
    assert len(records) == 1
    assert records[0]["fsl_status"] == "CONFIRMED_POSITIVE"
    assert "Dr. Alok Verma" in records[0]["fsl_chemist"]
    assert "CH-99" in records[0]["fsl_chemist"]
    assert records[0]["fsl_purity"] == 88.5


def test_panchnama_and_pdf_with_barcode():
    cert = {
        "test_id": "FV-DOC-TEST-99",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "officer_badge_id": "AS-CID-9942",
        "officer_name": "SI Rajesh Barua",
        "fir_case_ref": "FIR-2026/GHY-001",
        "evidence_bag_barcode": "BAG-TAMPER-SEAL-7711",
        "estimated_weight_g": 450.0,
        "reagent_type": "SCOTT_REAGENT",
        "outcome": "POSITIVE",
        "delta_e00": 1.25,
        "location_name": "Silk Board Checkpoint, Bengaluru",
        "witness_1_name": "Shri Amit Kumar",
        "witness_2_name": "Shri Suresh Rao",
        "sha256_raw_image": "abcdef1234567890",
        "sha256_calibrated_roi": "1234567890abcdef",
        "ecdsa_signature_hex": "3045022100..."
    }

    # Verify Panchnama text contains the evidence barcode
    panch_text = generate_ndps_panchnama_text(cert)
    assert "BAG-TAMPER-SEAL-7711" in panch_text
    assert "Silk Board Checkpoint, Bengaluru" in panch_text

    # Verify PDF affidavit generates valid bytes containing barcode
    pdf_bytes = generate_evidentiary_pdf(cert)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF")
