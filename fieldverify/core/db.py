"""
FieldVerify SQLite Database Ledger
Maintains an immutable local ledger of field drug tests conducted,
with searchable logs, chain-of-custody evidence bag linkage, and CFSL lab reconciliation.
"""

import sqlite3
import os
import json

DB_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "fieldverify_ledger.db")


def get_db_connection(db_path=DB_FILE_PATH):
    """Establishes and returns SQLite connection."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path=DB_FILE_PATH):
    """Initializes SQLite schema and indexes, performing non-destructive migrations if needed."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS test_records (
        id TEXT PRIMARY KEY,
        timestamp_utc TEXT NOT NULL,
        officer_id TEXT NOT NULL,
        officer_name TEXT DEFAULT 'Sub-Inspector Rajesh Barua',
        fir_case_ref TEXT,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        location_name TEXT,
        reagent_type TEXT NOT NULL,
        batch_lot TEXT NOT NULL,
        measured_l REAL NOT NULL,
        measured_a REAL NOT NULL,
        measured_b REAL NOT NULL,
        delta_e REAL NOT NULL,
        result TEXT NOT NULL,
        anti_spoof_status TEXT NOT NULL,
        evidence_bag_barcode TEXT DEFAULT 'N/A',
        estimated_weight_g REAL DEFAULT 0.0,
        witness_1_name TEXT DEFAULT 'N/A',
        witness_2_name TEXT DEFAULT 'N/A',
        ambient_lux REAL DEFAULT 450.0,
        fsl_status TEXT DEFAULT 'PENDING_LAB',
        fsl_chemist TEXT,
        fsl_lab_name TEXT,
        fsl_method TEXT,
        fsl_confirmed_substance TEXT,
        fsl_purity REAL,
        fsl_timestamp TEXT,
        fsl_notes TEXT,
        raw_image_path TEXT,
        raw_image_hash TEXT NOT NULL,
        roi_image_path TEXT,
        roi_image_hash TEXT NOT NULL,
        digital_signature TEXT NOT NULL,
        certificate_json TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Check and add new columns if table existed prior to update
    cursor.execute("PRAGMA table_info(test_records)")
    existing_cols = [c[1] for c in cursor.fetchall()]

    new_cols = [
        ("officer_name", "TEXT DEFAULT 'Sub-Inspector Rajesh Barua'"),
        ("evidence_bag_barcode", "TEXT DEFAULT 'N/A'"),
        ("estimated_weight_g", "REAL DEFAULT 0.0"),
        ("witness_1_name", "TEXT DEFAULT 'N/A'"),
        ("witness_2_name", "TEXT DEFAULT 'N/A'"),
        ("ambient_lux", "REAL DEFAULT 450.0"),
        ("fsl_status", "TEXT DEFAULT 'PENDING_LAB'"),
        ("fsl_chemist", "TEXT"),
        ("fsl_lab_name", "TEXT"),
        ("fsl_method", "TEXT"),
        ("fsl_confirmed_substance", "TEXT"),
        ("fsl_purity", "REAL"),
        ("fsl_timestamp", "TEXT"),
        ("fsl_notes", "TEXT")
    ]

    for col_name, col_def in new_cols:
        if col_name not in existing_cols:
            try:
                cursor.execute(f"ALTER TABLE test_records ADD COLUMN {col_name} {col_def};")
            except Exception:
                pass

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_officer_date ON test_records(officer_id, timestamp_utc);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_result ON test_records(result);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reagent ON test_records(reagent_type);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fsl_status ON test_records(fsl_status);")

    conn.commit()
    conn.close()


def save_test_record(cert, raw_img_path="", roi_img_path="", db_path=DB_FILE_PATH):
    """Inserts or updates a completed test certificate record in the SQLite database."""
    init_db(db_path)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    gps = cert.get("gps", {})
    lab = cert.get("measured_lab", {})

    cursor.execute("""
    INSERT OR REPLACE INTO test_records (
        id, timestamp_utc, officer_id, officer_name, fir_case_ref, latitude, longitude, location_name,
        reagent_type, batch_lot, measured_l, measured_a, measured_b, delta_e,
        result, anti_spoof_status, evidence_bag_barcode, estimated_weight_g,
        witness_1_name, witness_2_name, ambient_lux, fsl_status, raw_image_path, raw_image_hash,
        roi_image_path, roi_image_hash, digital_signature, certificate_json
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        cert["test_id"],
        cert["timestamp_utc"],
        cert["officer_badge_id"],
        cert.get("officer_name", "Sub-Inspector Rajesh Barua"),
        cert.get("fir_case_ref", "N/A"),
        gps.get("lat", 0.0),
        gps.get("lon", 0.0),
        cert.get("location_name", "N/A"),
        cert["reagent_type"],
        cert["batch_lot"],
        lab.get("L", 0.0),
        lab.get("a", 0.0),
        lab.get("b", 0.0),
        cert["delta_e00"],
        cert["outcome"],
        cert.get("anti_spoof_status", "PASS"),
        cert.get("evidence_bag_barcode", "N/A"),
        cert.get("estimated_weight_g", 0.0),
        cert.get("witness_1_name", "N/A"),
        cert.get("witness_2_name", "N/A"),
        cert.get("ambient_lux", 450.0),
        cert.get("fsl_status", "PENDING_LAB"),
        raw_img_path,
        cert["sha256_raw_image"],
        roi_img_path,
        cert["sha256_calibrated_roi"],
        cert.get("ecdsa_signature_hex", cert.get("digital_signature", "N/A")),
        json.dumps(cert, sort_keys=True)
    ))

    conn.commit()
    conn.close()


def search_test_records(officer_id=None, result_filter=None, search_query=None, limit=100, db_path=DB_FILE_PATH):
    """Searches test records by officer, outcome, or keyword."""
    init_db(db_path)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    query = "SELECT * FROM test_records WHERE 1=1"
    params = []

    if officer_id:
        query += " AND officer_id LIKE ?"
        params.append(f"%{officer_id}%")

    if result_filter and result_filter != "ALL":
        query += " AND result = ?"
        params.append(result_filter)

    if search_query:
        query += " AND (id LIKE ? OR fir_case_ref LIKE ? OR reagent_type LIKE ? OR batch_lot LIKE ? OR evidence_bag_barcode LIKE ?)"
        term = f"%{search_query}%"
        params.extend([term, term, term, term, term])

    query += " ORDER BY timestamp_utc DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]
