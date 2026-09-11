"""
FieldVerify Core Optical Engine
Deterministic Computer Vision & Forensic Color Science Pipeline
- Homography Perspective Rectification via ArUco Fiducials
- von Kries White-Balance Chromatic Gain Normalization
- Specular Glare Elimination
- Multi-Phase Liquid Layer Extraction (Duquenois-Levine organic phase)
- Anti-Spoofing Screen Re-photography Moiré & FFT Detection
- CIEDE2000 Delta-E (ΔE00) Perceptual Color Metric
"""

import cv2
import numpy as np
import math


def ciede2000(lab1, lab2):
    """
    Calculates exact CIEDE2000 color difference between two (L*, a*, b*) tuples.
    Based on CIE 15:2004 / ISO 11664-6 standard.
    """
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2

    avg_L = (L1 + L2) / 2.0
    C1 = math.sqrt(a1**2 + b1**2)
    C2 = math.sqrt(a2**2 + b2**2)
    avg_C = (C1 + C2) / 2.0

    G = 0.5 * (1.0 - math.sqrt((avg_C**7) / (avg_C**7 + 25.0**7 + 1e-9)))
    a1_p = (1.0 + G) * a1
    a2_p = (1.0 + G) * a2

    C1_p = math.sqrt(a1_p**2 + b1**2)
    C2_p = math.sqrt(a2_p**2 + b2**2)
    avg_C_p = (C1_p + C2_p) / 2.0

    h1_p = math.degrees(math.atan2(b1, a1_p)) % 360
    h2_p = math.degrees(math.atan2(b2, a2_p)) % 360

    if abs(h1_p - h2_p) <= 180:
        avg_h_p = (h1_p + h2_p) / 2.0
    else:
        avg_h_p = (h1_p + h2_p + 360) / 2.0 if (h1_p + h2_p) < 360 else (h1_p + h2_p - 360) / 2.0

    T = (1.0 - 0.17 * math.cos(math.radians(avg_h_p - 30))
           + 0.24 * math.cos(math.radians(2 * avg_h_p))
           + 0.32 * math.cos(math.radians(3 * avg_h_p + 6))
           - 0.20 * math.cos(math.radians(4 * avg_h_p - 63)))

    delta_h_p = h2_p - h1_p
    if abs(delta_h_p) > 180:
        delta_h_p += 360 if h2_p <= h1_p else -360

    delta_L_p = L2 - L1
    delta_C_p = C2_p - C1_p
    delta_H_p = 2.0 * math.sqrt(C1_p * C2_p + 1e-9) * math.sin(math.radians(delta_h_p / 2.0))

    S_L = 1.0 + ((0.015 * ((avg_L - 50.0)**2)) / math.sqrt(20.0 + ((avg_L - 50.0)**2)))
    S_C = 1.0 + 0.045 * avg_C_p
    S_H = 1.0 + 0.015 * avg_C_p * T

    delta_theta = 30.0 * math.exp(-(((avg_h_p - 275.0) / 25.0)**2))
    R_C = 2.0 * math.sqrt((avg_C_p**7) / (avg_C_p**7 + 25.0**7 + 1e-9))
    R_T = -math.sin(math.radians(2 * delta_theta)) * R_C

    dE = math.sqrt(
        (delta_L_p / S_L)**2 +
        (delta_C_p / S_C)**2 +
        (delta_H_p / S_H)**2 +
        R_T * (delta_C_p / S_C) * (delta_H_p / S_H)
    )
    return round(dE, 2)


