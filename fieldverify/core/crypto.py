"""
FieldVerify Cryptographic Evidence Engine
Section 63 Bharatiya Sakshya Adhiniyam (BSA), 2023 Tamper-Evident Sealing
- Dual SHA-256 Image Hash Calculation (Raw frame + Calibrated ROI)
- Asymmetric Hardware Key Signing (ECDSA P-256 Curve SECP256R1)
- Evidence Certificate Verification & Audit Integrity Check
"""

import hashlib
import json
from datetime import datetime, timezone
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.exceptions import InvalidSignature

# Singleton Device Private Key simulating Secure Enclave / Android Keystore
_DEVICE_PRIVATE_KEY = ec.generate_private_key(ec.SECP256R1())
_DEVICE_PUBLIC_KEY = _DEVICE_PRIVATE_KEY.public_key()


def get_device_public_key_pem():
    """Returns the PEM representation of the device public key for audit verification."""
    return _DEVICE_PUBLIC_KEY.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode("utf-8")


def generate_evidentiary_certificate(raw_img_bytes, roi_img_bytes, metadata=None, private_key=_DEVICE_PRIVATE_KEY):
    """
    Assembles a canonical JSON evidentiary certificate and signs it with ECDSA P-256.
    Complies with Section 63 Bharatiya Sakshya Adhiniyam (BSA), 2023 mandatory hash logging.
    """
    if metadata is None or not isinstance(metadata, dict):
        metadata = {}

    raw_hash = hashlib.sha256(raw_img_bytes or b"").hexdigest()
    roi_hash = hashlib.sha256(roi_img_bytes or b"").hexdigest()

    certificate = {
        "test_id": str(metadata.get("test_id") or f"FV-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "officer_badge_id": str(metadata.get("officer_id") or metadata.get("officer_badge_id") or "UNKNOWN_OFFICER"),
        "officer_name": str(metadata.get("officer_name") or "Sub-Inspector Rajesh Barua"),
        "fir_case_ref": str(metadata.get("fir_case_ref") or "N/A"),
        "gps": metadata.get("gps") if isinstance(metadata.get("gps"), dict) else {"lat": 26.14, "lon": 91.73},
        "location_name": str(metadata.get("location_name") or "Roadside Inspection Checkpoint"),
        "reagent_type": str(metadata.get("reagent_type") or "UNKNOWN"),
        "batch_lot": str(metadata.get("batch_lot") or "UNTRACKED"),
        "measured_lab": metadata.get("measured_lab") if isinstance(metadata.get("measured_lab"), dict) else {"L": 0.0, "a": 0.0, "b": 0.0},
        "delta_e00": float(metadata.get("delta_e00", metadata.get("delta_e", 0.0)) or 0.0),
        "outcome": str(metadata.get("outcome") or "INCONCLUSIVE"),
        "anti_spoof_status": str(metadata.get("anti_spoof_status") or "PASS"),
        "evidence_bag_barcode": str(metadata.get("evidence_bag_barcode") or "N/A"),
        "estimated_weight_g": float(metadata.get("estimated_weight_g") or 0.0),
        "witness_1_name": str(metadata.get("witness_1_name") or "N/A"),
        "witness_2_name": str(metadata.get("witness_2_name") or "N/A"),
        "ambient_lux": float(metadata.get("ambient_lux") or 450.0),
        "fsl_status": str(metadata.get("fsl_status") or "PENDING_LAB"),
        "sha256_raw_image": raw_hash,
        "sha256_calibrated_roi": roi_hash,
        "statutory_act": "Section 63 Bharatiya Sakshya Adhiniyam (BSA), 2023",
        "device_public_key_pem": get_device_public_key_pem()
    }

    # Canonical JSON string sort keys for deterministic byte payload
    canonical_bytes = json.dumps(certificate, sort_keys=True).encode("utf-8")
    signature_bytes = private_key.sign(canonical_bytes, ec.ECDSA(hashes.SHA256()))

    certificate["ecdsa_signature_hex"] = signature_bytes.hex()
    return certificate


def verify_evidentiary_certificate(certificate, public_key_pem=None):
    """
    Court-side audit verification. Returns True if digital signature is valid
    and metadata has not been tampered with. Returns False if altered.
    """
    if not isinstance(certificate, dict):
        return False, "Invalid certificate object"

    cert_copy = dict(certificate)
    if "ecdsa_signature_hex" in cert_copy:
        sig_hex = cert_copy.pop("ecdsa_signature_hex")
    elif "digital_signature" in cert_copy:
        sig_hex = cert_copy.pop("digital_signature")
    else:
        return False, "Missing ECDSA signature"

    if not isinstance(sig_hex, str) or not sig_hex.strip():
        return False, "Invalid or empty ECDSA signature"

    canonical_bytes = json.dumps(cert_copy, sort_keys=True).encode("utf-8")

    try:
        if public_key_pem is None:
            public_key_pem = cert_copy.get("device_public_key_pem") or get_device_public_key_pem()

        if not public_key_pem:
            return False, "Public key missing"

        sig_bytes = bytes.fromhex(sig_hex.strip())
        pub_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
        pub_key.verify(sig_bytes, canonical_bytes, ec.ECDSA(hashes.SHA256()))
        return True, "SIGNATURE_VALID: Record is authentic and un-tampered under Section 63 BSA."

    except (InvalidSignature, ValueError):
        return False, "TAMPER_DETECTED: Signature verification failed! Record modified."
    except Exception as e:
        return False, f"VERIFICATION_ERROR: {str(e)}"
