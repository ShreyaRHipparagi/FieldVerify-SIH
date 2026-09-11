"""
FieldVerify AI - Barcode & QR Code Processing Engine
Provides deterministic barcode/QR scanning from camera/images, evidence seal generation,
and verification for chain-of-custody tracking under the NDPS Act and BSA 2023.
"""

import cv2
import numpy as np
import qrcode
from typing import Optional, Dict, Any, Tuple
import io
from PIL import Image


def scan_barcode_or_qr_from_image(img_bgr: np.ndarray) -> Dict[str, Any]:
    """
    Scans and decodes any QR code or 1D barcode (Code 128, EAN-13, etc.)
    from an acquired camera frame or uploaded image.
    Returns dict with keys:
    - found: bool
    - text: decoded string
    - code_type: 'QR' | 'BARCODE' | None
    - bbox: bounding box coordinates if available
    """
    if img_bgr is None or not isinstance(img_bgr, np.ndarray) or img_bgr.size == 0:
        return {"found": False, "text": "", "code_type": None, "bbox": None}

    # 1. Attempt QR Code Detection via OpenCV QRCodeDetector
    try:
        qr_detector = cv2.QRCodeDetector()
        decoded_text, points, _ = qr_detector.detectAndDecode(img_bgr)
        if decoded_text and decoded_text.strip():
            return {
                "found": True,
                "text": decoded_text.strip(),
                "code_type": "QR",
                "bbox": points.tolist() if points is not None else None
            }
    except Exception:
        pass

    # 2. Attempt 1D/2D Barcode Detection via cv2.barcode
    try:
        if hasattr(cv2, "barcode") and hasattr(cv2.barcode, "BarcodeDetector"):
            barcode_detector = cv2.barcode.BarcodeDetector()
            ok, decoded_info, decoded_type, corners = barcode_detector.detectAndDecode(img_bgr)
            if ok and decoded_info:
                text = decoded_info[0] if isinstance(decoded_info, (list, tuple)) else decoded_info
                b_type = decoded_type[0] if isinstance(decoded_type, (list, tuple)) else decoded_type
                if text and str(text).strip():
                    return {
                        "found": True,
                        "text": str(text).strip(),
                        "code_type": f"BARCODE_{b_type}" if b_type else "BARCODE",
                        "bbox": corners.tolist() if corners is not None else None
                    }
    except Exception:
        pass

    # 3. Grayscale / Contrast enhanced fallback for low-light or angled scans
    try:
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        qr_detector = cv2.QRCodeDetector()
        decoded_text, points, _ = qr_detector.detectAndDecode(enhanced)
        if decoded_text and decoded_text.strip():
            return {
                "found": True,
                "text": decoded_text.strip(),
                "code_type": "QR",
                "bbox": points.tolist() if points is not None else None
            }
    except Exception:
        pass

    return {"found": False, "text": "", "code_type": None, "bbox": None}


def generate_barcode_qr_image(text: str, box_size: int = 6, border: int = 2) -> np.ndarray:
    """
    Generates a high-contrast QR/Barcode image from text (e.g. Evidence Bag Barcode or Reagent Lot).
    Returns BGR numpy array.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(text)
    qr.make(fit=True)
    pil_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    rgb_arr = np.array(pil_img)
    return cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2BGR)


def validate_evidence_bag_barcode(barcode: str) -> Dict[str, Any]:
    """
    Validates evidence bag barcode structure and returns sanitized barcode metadata.
    """
    s = str(barcode or "").strip().upper()
    if not s or s == "N/A":
        return {
            "is_valid": False,
            "barcode": "N/A",
            "error": "Evidence bag barcode is required for Section 63 BSA custody compliance."
        }
    if len(s) < 3:
        return {
            "is_valid": False,
            "barcode": s,
            "error": "Barcode number is too short."
        }
    return {
        "is_valid": True,
        "barcode": s,
        "error": None
    }