def srgb_to_lab(bgr_color):
    """
    Converts a BGR float/int tuple [B, G, R] to CIE L*a*b* using D65 reference white.
    """
    b, g, r = [float(x) / 255.0 for x in bgr_color]

    # Linearize sRGB channels
    def linearize(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r_l, g_l, b_l = linearize(r), linearize(g), linearize(b)

    # sRGB to XYZ (CIE 1931 D65)
    X = r_l * 0.4124564 + g_l * 0.3575761 + b_l * 0.1804375
    Y = r_l * 0.2126729 + g_l * 0.7151522 + b_l * 0.0721750
    Z = r_l * 0.0193339 + g_l * 0.1191920 + b_l * 0.9503041

    # D65 Tristimulus Values
    X /= 0.95047
    Y /= 1.00000
    Z /= 1.08883

    def f(t):
        return t ** (1.0 / 3.0) if t > 0.008856 else (7.787037 * t) + (16.0 / 116.0)

    fx, fy, fz = f(X), f(Y), f(Z)
    L = (116.0 * fy) - 16.0
    a = 500.0 * (fx - fy)
    b_val = 200.0 * (fy - fz)

    return round(L, 2), round(a, 2), round(b_val, 2)


def detect_screen_spoofing(image_bgr):
    """
    Analyzes high-frequency FFT power spectrum and Moiré pattern artifacts
    to determine if the photo was taken off a digital phone/laptop screen.
    Returns: (is_spoof: bool, score: float, reason: str)
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    # 1. Laplacian Variance Blur/Grid Test
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()

    # 2. 2D Fast Fourier Transform (FFT) for periodic Moiré patterns
    dft = np.fft.fft2(gray)
    dft_shift = np.fft.fftshift(dft)
    magnitude_spectrum = 20 * np.log(np.abs(dft_shift) + 1e-9)

    # High frequency energy ratio
    cy, cx = h // 2, w // 2
    r = min(h, w) // 8
    # Mask out DC and low frequencies
    magnitude_spectrum_high = magnitude_spectrum.copy()
    cv2.circle(magnitude_spectrum_high, (cx, cy), r, 0, -1)

    high_freq_peaks = np.percentile(magnitude_spectrum_high, 99.8)

    # Screen re-photography often introduces sharp periodic grid spikes in high frequencies
    # or unusual peak energy density combined with high Laplacian grid contrast.
    is_spoof = False
    reasons = []

    if high_freq_peaks > 220.0 and laplacian_var > 1500.0:
        is_spoof = True
        reasons.append(f"Moiré screen grid artifact detected (FFT peak={high_freq_peaks:.1f})")

    score = round(float(high_freq_peaks), 2)
    reason_str = " | ".join(reasons) if is_spoof else "Physical sample authentic (No screen Moiré grid detected)"
    return is_spoof, score, reason_str


def check_ambient_lighting(image_bgr, rectified_card=None):
    """
    Evaluates ambient scene illumination using standard CIE 1931 photopic luminance (Y)
    and gray card reflectance.
    Returns:
        dict with status ('OPTIMAL', 'TOO_DARK', 'TOO_BRIGHT'),
        estimated_lux, message, and recommendation.
    """
    if rectified_card is not None:
        # Sample the 18% Neutral Gray swatch on the rectified card: x=250, y=450, w=80, h=80
        gx, gy, gw, gh = 250, 450, 80, 80
        gray_patch = rectified_card[gy:gy+gh, gx:gx+gw]
        b = np.mean(gray_patch[:, :, 0])
        g = np.mean(gray_patch[:, :, 1])
        r = np.mean(gray_patch[:, :, 2])
        # Photopic luminance Y = 0.2126 R + 0.7152 G + 0.0722 B
        lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    else:
        # Overall image luminance
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        lum = float(np.mean(gray))

    # Calibrated empirical lux mapping from 8-bit luminance
    # Reference: 18% gray at standard daylight/office lighting ~ 118 RGB (approx 300 - 500 lux)
    estimated_lux = round(float((lum / 118.0) * 450.0), 1)

    if lum < 35.0 or estimated_lux < 50.0:
        status = "TOO_DARK"
        rec = "FLASHLIGHT_REQUIRED"
        msg = f"Ambient light is too dim ({estimated_lux} lux). Turn on phone flashlight or move to lit area."
    elif lum > 230.0 or estimated_lux > 1200.0:
        status = "TOO_BRIGHT"
        rec = "MOVE_TO_SHADE"
        msg = f"Extreme direct glare/sunlight ({estimated_lux} lux). Move card to shade to avoid sensor saturation."
    else:
        status = "OPTIMAL"
        rec = "PROCEED"
        msg = f"Lighting is optimal for forensic colorimetric analysis ({estimated_lux} lux)."

    return {
        "status": status,
        "recommendation": rec,
        "estimated_lux": estimated_lux,
        "luminance_value": round(float(lum), 1),
        "message": msg
    }



def rectify_reference_card(image_bgr, target_w=1000, target_h=600):
    """
    Detects 4 corner ArUco fiducials (DICT_4X4_50, IDs 0=TL, 1=TR, 2=BR, 3=BL)
    and warps perspective into a flat top-down canvas.
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    parameters = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)

    corners, ids, _ = detector.detectMarkers(gray)
    if ids is None or len(ids) < 4:
        raise ValueError("Could not find all 4 corner ArUco fiducials (IDs 0, 1, 2, 3). Frame reference card properly.")

    marker_centers = {}
    for i, marker_id in enumerate(ids.flatten()):
        c = corners[i][0]
        center_x = float(np.mean(c[:, 0]))
        center_y = float(np.mean(c[:, 1]))
        marker_centers[int(marker_id)] = [center_x, center_y]

    for req_id in [0, 1, 2, 3]:
        if req_id not in marker_centers:
            raise ValueError(f"Missing required ArUco marker ID {req_id}. Ensure top-left=0, top-right=1, bottom-right=2, bottom-left=3.")

    src_pts = np.array([
        marker_centers[0],
        marker_centers[1],
        marker_centers[2],
        marker_centers[3]
    ], dtype=np.float32)

    dst_pts = np.array([
        [0, 0],
        [target_w, 0],
        [target_w, target_h],
        [0, target_h]
    ], dtype=np.float32)

    H = cv2.getPerspectiveTransform(src_pts, dst_pts)
    rectified = cv2.warpPerspective(image_bgr, H, (target_w, target_h))
    return rectified


