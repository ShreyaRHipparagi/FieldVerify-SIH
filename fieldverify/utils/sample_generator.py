"""
FieldVerify Synthetic Test Sample Generator
Creates realistic synthetic camera field photos for hackathon testing and UI demonstration:
- Cocaine Scott Reagent (Cobalt Blue Positive)
- Heroin Marquis Reagent (Deep Violet Positive)
- Cannabis Duquenois-Levine Reagent (Multi-phase Indigo-Violet Organic Layer)
- Negative Blank Reagent (Clear Non-reaction)
- Digital Screen Re-photography Spoof Attempt (Moiré pattern overlay)
"""

import cv2
import numpy as np
import os
import tempfile
from fieldverify.utils.card_generator import generate_reference_card

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_DEMO_DIR = os.path.join(PROJECT_ROOT, "demo_samples")


def create_synthetic_test_image(
    reagent_type="SCOTT_REAGENT",
    is_positive=True,
    is_multi_phase=False,
    is_screen_spoof=False,
    perspective_tilt=True,
    output_filename=None
):
    """
    Generates a full synthetic camera frame containing the reference card,
    simulated chemical reaction pouch with target colors, and perspective warp.
    """
    base_card_path = os.path.join(tempfile.gettempdir(), f"temp_ref_card_{os.getpid()}.png")
    generate_reference_card(base_card_path)
    card_img = cv2.imread(base_card_path)
    if os.path.exists(base_card_path):
        try:
            os.remove(base_card_path)
        except Exception:
            pass

    # Reaction Zone coordinates: x=450, y=150, w=300, h=300
    px, py, pw, ph = 450, 150, 300, 300

    # Draw Plastic Pouch outline
    pouch_overlay = card_img[py:py+ph, px:px+pw].copy()
    cv2.rectangle(pouch_overlay, (20, 20), (pw-20, ph-20), (220, 220, 220), -1)

    # Determine BGR color for simulation (calibrated to certified NIJ CIELAB targets)
    if not is_positive:
        liquid_bgr = (210, 210, 210) # Clear / colorless liquid
    elif reagent_type == "SCOTT_REAGENT":
        liquid_bgr = (124, 79, 0)    # Cobalt Blue (Target Lab 30, 2, -52)
    elif reagent_type == "MARQUIS_OPIATE":
        liquid_bgr = (95, 33, 78)    # Deep Violet (Target Lab 22, 32, -28)
    elif reagent_type == "MARQUIS_AMPHETAMINE":
        liquid_bgr = (42, 70, 177)   # Orange-Brown (Target Lab 44, 42, 38)
    elif reagent_type == "DUQUENOIS_LEVINE" or is_multi_phase:
        liquid_bgr = (106, 46, 66)   # Indigo-Violet Organic Phase (Target Lab 24, 24, -32)
    else:
        liquid_bgr = (124, 79, 0)

    # Fill reaction liquid
    if is_multi_phase:
        # Multi-phase: top layer clear/yellowish, bottom layer deep indigo-violet
        mid_y = ph // 2
        cv2.rectangle(pouch_overlay, (40, 40), (pw-40, mid_y), (180, 220, 230), -1) # Top aqueous
        cv2.rectangle(pouch_overlay, (40, mid_y), (pw-40, ph-40), liquid_bgr, -1)  # Bottom organic
        cv2.line(pouch_overlay, (35, mid_y), (pw-35, mid_y), (100, 100, 100), 2)  # Phase interface line
    else:
        cv2.rectangle(pouch_overlay, (40, 40), (pw-40, ph-40), liquid_bgr, -1)

    # Add realistic plastic specular glare reflection
    cv2.ellipse(pouch_overlay, (pw//2 - 20, py//2 + 30), (70, 15), -30, 0, 360, (255, 255, 255), -1)
    cv2.rectangle(pouch_overlay, (20, 20), (pw-20, ph-20), (140, 140, 140), 3)

    card_img[py:py+ph, px:px+pw] = pouch_overlay

    # Add background canvas padding (simulating roadside table / ground)
    canvas_w, canvas_h = 1200, 800
    canvas = np.full((canvas_h, canvas_w, 3), (40, 45, 50), dtype=np.uint8) # Dark asphalt background

    if perspective_tilt:
        # Perspective transform simulation (tilted phone shot)
        src_pts = np.array([[0, 0], [1000, 0], [1000, 600], [0, 600]], dtype=np.float32)
        dst_pts = np.array([[150, 120], [1050, 90], [980, 720], [110, 680]], dtype=np.float32)
        H = cv2.getPerspectiveTransform(src_pts, dst_pts)
        warped_card = cv2.warpPerspective(card_img, H, (canvas_w, canvas_h))
        mask = cv2.warpPerspective(np.ones((600, 1000, 3), dtype=np.uint8)*255, H, (canvas_w, canvas_h))
        canvas = np.where(mask > 0, warped_card, canvas)
    else:
        canvas[100:700, 100:1100] = card_img

    if is_screen_spoof:
        # Overlay high-frequency Moiré grid lines to simulate screen re-photography
        for x in range(0, canvas_w, 3):
            cv2.line(canvas, (x, 0), (x, canvas_h), (255, 255, 255), 1)
        for y in range(0, canvas_h, 3):
            cv2.line(canvas, (0, y), (canvas_w, y), (200, 200, 200), 1)

    if output_filename:
        cv2.imwrite(output_filename, canvas)

    return canvas


def generate_all_demo_samples(output_dir=None):
    """Generates a complete suite of synthetic demo images."""
    if output_dir is None:
        output_dir = DEFAULT_DEMO_DIR

    os.makedirs(output_dir, exist_ok=True)

    samples = [
        ("cocaine_scott_positive.png", "SCOTT_REAGENT", True, False, False),
        ("heroin_marquis_positive.png", "MARQUIS_OPIATE", True, False, False),
        ("cannabis_duquenois_multiphase.png", "DUQUENOIS_LEVINE", True, True, False),
        ("negative_blank_test.png", "SCOTT_REAGENT", False, False, False),
        ("screen_spoof_attempt.png", "SCOTT_REAGENT", True, False, True),
    ]

    generated_paths = []
    for filename, reagent, is_pos, is_multi, is_spoof in samples:
        path = os.path.join(output_dir, filename)
        create_synthetic_test_image(
            reagent_type=reagent,
            is_positive=is_pos,
            is_multi_phase=is_multi,
            is_screen_spoof=is_spoof,
            output_filename=path
        )
        generated_paths.append(path)

    return generated_paths


if __name__ == "__main__":
    generate_all_demo_samples()
    print("Demo samples generated in demo_samples/")
