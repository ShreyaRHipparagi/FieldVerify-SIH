"""
FieldVerify Reagent Profile Library & Batch Lot Expiry Parser
Defines certified presumptive reaction color standards under NIJ Standard 0604.01
and parses packaging QR codes for batch lot tracking and expiry checks.
"""

import json
from datetime import datetime, timezone

# Certified Presumptive Reagent Color Target Standards (CIELAB L*, a*, b*)
VALIDATED_REAGENT_LIBRARY = {
    "SCOTT_REAGENT": {
        "name": "Scott Reagent (Cobalt Thiocyanate)",
        "substance": "Cocaine HCl (Presumptive)",
        "target_lab": (30.0, 2.0, -52.0),   # Cobalt Blue
        "max_positive_delta_e": 6.5,
        "min_negative_delta_e": 16.0,
        "is_multi_phase": False
    },
    "MARQUIS_OPIATE": {
        "name": "Marquis Reagent (Opiates)",
        "substance": "Heroin / Morphine (Presumptive)",
        "target_lab": (22.0, 32.0, -28.0),  # Deep Violet
        "max_positive_delta_e": 6.0,
        "min_negative_delta_e": 15.0,
        "is_multi_phase": False
    },
    "MARQUIS_AMPHETAMINE": {
        "name": "Marquis Reagent (Amphetamines)",
        "substance": "Methamphetamine / MDMA (Presumptive)",
        "target_lab": (44.0, 42.0, 38.0),   # Orange-Brown
        "max_positive_delta_e": 7.0,
        "min_negative_delta_e": 15.0,
        "is_multi_phase": False
    },
    "DUQUENOIS_LEVINE": {
        "name": "Duquenois-Levine Reagent",
        "substance": "Cannabis / THC (Presumptive)",
        "target_lab": (24.0, 24.0, -32.0),  # Indigo-Violet (Lower Chloroform Layer)
        "max_positive_delta_e": 6.5,
        "min_negative_delta_e": 16.0,
        "is_multi_phase": True
    }
}


def parse_reagent_qr_data(qr_payload_str):
    """
    Parses reagent kit QR code payload (JSON or structured string).
    Expected JSON schema: {"reagent": "SCOTT_REAGENT", "lot": "SC-2026-0819", "exp": "2027-12-31"}
    Returns status dict with validation and lot expiry information.
    """
    if not qr_payload_str:
        return {
            "is_valid": False,
            "is_expired": False,
            "reagent_type": "UNKNOWN",
            "lot_number": "N/A",
            "expiry_date": "N/A",
            "error": "Empty QR code data."
        }

    try:
        if isinstance(qr_payload_str, dict):
            data = qr_payload_str
        else:
            data = json.loads(qr_payload_str)

        if not isinstance(data, dict):
            return {
                "is_valid": False,
                "is_expired": False,
                "reagent_type": "INVALID",
                "lot_number": "N/A",
                "expiry_date": "N/A",
                "error": "Invalid QR code payload: expected JSON object."
            }

        reagent_type = str(data.get("reagent", "")).upper()
        lot_number = str(data.get("lot", "UNTRACKED"))
        exp_str = data.get("exp", "")

        if reagent_type not in VALIDATED_REAGENT_LIBRARY:
            return {
                "is_valid": False,
                "is_expired": False,
                "reagent_type": reagent_type,
                "lot_number": lot_number,
                "expiry_date": exp_str,
                "error": f"Unrecognized reagent type '{reagent_type}'."
            }

        if not exp_str:
            return {
                "is_valid": False,
                "is_expired": False,
                "reagent_type": reagent_type,
                "lot_number": lot_number,
                "expiry_date": "N/A",
                "error": "Missing expiry date in reagent QR code."
            }

        try:
            exp_date = datetime.strptime(str(exp_str).strip(), "%Y-%m-%d").date()
            now_date = datetime.now(timezone.utc).date()
            is_expired = now_date > exp_date
        except (ValueError, TypeError):
            return {
                "is_valid": False,
                "is_expired": False,
                "reagent_type": reagent_type,
                "lot_number": lot_number,
                "expiry_date": exp_str,
                "error": f"Invalid expiry date format '{exp_str}'. Expected YYYY-MM-DD."
            }

        return {
            "is_valid": True,
            "is_expired": is_expired,
            "reagent_type": reagent_type,
            "lot_number": lot_number,
            "expiry_date": str(exp_str),
            "reagent_info": VALIDATED_REAGENT_LIBRARY[reagent_type],
            "error": "EXPIRED REAGENT KIT! Do not use for court evidence." if is_expired else None
        }

    except Exception as e:
        return {
            "is_valid": False,
            "is_expired": False,
            "reagent_type": "INVALID",
            "lot_number": "N/A",
            "expiry_date": "N/A",
            "error": f"Failed to parse QR code format: {str(e)}"
        }