def calibrate_and_extract_color(rectified_img, is_multi_phase=False):
    """
    Performs:
    1. von Kries White Balance gain calibration using 95% White Swatch.
    2. Glare elimination in HSV space.
    3. Multi-phase liquid separation boundary extraction (if required, e.g. Duquenois-Levine).
    4. sRGB to CIELAB conversion of extracted valid pixels.
    """
    target_w, target_h = 1000, 600

    # Card ROI Layout:
    # White Patch ROI: x=150, y=450, w=80, h=80
    WHITE_PATCH_ROI = (150, 450, 80, 80)
    # Reaction Zone ROI: x=450, y=150, w=300, h=300
    POUCH_ZONE_ROI = (450, 150, 300, 300)

    # 1. Sample White Patch
    wx, wy, ww, wh = WHITE_PATCH_ROI
    white_crop = rectified_img[wy:wy+wh, wx:wx+ww]
    mean_b = float(np.mean(white_crop[:, :, 0]))
    mean_g = float(np.mean(white_crop[:, :, 1]))
    mean_r = float(np.mean(white_crop[:, :, 2]))

    # Target 95% White RGB value: 242.0
    gain_b = 242.0 / max(mean_b, 1.0)
    gain_g = 242.0 / max(mean_g, 1.0)
    gain_r = 242.0 / max(mean_r, 1.0)

    # 2. Sample Reaction Zone & Apply Gains
    px, py, pw, ph = POUCH_ZONE_ROI
    pouch_crop = rectified_img[py:py+ph, px:px+pw]

    calibrated_pouch = pouch_crop.astype(np.float32)
    calibrated_pouch[:, :, 0] = np.clip(calibrated_pouch[:, :, 0] * gain_b, 0, 255)
    calibrated_pouch[:, :, 1] = np.clip(calibrated_pouch[:, :, 1] * gain_g, 0, 255)
    calibrated_pouch[:, :, 2] = np.clip(calibrated_pouch[:, :, 2] * gain_r, 0, 255)
    calibrated_pouch = calibrated_pouch.astype(np.uint8)

    # 3. Specular Glare Masking (HSV space)
    hsv = cv2.cvtColor(calibrated_pouch, cv2.COLOR_BGR2HSV)
    v_channel = hsv[:, :, 2]
    s_channel = hsv[:, :, 1]
    glare_mask = (v_channel >= 235) | (s_channel < 30)
    valid_mask = ~glare_mask

    total_pixels = pw * ph
    glare_pixels = int(np.sum(glare_mask))
    glare_percentage = round((glare_pixels / total_pixels) * 100.0, 1)

    if glare_percentage > 45.0:
        raise ValueError(f"Excessive specular glare ({glare_percentage}%). Tilt camera slightly to avoid reflections.")

    # 4. Multi-Phase Boundary Extraction (Duquenois-Levine Organic Bottom Phase)
    phase_boundary_y = None
    if is_multi_phase:
        # Duquenois-Levine test separates into top aqueous layer and bottom chloroform layer.
        # We compute vertical color gradient down the valid rows of the pouch.
        row_b_means = [np.mean(calibrated_pouch[r, valid_mask[r, :], 0]) if np.any(valid_mask[r, :]) else 0 for r in range(ph)]
        row_gradients = np.abs(np.diff(row_b_means))
        if len(row_gradients) > 0:
            phase_boundary_y = int(np.argmax(row_gradients)) + 1
            # For Duquenois-Levine, the lower phase is the bottom organic layer (y from phase_boundary_y to ph)
            lower_phase_mask = np.zeros_like(valid_mask)
            lower_phase_mask[phase_boundary_y:, :] = valid_mask[phase_boundary_y:, :]
            if np.sum(lower_phase_mask) > 50:
                valid_mask = lower_phase_mask

    valid_pixels = calibrated_pouch[valid_mask]
    if len(valid_pixels) < 100:
        raise ValueError("Insufficient valid reaction liquid pixels. Ensure pouch is positioned inside reaction reticle.")

    median_bgr = np.median(valid_pixels, axis=0)
    measured_lab = srgb_to_lab(median_bgr)

    return {
        "calibrated_pouch": calibrated_pouch,
        "measured_lab": measured_lab,
        "median_bgr": [round(float(c), 1) for c in median_bgr],
        "glare_percentage": glare_percentage,
        "white_gains": {"k_R": round(gain_r, 3), "k_G": round(gain_g, 3), "k_B": round(gain_b, 3)},
        "is_multi_phase": is_multi_phase,
        "phase_boundary_y": phase_boundary_y
    }
