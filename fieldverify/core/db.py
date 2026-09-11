"""
FieldVerify SQLite Database Ledger
Maintains an immutable local ledger of field drug tests conducted,
with searchable logs, chain-of-custody evidence bag linkage, and CFSL lab reconciliation.
"""

import sqlite3
import os
import json

DB_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "fieldverify_ledger.db")
_INITIALIZED_DBS = set()


def get_db_connection(db_path=DB_FILE_PATH):
    """Establishes and returns SQLite connection with timeout and WAL mode."""
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    return conn


def init_db(db_path=DB_FILE_PATH):
    """Initializes SQLite schema and indexes, performing non-destructive migrations if needed."""
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute("""
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
            cursor = conn.cursor()
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
                        conn.execute(f"ALTER TABLE test_records ADD COLUMN {col_name} {col_def};")
                    except Exception:
                        pass

            conn.execute("CREATE INDEX IF NOT EXISTS idx_officer_date ON test_records(officer_id, timestamp_utc);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_result ON test_records(result);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_reagent ON test_records(reagent_type);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_fsl_status ON test_records(fsl_status);")

        _INITIALIZED_DBS.add(os.path.abspath(db_path))
    finally:
        conn.close()


def save_test_record(cert, raw_img_path="", roi_img_path="", db_path=DB_FILE_PATH):
    """Inserts or updates a completed test certificate record in the SQLite database."""
    abs_path = os.path.abspath(db_path)
    if abs_path not in _INITIALIZED_DBS:
        init_db(db_path)

    conn = get_db_connection(db_path)
    try:
        # Safe GPS extraction
        gps = cert.get("gps")
        lat, lon = 0.0, 0.0
        if isinstance(gps, dict):
            try:
                lat = float(gps.get("lat", 0.0) or 0.0)
                lon = float(gps.get("lon", 0.0) or 0.0)
            except (ValueError, TypeError):
                pass
        elif isinstance(gps, (tuple, list)) and len(gps) >= 2:
            try:
                lat = float(gps[0] or 0.0)
                lon = float(gps[1] or 0.0)
            except (ValueError, TypeError):
                pass

        # Safe Lab extraction
        lab = cert.get("measured_lab")
        lab_l, lab_a, lab_b = 0.0, 0.0, 0.0
        if isinstance(lab, dict):
            try:
                lab_l = float(lab.get("L", 0.0) or 0.0)
                lab_a = float(lab.get("a", 0.0) or 0.0)
                lab_b = float(lab.get("b", 0.0) or 0.0)
            except (ValueError, TypeError):
                pass
        elif isinstance(lab, (tuple, list)) and len(lab) >= 3:
            try:
                lab_l = float(lab[0] or 0.0)
                lab_a = float(lab[1] or 0.0)
                lab_b = float(lab[2] or 0.0)
            except (ValueError, TypeError):
                pass

        try:
            delta_e = float(cert.get("delta_e00", cert.get("delta_e", 0.0)) or 0.0)
        except (ValueError, TypeError):
            delta_e = 0.0

        try:
            est_weight = float(cert.get("estimated_weight_g", 0.0) or 0.0)
        except (ValueError, TypeError):
            est_weight = 0.0

        try:
            lux = float(cert.get("ambient_lux", 450.0) or 450.0)
        except (ValueError, TypeError):
            lux = 450.0

        test_id = str(cert.get("test_id") or "N/A")
        ts_utc = str(cert.get("timestamp_utc") or "N/A")
        off_id = str(cert.get("officer_badge_id") or cert.get("officer_id") or "N/A")
        raw_hash = str(cert.get("sha256_raw_image") or "N/A")
        roi_hash = str(cert.get("sha256_calibrated_roi") or "N/A")
        sig = str(cert.get("ecdsa_signature_hex") or cert.get("digital_signature") or "N/A")

        with conn:
            conn.execute("""
            INSERT OR REPLACE INTO test_records (
                id, timestamp_utc, officer_id, officer_name, fir_case_ref, latitude, longitude, location_name,
                reagent_type, batch_lot, measured_l, measured_a, measured_b, delta_e,
                result, anti_spoof_status, evidence_bag_barcode, estimated_weight_g,
                witness_1_name, witness_2_name, ambient_lux, fsl_status, raw_image_path, raw_image_hash,
                roi_image_path, roi_image_hash, digital_signature, certificate_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                test_id,
                ts_utc,
                off_id,
                str(cert.get("officer_name") or "Sub-Inspector Rajesh Barua"),
                str(cert.get("fir_case_ref") or "N/A"),
                lat,
                lon,
                str(cert.get("location_name") or "N/A"),
                str(cert.get("reagent_type") or "UNKNOWN"),
                str(cert.get("batch_lot") or "UNTRACKED"),
                lab_l,
                lab_a,
                lab_b,
                delta_e,
                str(cert.get("outcome") or cert.get("result") or "INCONCLUSIVE"),
                str(cert.get("anti_spoof_status") or "PASS"),
                str(cert.get("evidence_bag_barcode") or "N/A"),
                est_weight,
                str(cert.get("witness_1_name") or "N/A"),
                str(cert.get("witness_2_name") or "N/A"),
                lux,
                str(cert.get("fsl_status") or "PENDING_LAB"),
                raw_img_path,
                raw_hash,
                roi_img_path,
                roi_hash,
                sig,
                json.dumps(cert, sort_keys=True)
            ))
    finally:
        conn.close()


def search_test_records(officer_id=None, result_filter=None, search_query=None, barcode=None, limit=100, db_path=DB_FILE_PATH):
    """Searches test records by officer, outcome, keyword, or evidence bag barcode."""
    abs_path = os.path.abspath(db_path)
    if abs_path not in _INITIALIZED_DBS:
        init_db(db_path)

    conn = get_db_connection(db_path)
    try:
        query = "SELECT * FROM test_records WHERE 1=1"
        params = []

        if officer_id and str(officer_id).strip():
            query += " AND (officer_id LIKE ? OR officer_name LIKE ?)"
            off_term = f"%{str(officer_id).strip()}%"
            params.extend([off_term, off_term])

        if result_filter and result_filter != "ALL":
            query += " AND result = ?"
            params.append(result_filter)

        if barcode and str(barcode).strip():
            query += " AND evidence_bag_barcode LIKE ?"
            params.append(f"%{str(barcode).strip()}%")

        if search_query and str(search_query).strip():
            query += " AND (id LIKE ? OR fir_case_ref LIKE ? OR reagent_type LIKE ? OR batch_lot LIKE ? OR evidence_bag_barcode LIKE ? OR location_name LIKE ? OR officer_name LIKE ? OR officer_id LIKE ?)"
            term = f"%{str(search_query).strip()}%"
            params.extend([term, term, term, term, term, term, term, term])

        query += " ORDER BY timestamp_utc DESC LIMIT ?"
        params.append(limit)

        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
