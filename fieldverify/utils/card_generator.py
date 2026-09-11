"""
FieldVerify Passive Reference Card Generator
Generates a printable ID-1 format card (1000x600 px canvas) with 4 ArUco markers (DICT_4X4_50)
and certified color swatches for lighting calibration.
"""

import cv2
import numpy as np
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_CARD_PATH = os.path.join(PROJECT_ROOT, "fieldverify_reference_card.png")


def generate_reference_card(output_path=None):
    """Creates a 1000x600 reference card image with 4 ArUco markers and calibration patches."""
    if output_path is None:
        output_path = DEFAULT_CARD_PATH

    card_w, card_h = 1000, 600
    card = np.full((card_h, card_w, 3), 245, dtype=np.uint8) # Off-white cardstock background

    # 1. Generate ArUco Markers
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    marker_size = 100

    def draw_marker(marker_id, top_left_x, top_left_y):
        marker_img = cv2.aruco.generateImageMarker(aruco_dict, marker_id, marker_size)
        marker_bgr = cv2.cvtColor(marker_img, cv2.COLOR_GRAY2BGR)
        card[top_left_y:top_left_y+marker_size, top_left_x:top_left_x+marker_size] = marker_bgr

    # Corner positions
    draw_marker(0, 20, 20)       # Top-Left (ID 0)
    draw_marker(1, 880, 20)      # Top-Right (ID 1)
    draw_marker(2, 880, 480)     # Bottom-Right (ID 2)
    draw_marker(3, 20, 480)      # Bottom-Left (ID 3)

    # 2. Draw Certified Color Calibration Swatches
    # White Swatch (95% reflectance): RGB (242, 242, 242)
    cv2.rectangle(card, (150, 450), (230, 530), (242, 242, 242), -1)
    cv2.rectangle(card, (150, 450), (230, 530), (100, 100, 100), 1)
    cv2.putText(card, "95% WHITE", (155, 545), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (50, 50, 50), 1)

    # Gray Swatch (18% reflectance): RGB (118, 118, 118)
    cv2.rectangle(card, (250, 450), (330, 530), (118, 118, 118), -1)
    cv2.rectangle(card, (250, 450), (330, 530), (100, 100, 100), 1)
    cv2.putText(card, "18% GRAY", (255, 545), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (50, 50, 50), 1)

    # Black Swatch (5% reflectance): RGB (20, 20, 20)
    cv2.rectangle(card, (350, 450), (430, 530), (20, 20, 20), -1)
    cv2.rectangle(card, (350, 450), (430, 530), (100, 100, 100), 1)
    cv2.putText(card, "5% BLACK", (355, 545), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (50, 50, 50), 1)

    # 3. Draw Chemical Reaction Pouch Reticle Bounding Zone
    px, py, pw, ph = 450, 150, 300, 300
    cv2.rectangle(card, (px, py), (px+pw, py+ph), (0, 140, 255), 2)
    cv2.putText(card, "PLACE REACTION POUCH HERE", (px+20, py-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 100, 200), 2)

    # Card Title Header
    cv2.putText(card, "FIELDVERIFY PASSIVE REFERENCE CARD (ID-1)", (150, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (30, 41, 59), 2)
    cv2.putText(card, "Sec 63 BSA Calibrated Optical Target | DICT_4X4_50", (150, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (71, 85, 105), 1)

    cv2.imwrite(output_path, card)
    return output_path


if __name__ == "__main__":
    generate_reference_card()
    print("Reference card generated at fieldverify_reference_card.png")
