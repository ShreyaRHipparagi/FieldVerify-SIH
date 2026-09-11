"""
FieldVerify CFSL / State FSL Confirmatory Laboratory Reconciliation Module
Allows Forensic Science Laboratory examiners to review roadside presumptive field tests,
enter confirmatory Gas Chromatography-Mass Spectrometry (GC-MS) or HPLC analytical reports,
and permanently reconcile judicial records under Section 293 CrPC / Section 63 BSA.
"""

import sqlite3
import os
from datetime import datetime, timezone

from fieldverify.core.db import init_db

DB_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "fieldverify_ledger.db")


def submit_fsl_confirmatory_report(
    test_id,
    chemist_id,
    chemist_name,
    lab_name,
    analytical_method,       # e.g., "GC-MS (Gas Chromatography - Mass Spectrometry)"
    molecular_identification, # e.g., "Cocaine Hydrochloride (C17H21NO4)"
    purity_percentage,       # e.g., 84.5
    fsl_verdict,             # "CONFIRMED_POSITIVE", "FALSE_POSITIVE", "INCONCLUSIVE"
    remarks="",
    db_path=DB_FILE_PATH
):
    """
    Records laboratory confirmation into the local judicial audit ledger.
    """
    init_db(db_path)
    conn = sqlite3.connect(db_path, timeout=30.0)
    try:
        now_iso = datetime.now(timezone.utc).isoformat()
        try:
            purity_val = float(purity_percentage)
        except (ValueError, TypeError):
            purity_val = 0.0

        with conn:
            cursor = conn.execute("""
            UPDATE test_records SET
                fsl_status = ?,
                fsl_chemist = ?,
                fsl_lab_name = ?,
                fsl_method = ?,
                fsl_confirmed_substance = ?,
                fsl_purity = ?,
                fsl_timestamp = ?,
                fsl_notes = ?
            WHERE id = ?
            """, (
                str(fsl_verdict),
                f"{chemist_name} ({chemist_id})",
                str(lab_name),
                str(analytical_method),
                str(molecular_identification),
                purity_val,
                now_iso,
                str(remarks),
                str(test_id)
            ))

            success = cursor.rowcount > 0

        return {
            "success": success,
            "test_id": test_id,
            "status": fsl_verdict,
            "timestamp": now_iso,
            "message": f"Successfully linked CFSL report to Seizure Certificate {test_id}." if success else f"Record {test_id} not found."
        }
    finally:
        conn.close()
