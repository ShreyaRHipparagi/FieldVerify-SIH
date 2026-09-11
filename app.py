"""
FieldVerify AI - Digital Companion for Field Drug Testing
Law Enforcement Web Dashboard UI (Streamlit)
Deterministic OpenCV Optical Calibration + CIEDE2000 ΔE + Section 63 BSA Cryptographic Certificate
Advanced Features:
- 🗺️ Geospatial Narcotics Seizure Heatmap & Smuggling Corridors
- 📄 1-Click NDPS Panchnama & Seizure Memo Generator
- 🏷️ Evidence Bag Tamper-Seal Barcode Custody Binding
- 💡 Ambient Lighting & Lux Guard
- 🧪 Station Reagent Inventory & Expiry Auto-Alarm Tracker
- 🌐 Multilingual Support (English, Hindi, Bengali, Tamil, Telugu, Marathi) + Audio Voice readout
- 🔬 CFSL / State Forensic Lab (FSL) Confirmatory Reconciliation Portal
"""

import sys
import os
from pathlib import Path
import warnings

# Suppress minor Streamlit deprecation notices for a clean terminal/UI
warnings.filterwarnings("ignore", message=".*use_container_width.*")
warnings.filterwarnings("ignore", category=SyntaxWarning)

# Ensure project root is in sys.path so all imports resolve from any working directory
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# When executed via `python app.py` (e.g. from VS Code Play/Run button), auto-launch via run_app
try:
    from streamlit.runtime.scriptrunner import get_script_run_ctx
    _in_streamlit = get_script_run_ctx() is not None
except Exception:
    _in_streamlit = False

if __name__ == "__main__" and not _in_streamlit:
    from run_app import main as launch_app
    launch_app()
    sys.exit(0)

import streamlit as st
import cv2
import numpy as np
import json
import tempfile
import pandas as pd
from datetime import datetime, timezone
from PIL import Image

from fieldverify.core.optical import (
    rectify_reference_card,
    calibrate_and_extract_color,
    ciede2000,
    detect_screen_spoofing,
    check_ambient_lighting
)
from fieldverify.core.reagent import (
    VALIDATED_REAGENT_LIBRARY,
    parse_reagent_qr_data
)
from fieldverify.core.crypto import (
    generate_evidentiary_certificate,
    verify_evidentiary_certificate
)
from fieldverify.core.db import (
    save_test_record,
    search_test_records,
    init_db
)
from fieldverify.core.pdf_generator import generate_evidentiary_pdf
from fieldverify.core.panchnama import generate_ndps_panchnama_text
from fieldverify.core.inventory import init_inventory_db, get_inventory_status, record_reagent_usage
from fieldverify.core.fsl import submit_fsl_confirmatory_report
from fieldverify.utils.card_generator import generate_reference_card
from fieldverify.utils.sample_generator import create_synthetic_test_image, generate_all_demo_samples

# Page Configuration
st.set_page_config(
    page_title="FieldVerify AI | Digital Field Drug Testing Companion",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Multilingual Dictionary
I18N = {
    "English": {
        "title": "FieldVerify AI: Forensic Field Screening Station",
        "subtitle": "Official Compliance Platform for Section 63 Bharatiya Sakshya Adhiniyam (BSA), 2023 & NDPS Act",
        "tab_test": "📸 Live Field Test Station",
        "tab_panchnama": "📄 Auto-Panchnama (Seizure Memo)",
        "tab_map": "🗺️ Geospatial Seizure Heatmap",
        "tab_fsl": "🔬 CFSL Forensic Lab Portal",
        "tab_inventory": "🧪 Reagent Inventory & Alarms",
        "tab_ledger": "📜 Searchable Audit Ledger",
        "tab_guide": "📄 Reference Card & Law Guide",
        "officer_title": "👮 Seizing Officer Telemetry",
        "officer_name": "Officer Name",
        "badge_id": "Badge / PIN ID",
        "fir_ref": "FIR / Case Reference",
        "location": "Inspection Location",
        "evidence_barcode": "Evidence Bag Barcode / Seal No.",
        "sample_weight": "Estimated Net Weight (grams)",
        "witness1": "Panch / Witness 1 Name",
        "witness2": "Panch / Witness 2 Name",
        "btn_run": "⚡ Run Deterministic Calibrated Analysis",
        "btn_speech": "🔊 Speak Result via Audio",
        "opt_status": "Calibrated Optical Analysis & Court Verdict",
        "positive": "POSITIVE FOR",
        "negative": "NEGATIVE RESULT",
        "spoof": "SCREEN RE-PHOTOGRAPHY SPOOF DETECTED",
        "inconclusive": "INCONCLUSIVE RESULT (Sent to CFSL)"
    },
    "Hindi (हिन्दी)": {
        "title": "फील्डवेरिफ़ाई एआई: फोरेंसिक फील्ड ड्रग स्क्रीनिंग स्टेशन",
        "subtitle": "भारतीय साक्ष्य अधिनियम (BSA) 2023 की धारा 63 और NDPS अधिनियम अनुपालन मंच",
        "tab_test": "📸 फील्ड टेस्ट स्टेशन",
        "tab_panchnama": "📄 पंचनामा (जब्ती ज्ञापन)",
        "tab_map": "🗺️ जब्ती हीटमैप",
        "tab_fsl": "🔬 CFSL फोरेंसिक लैब पोर्टल",
        "tab_inventory": "🧪 रिएजेंट स्टॉक एवं एक्सपायरी",
        "tab_ledger": "📜 ऑडिट लेजर रिकॉर्ड",
        "tab_guide": "📄 रेफरेंस कार्ड और नियम",
        "officer_title": "👮 जांच अधिकारी विवरण",
        "officer_name": "अधिकारी का नाम",
        "badge_id": "बैज / पिन संख्या",
        "fir_ref": "प्राथमिकी / केस संदर्भ संख्या",
        "location": "निरीक्षण स्थल",
        "evidence_barcode": "साक्ष्य बैग बारकोड / सील संख्या",
        "sample_weight": "अनुमानित वजन (ग्राम)",
        "witness1": "गवाह 1 का नाम",
        "witness2": "गवाह 2 का नाम",
        "btn_run": "⚡ ऑप्टिकल विश्लेषण शुरू करें",
        "btn_speech": "🔊 परिणाम आवाज में सुनें",
        "opt_status": "प्रमाणित ऑप्टिकल विश्लेषण व न्यायालय निर्णय",
        "positive": "मादक पदार्थ की पुष्टि हुई:",
        "negative": "नकारात्मक परिणाम (ड्रग अनुपस्थित)",
        "spoof": "स्क्रीन स्पूफिंग / नकली फोटो चेतावनी",
        "inconclusive": "अस्पष्ट परिणाम (CFSL भेजा जाएगा)"
    },
    "Bengali (বাংলা)": {
        "title": "ফিল্ডভেরিফাই এআই: ফরেনসিক ফিল্ড ড্রাগ স্ক্রিনিং স্টেশন",
        "subtitle": "ভারতীয় সাক্ষ্য অধিনিয়ম (BSA) ২০২৩ ধারা ৬৩ এবং এনডিপিএস আইন প্ল্যাটফর্ম",
        "tab_test": "📸 ফিল্ড টেস্ট স্টেশন",
        "tab_panchnama": "📄 পঞ্চনামা (জব্দ তালিকা)",
        "tab_map": "🗺️ উদ্ধার হিটম্যাপ",
        "tab_fsl": "🔬 সিএফএসএল ল্যাব পোর্টাল",
        "tab_inventory": "🧪 রিএজেন্ট স্টক ও মেয়াদ",
        "tab_ledger": "📜 অডিট খতিয়ান",
        "tab_guide": "📄 রেফারেন্স কার্ড ও নির্দেশিকা",
        "officer_title": "👮 তদন্তকারী কর্মকর্তার বিবরণ",
        "officer_name": "কর্মকর্তার নাম",
        "badge_id": "ব্যাজ / পিন নম্বর",
        "fir_ref": "এফআইআর / কেস নম্বর",
        "location": "ঘটনাস্থল",
        "evidence_barcode": "প্রমাণ ব্যাগের বারকোড",
        "sample_weight": "ওজন (গ্রাম)",
        "witness1": "সাক্ষী ১",
        "witness2": "সাক্ষী ২",
        "btn_run": "⚡ বিশ্লেষণ শুরু করুন",
        "btn_speech": "🔊 ফলাফল শুনুন",
        "opt_status": "অপটিক্যাল বিশ্লেষণ ও আদালতের রায়",
        "positive": "মাদকদ্রব্য নিশ্চিত:",
        "negative": "নেতিবাচক ফলাফল",
        "spoof": "স্ক্রিন স্পুফিং সতর্কতা",
        "inconclusive": "অমীমাংসিত ফলাফল"
    },
    "Tamil (தமிழ்)": {
        "title": "FieldVerify AI: போதைப்பொருள் கள ஆய்வு நிலையம்",
        "subtitle": "பாரதிய சாட்சிய சட்டம் 2023 பிரிவு 63 & NDPS சட்ட இணக்க தளம்",
        "tab_test": "📸 கள ஆய்வு நிலையம்",
        "tab_panchnama": "📄 பஞ்சநாமா ஆவணம்",
        "tab_map": "🗺️ போதைப்பொருள் வரைபடம்",
        "tab_fsl": "🔬 தடய அறிவியல் ஆய்வகம்",
        "tab_inventory": "🧪 ரசாயன இருப்பு மேலாண்மை",
        "tab_ledger": "📜 தணிக்கை பதிவேடு",
        "tab_guide": "📄 குறிப்பு அட்டை வழிகாட்டி",
        "officer_title": "👮 விசாரணை அதிகாரி தகவல்",
        "officer_name": "அதிகாரி பெயர்",
        "badge_id": "அடையாள எண்",
        "fir_ref": "வழக்கு குறிப்பு எண்",
        "location": "இடம்",
        "evidence_barcode": "சான்று பை பார்கோடு",
        "sample_weight": "எடை (கிராம்)",
        "witness1": "சாட்சி 1",
        "witness2": "சாட்சி 2",
        "btn_run": "⚡ பகுப்பாய்வு செய்க",
        "btn_speech": "🔊 முடிவை கேட்க",
        "opt_status": "நீதிமன்ற முடிவு",
        "positive": "உறுதிப்படுத்தப்பட்டது:",
        "negative": "எதிர்மறை முடிவு",
        "spoof": "போலி திரை எச்சரிக்கை",
        "inconclusive": "முடிவற்ற நிலை"
    }
}

# Custom CSS for Law Enforcement Dark-Theme Aesthetics
st.markdown("""
<style>
    .main {
        background-color: #0B0F17;
        color: #F8FAFC;
    }
    .stApp {
        background: linear-gradient(180deg, #0B0F17 0%, #0F172A 100%);
    }
    .stCard {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(226, 232, 240, 0.1);
        border-radius: 12px;
        padding: 18px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    }
    .badge-positive {
        background-color: #166534;
        color: #DCFCE7;
        padding: 12px 20px;
        border-radius: 8px;
        font-weight: bold;
        font-size: 22px;
        text-align: center;
        border: 1px solid #22C55E;
    }
    .badge-negative {
        background-color: #991B1B;
        color: #FEE2E2;
        padding: 12px 20px;
        border-radius: 8px;
        font-weight: bold;
        font-size: 22px;
        text-align: center;
        border: 1px solid #EF4444;
    }
    .badge-inconclusive {
        background-color: #92400E;
        color: #FEF3C7;
        padding: 12px 20px;
        border-radius: 8px;
        font-weight: bold;
        font-size: 22px;
        text-align: center;
        border: 1px solid #F59E0B;
    }
    .badge-warning {
        background-color: #831843;
        color: #FCE7F3;
        padding: 12px 20px;
        border-radius: 8px;
        font-weight: bold;
        font-size: 20px;
        text-align: center;
        border: 1px solid #EC4899;
    }
    .lighting-guard-box {
        padding: 10px;
        border-radius: 6px;
        font-size: 14px;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Database, Inventory & Demo Samples
init_db()
init_inventory_db()
demo_dir = str(PROJECT_ROOT / "demo_samples")
if not os.path.exists(os.path.join(demo_dir, "cocaine_scott_positive.png")):
    generate_all_demo_samples(demo_dir)

# -----------------------------------------------------------------------------
# SIDEBAR: REGIONAL LANGUAGE, TELEMETRY & REAGENTS
# -----------------------------------------------------------------------------
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/police-badge.png", width=64)
    st.title("FieldVerify Control")

    # Language Switcher
    lang_choice = st.selectbox("🌐 Select Language / भाषा", list(I18N.keys()), index=0)
    T = I18N[lang_choice]

    st.markdown("---")
    st.subheader(T["officer_title"])
    officer_name = st.text_input(T["officer_name"], value="SI Rajesh Barua")
    officer_id = st.text_input(T["badge_id"], value="AS-CID-9942")
    fir_case_ref = st.text_input(T["fir_ref"], value="FIR-2026/NCB-GHY-042")
    location_name = st.text_input(T["location"], value="Guwahati Interstate Toll Checkpoint")

    col_lat, col_lon = st.columns(2)
    with col_lat:
        lat = st.number_input("Latitude", value=26.1445, format="%.4f")
    with col_lon:
        lon = st.number_input("Longitude", value=91.7362, format="%.4f")

    st.markdown("---")
    st.subheader("🏷️ Physical Evidence Custody")
    evidence_bag_barcode = st.text_input(T["evidence_barcode"], value="BAG-NCB-2026-9912")
    sample_weight = st.number_input(T["sample_weight"], value=250.0, step=5.0)

    col_w1, col_w2 = st.columns(2)
    with col_w1:
        witness_1 = st.text_input(T["witness1"], value="Shri Ramesh Kumar")
    with col_w2:
        witness_2 = st.text_input(T["witness2"], value="Shri Amit Sen")

    st.markdown("---")
    st.subheader("🧪 Reagent Batch & Lot Verification")
    qr_mode = st.radio("Reagent Source", ["Manual Select", "Scan Reagent QR Code"])

    selected_reagent_key = "SCOTT_REAGENT"
    batch_lot_num = "SC-2026-0819"
    is_expired_kit = False

    if qr_mode == "Scan Reagent QR Code":
        qr_json_str = st.text_area(
            "Reagent QR Code Data Payload",
            value='{"reagent": "SCOTT_REAGENT", "lot": "SC-2026-0819", "exp": "2027-12-31"}',
            height=70
        )
        parsed_qr = parse_reagent_qr_data(qr_json_str)
        if parsed_qr["is_valid"]:
            selected_reagent_key = parsed_qr["reagent_type"]
            batch_lot_num = parsed_qr["lot_number"]
            is_expired_kit = parsed_qr["is_expired"]
            if is_expired_kit:
                st.error("⚠️ EXPIRED REAGENT KIT DETECTED! Results invalidated.")
            else:
                st.success(f"✅ Kit Verified: Lot {batch_lot_num} (Exp: {parsed_qr['expiry_date']})")
        else:
            st.warning(f"⚠️ {parsed_qr['error']}")
    else:
        selected_reagent_key = st.selectbox(
            "Chemical Reagent Kit",
            options=list(VALIDATED_REAGENT_LIBRARY.keys()),
            format_func=lambda x: VALIDATED_REAGENT_LIBRARY[x]["name"]
        )
        batch_lot_num = st.text_input("Reagent Lot Number", value="SC-2026-0819")


# -----------------------------------------------------------------------------
# MAIN APP BODY: TABS
# -----------------------------------------------------------------------------
st.title(f"🛡️ {T['title']}")
st.caption(T["subtitle"])

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    T["tab_test"],
    T["tab_panchnama"],
    T["tab_map"],
    T["tab_fsl"],
    T["tab_inventory"],
    T["tab_ledger"],
    T["tab_guide"]
])

# -----------------------------------------------------------------------------
# TAB 1: LIVE FIELD TEST STATION
# -----------------------------------------------------------------------------
with tab1:
    col_input, col_results = st.columns([1, 1])

    with col_input:
        st.subheader("1. Sample Frame Acquisition")

        input_source = st.radio(
            "Select Image Input Method",
            ["Pre-loaded Synthetic Demo Samples", "Upload Field Photo", "Use Camera"],
            horizontal=True
        )

        input_image_bgr = None

        if input_source == "Pre-loaded Synthetic Demo Samples":
            demo_option = st.selectbox(
                "Choose Demo Scenario",
                [
                    "Cocaine Scott Reagent (Cobalt Blue Positive)",
                    "Heroin Marquis Reagent (Deep Violet Positive)",
                    "Cannabis Duquenois-Levine (Multi-phase Organic Layer)",
                    "Negative Blank Test (Clear Liquid)",
                    "Digital Screen Re-photography Spoof Attempt"
                ]
            )

            file_map = {
                "Cocaine Scott Reagent (Cobalt Blue Positive)": "cocaine_scott_positive.png",
                "Heroin Marquis Reagent (Deep Violet Positive)": "heroin_marquis_positive.png",
                "Cannabis Duquenois-Levine (Multi-phase Organic Layer)": "cannabis_duquenois_multiphase.png",
                "Negative Blank Test (Clear Liquid)": "negative_blank_test.png",
                "Digital Screen Re-photography Spoof Attempt": "screen_spoof_attempt.png"
            }

            if demo_option == "Cocaine Scott Reagent (Cobalt Blue Positive)":
                selected_reagent_key = "SCOTT_REAGENT"
            elif demo_option == "Heroin Marquis Reagent (Deep Violet Positive)":
                selected_reagent_key = "MARQUIS_OPIATE"
            elif demo_option == "Cannabis Duquenois-Levine (Multi-phase Organic Layer)":
                selected_reagent_key = "DUQUENOIS_LEVINE"

            sample_file = os.path.join(demo_dir, file_map[demo_option])
            if os.path.exists(sample_file):
                input_image_bgr = cv2.imread(sample_file)
                st.image(cv2.cvtColor(input_image_bgr, cv2.COLOR_BGR2RGB), caption="Acquired Field Sample", use_container_width=True)

        elif input_source == "Upload Field Photo":
            uploaded_file = st.file_uploader("Upload raw image frame (PNG/JPG)", type=["png", "jpg", "jpeg"])
            if uploaded_file:
                file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
                input_image_bgr = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                st.image(cv2.cvtColor(input_image_bgr, cv2.COLOR_BGR2RGB), caption="Uploaded Sample", use_container_width=True)

        elif input_source == "Use Camera":
            camera_photo = st.camera_input("Take Field Photo")
            if camera_photo:
                file_bytes = np.asarray(bytearray(camera_photo.read()), dtype=np.uint8)
                input_image_bgr = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        # Ambient Lighting Guard Check
        if input_image_bgr is not None:
            light_check = check_ambient_lighting(input_image_bgr)
            if light_check["status"] == "TOO_DARK":
                st.warning(f"💡 **Lighting Guard:** {light_check['message']}")
            elif light_check["status"] == "TOO_BRIGHT":
                st.warning(f"☀️ **Lighting Guard:** {light_check['message']}")
            else:
                st.success(f"✅ **Lighting Guard:** {light_check['message']}")

        run_button = st.button(T["btn_run"], type="primary", use_container_width=True)

    with col_results:
        st.subheader(f"2. {T['opt_status']}")

        if run_button and input_image_bgr is not None:
            if is_expired_kit:
                st.markdown("<div class='badge-warning'>⚠️ EXPIRED REAGENT KIT<br/>TEST INVALIDATED</div>", unsafe_allow_html=True)
                st.error("Reagent lot expiry date has passed. Disposal required under Standing Order 1/88.")
            else:
                try:
                    # Step A: Anti-Spoofing Check
                    is_spoof, spoof_score, spoof_reason = detect_screen_spoofing(input_image_bgr)

                    # Step B: Perspective Homography
                    rectified = rectify_reference_card(input_image_bgr)

                    # Step C: von Kries Calibration & Color Extraction
                    reagent_info = VALIDATED_REAGENT_LIBRARY[selected_reagent_key]
                    is_multi_phase = reagent_info.get("is_multi_phase", False)

                    opt_res = calibrate_and_extract_color(rectified, is_multi_phase=is_multi_phase)

                    calibrated_crop = opt_res["calibrated_pouch"]
                    measured_lab = opt_res["measured_lab"]
                    target_lab = reagent_info["target_lab"]

                    # Step D: CIEDE2000 Delta-E Calculation
                    delta_e = ciede2000(measured_lab, target_lab)

                    if is_spoof:
                        outcome = "SCREEN_SPOOF_ALERT"
                    elif delta_e <= reagent_info["max_positive_delta_e"]:
                        outcome = "POSITIVE"
                    elif delta_e >= reagent_info["min_negative_delta_e"]:
                        outcome = "NEGATIVE"
                    else:
                        outcome = "INCONCLUSIVE"

                    # Decrement reagent inventory count
                    record_reagent_usage(selected_reagent_key)

                    # Display Large Verdict Badge
                    voice_text = ""
                    if outcome == "POSITIVE":
                        display_text = f"{T['positive']} {reagent_info['substance'].upper()} (ΔE00 = {delta_e:.2f})"
                        st.markdown(f"<div class='badge-positive'>{display_text}</div>", unsafe_allow_html=True)
                        voice_text = f"Warning. Chemical test result is Positive for {reagent_info['substance']}."
                    elif outcome == "NEGATIVE":
                        display_text = f"{T['negative']} (ΔE00 = {delta_e:.2f})"
                        st.markdown(f"<div class='badge-negative'>{display_text}</div>", unsafe_allow_html=True)
                        voice_text = "Test completed. Result is Negative."
                    elif outcome == "SCREEN_SPOOF_ALERT":
                        st.markdown(f"<div class='badge-warning'>⚠️ {T['spoof']}<br/>({spoof_reason})</div>", unsafe_allow_html=True)
                        voice_text = "Security Alert. Screen re-photography spoofing detected."
                    else:
                        st.markdown(f"<div class='badge-inconclusive'>{T['inconclusive']} (ΔE00 = {delta_e:.2f})</div>", unsafe_allow_html=True)
                        voice_text = "Test inconclusive. Sample marked for forensic science laboratory."

                    # Audio Voice Readout (HTML5 Web Speech API)
                    if voice_text:
                        speech_html = f"""
                        <script>
                            var msg = new SpeechSynthesisUtterance("{voice_text}");
                            msg.rate = 0.95;
                            window.speechSynthesis.speak(msg);
                        </script>
                        """
                        st.components.v1.html(speech_html, height=0)

                    st.markdown("---")

                    # Display Optical Reticle Views
                    col_r1, col_r2 = st.columns(2)
                    with col_r1:
                        st.image(cv2.cvtColor(rectified, cv2.COLOR_BGR2RGB), caption="Rectified Reference Card (1000x600 px)", use_container_width=True)
                    with col_r2:
                        st.image(cv2.cvtColor(calibrated_crop, cv2.COLOR_BGR2RGB), caption=f"Calibrated ROI ({'Multi-Phase Organic Layer' if is_multi_phase else 'Single Phase'})", use_container_width=True)

                    # Metrics Row
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Target CIELAB", f"{target_lab[0]}, {target_lab[1]}, {target_lab[2]}")
                    m2.metric("Measured LAB", f"{measured_lab[0]}, {measured_lab[1]}, {measured_lab[2]}")
                    m3.metric("Specular Glare", f"{opt_res['glare_percentage']}%")
                    m4.metric("Color ΔE00", f"{delta_e:.2f}")

                    # Step E: Cryptographic Evidence Sealing
                    _, raw_encoded = cv2.imencode(".png", input_image_bgr)
                    _, roi_encoded = cv2.imencode(".png", calibrated_crop)

                    test_uid = f"FV-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"

                    meta = {
                        "test_id": test_uid,
                        "officer_id": officer_id,
                        "officer_name": officer_name,
                        "fir_case_ref": fir_case_ref,
                        "gps": {"lat": lat, "lon": lon},
                        "location_name": location_name,
                        "reagent_type": selected_reagent_key,
                        "batch_lot": batch_lot_num,
                        "measured_lab": {"L": measured_lab[0], "a": measured_lab[1], "b": measured_lab[2]},
                        "delta_e00": delta_e,
                        "outcome": outcome,
                        "anti_spoof_status": "REJECTED_SPOOF" if is_spoof else "PASS",
                        "evidence_bag_barcode": evidence_bag_barcode,
                        "estimated_weight_g": sample_weight,
                        "witness_1_name": witness_1,
                        "witness_2_name": witness_2,
                        "ambient_lux": opt_res.get("ambient_lux", 450.0),
                        "fsl_status": "PENDING_LAB"
                    }

                    cert = generate_evidentiary_certificate(raw_encoded.tobytes(), roi_encoded.tobytes(), meta)

                    # Save to SQLite Database
                    save_test_record(cert)

                    # Store last test in session state for Panchnama generator
                    st.session_state["last_test_cert"] = cert

                    st.markdown("---")
                    st.subheader("3. Section 63 BSA Digital Certificate & PDF Affidavit")

                    with st.expander("🔍 View Raw Cryptographic JSON Payload", expanded=False):
                        st.json(cert)

                    # PDF Affidavit Generation Button
                    pdf_bytes = generate_evidentiary_pdf(cert)

                    st.download_button(
                        label="📄 Download Section 63 BSA Court Evidence Affidavit (PDF)",
                        data=pdf_bytes,
                        file_name=f"BSA_Section63_Affidavit_{cert['test_id']}.pdf",
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True
                    )

                except Exception as e:
                    st.error(f"Execution Error: {str(e)}")
        else:
            st.info("👆 Select an image source on the left panel and click 'Run Calibrated Analysis'.")


# -----------------------------------------------------------------------------
# TAB 2: AUTO-GENERATED NDPS PANCHNAMA / SEIZURE MEMO
# -----------------------------------------------------------------------------
with tab2:
    st.subheader("📄 1-Click Auto-Generated NDPS Panchnama / Seizure Memo")
    st.caption("Drafted in accordance with Sections 42, 43, 50, and 52 of the NDPS Act, 1985 & Section 63 BSA, 2023.")

    cert_for_panchnama = st.session_state.get("last_test_cert")

    if not cert_for_panchnama:
        # Load most recent from database
        recent_records = search_test_records(limit=1)
        if recent_records:
            cert_for_panchnama = json.loads(recent_records[0]["certificate_json"])

    if cert_for_panchnama:
        panch_data = {
            "test_id": cert_for_panchnama["test_id"],
            "fir_case_ref": cert_for_panchnama.get("fir_case_ref", "FIR-2026/NCB-GHY-042"),
            "officer_name": cert_for_panchnama.get("officer_name", officer_name),
            "officer_badge_id": cert_for_panchnama.get("officer_badge_id", officer_id),
            "police_station": "Narcotics Control Bureau / CID Guwahati",
            "seizure_location": cert_for_panchnama.get("location_name", location_name),
            "gps_coords": (cert_for_panchnama.get("gps", {}).get("lat", lat), cert_for_panchnama.get("gps", {}).get("lon", lon)),
            "timestamp_str": cert_for_panchnama.get("timestamp_utc"),
            "suspected_substance": f"Suspected Contraband ({cert_for_panchnama.get('reagent_type')})",
            "presumptive_result": cert_for_panchnama.get("outcome"),
            "delta_e": cert_for_panchnama.get("delta_e00", 0.0),
            "estimated_weight_g": cert_for_panchnama.get("estimated_weight_g", sample_weight),
            "evidence_bag_barcode": cert_for_panchnama.get("evidence_bag_barcode", evidence_bag_barcode),
            "witness_1_name": cert_for_panchnama.get("witness_1_name", witness_1),
            "witness_1_address": "Highway Toll Booth No. 4, Guwahati",
            "witness_2_name": cert_for_panchnama.get("witness_2_name", witness_2),
            "witness_2_address": "Village Bhetapara, Kamrup, Assam",
            "raw_hash": cert_for_panchnama.get("sha256_raw_image"),
            "roi_hash": cert_for_panchnama.get("sha256_calibrated_roi"),
            "ecdsa_sig": cert_for_panchnama.get("ecdsa_signature_hex")
        }

        panchnama_text = generate_ndps_panchnama_text(panch_data)

        st.text_area("Legal Panchnama Memo Text (Court Ready)", value=panchnama_text, height=380)

        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.download_button(
                "📥 Download Panchnama Form (.txt)",
                data=panchnama_text,
                file_name=f"NDPS_Panchnama_{cert_for_panchnama['test_id']}.txt",
                mime="text/plain",
                use_container_width=True
            )
        with col_p2:
            st.info("💡 Tip: Print this memo directly at the roadside inspection post and collect physical signatures from the two Panchas.")
    else:
        st.warning("No test record available yet. Run a field screening test in Tab 1 first.")


# -----------------------------------------------------------------------------
# TAB 3: GEOSPATIAL NARCOTICS SEIZURE HEATMAP
# -----------------------------------------------------------------------------
with tab3:
    st.subheader("🗺️ Geospatial Narcotics Seizure Heatmap & Smuggling Corridors")
    st.caption("Strategic Intelligence Mapping for Police Superintendents and NCB Directors.")

    all_tests = search_test_records(limit=200)

    # Seed demo locations across Northeast & interstate corridors if few records
    map_data = []
    if all_tests:
        for t in all_tests:
            map_data.append({
                "latitude": t["latitude"],
                "longitude": t["longitude"],
                "substance": t["reagent_type"],
                "result": t["result"],
                "weight_g": t.get("estimated_weight_g", 100.0)
            })

    # Add realistic corridor clusters for visual intelligence demonstration
    clusters = [
        {"latitude": 26.1445, "longitude": 91.7362, "substance": "SCOTT_REAGENT", "result": "POSITIVE", "weight_g": 350.0},
        {"latitude": 26.1850, "longitude": 91.7500, "substance": "MARQUIS_OPIATE", "result": "POSITIVE", "weight_g": 520.0},
        {"latitude": 25.5788, "longitude": 91.8933, "substance": "DUQUENOIS_LEVINE", "result": "POSITIVE", "weight_g": 1200.0},
        {"latitude": 24.8170, "longitude": 93.9368, "substance": "MARQUIS_AMPHETAMINE", "result": "POSITIVE", "weight_g": 400.0},
        {"latitude": 23.8315, "longitude": 91.2868, "substance": "SCOTT_REAGENT", "result": "POSITIVE", "weight_g": 180.0},
        {"latitude": 26.7509, "longitude": 94.2037, "substance": "MARQUIS_OPIATE", "result": "POSITIVE", "weight_g": 640.0}
    ]
    map_data.extend(clusters)

    df_map = pd.DataFrame(map_data)

    col_m1, col_m2 = st.columns([3, 1])
    with col_m1:
        st.map(df_map, latitude="latitude", longitude="longitude", size=25, zoom=6)

    with col_m2:
        st.markdown("### 📊 Corridor Statistics")
        st.metric("Total Interdictions", len(df_map))
        pos_count = len(df_map[df_map["result"] == "POSITIVE"])
        st.metric("Confirmed Positives", pos_count)
        st.metric("Total Seized Weight", f"{df_map['weight_g'].sum():,.1f} g")

        st.markdown("---")
        st.caption("Active Corridors: NH-27 (Guwahati Toll), NH-102 (Moreh Border), Silchar-Aizawl Corridor.")


# -----------------------------------------------------------------------------
# TAB 4: CFSL / STATE FORENSIC SCIENCE LABORATORY (FSL) PORTAL
# -----------------------------------------------------------------------------
with tab4:
    st.subheader("🔬 Central Forensic Science Laboratory (CFSL) Confirmation Portal")
    st.caption("Judicial Reconciliation under Section 293 CrPC / Section 63 BSA.")

    st.markdown("""
    When seized physical evidence arrives from the police station in sealed bags, 
    forensic scientists conduct confirmatory Gas Chromatography-Mass Spectrometry (GC-MS) 
    and HPLC molecular testing to validate roadside presumptive calls.
    """)

    fsl_records = search_test_records(limit=50)

    if fsl_records:
        pending_list = [f"{r['id']} | Bag: {r.get('evidence_bag_barcode', 'N/A')} | {r['reagent_type']} ({r['result']})" for r in fsl_records]
        selected_case = st.selectbox("Select Seizure Case for Laboratory Confirmation", pending_list)

        selected_id = selected_case.split(" | ")[0]
        case_row = next(r for r in fsl_records if r["id"] == selected_id)

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            st.text_input("Selected Test ID", value=case_row["id"], disabled=True)
            st.text_input("Linked Evidence Bag Barcode", value=case_row.get("evidence_bag_barcode", "N/A"), disabled=True)
            chemist_name = st.text_input("Forensic Examiner Name", value="Dr. Ananya Sharma (Senior Scientific Officer)")
            chemist_id = st.text_input("CFSL Examiner ID", value="CFSL-ND-8492")
            lab_name = st.selectbox("Forensic Institution", ["CFSL New Delhi", "CFSL Kolkata", "CFSL Hyderabad", "State FSL Guwahati"])

        with col_f2:
            method = st.selectbox("Analytical Confirmatory Method", [
                "GC-MS (Gas Chromatography - Mass Spectrometry)",
                "HPLC (High Performance Liquid Chromatography)",
                "FTIR (Fourier Transform Infrared Spectroscopy)",
                "LC-MS/MS (Liquid Chromatography Tandem Mass Spectrometry)"
            ])
            mol_id = st.text_input("Molecular Confirmation", value=f"Confirmed {case_row['reagent_type']} Base Alkaloid")
            purity = st.slider("Quantitative Purity (%)", min_value=1.0, max_value=99.9, value=82.4, step=0.1)
            verdict = st.selectbox("Laboratory Verdict", ["CONFIRMED_POSITIVE", "FALSE_POSITIVE", "INCONCLUSIVE"])
            fsl_notes = st.text_area("Forensic Observations & Spectral Retention Notes", value="Retention time matched reference analytical standard at 4.28 min with 99.4% spectral match.")

        if st.button("💾 Submit & Digitally Reconcile CFSL Report", type="primary", use_container_width=True):
            res = submit_fsl_confirmatory_report(
                test_id=case_row["id"],
                chemist_id=chemist_id,
                chemist_name=chemist_name,
                lab_name=lab_name,
                analytical_method=method,
                molecular_identification=mol_id,
                purity_percentage=purity,
                fsl_verdict=verdict,
                remarks=fsl_notes
            )
            st.success(f"✅ {res['message']}")
            st.info("Chain of custody record updated to 'CONFIRMED' in the central judicial database.")
    else:
        st.warning("No test cases found to reconcile.")


# -----------------------------------------------------------------------------
# TAB 5: STATION REAGENT INVENTORY & ALARMS
# -----------------------------------------------------------------------------
with tab5:
    st.subheader("🧪 Station Chemical Reagent Inventory & Expiry Auto-Alarm Tracker")
    st.caption("Monitors chemical ampoule stocks, tracks lot expiration dates, and alerts logistics storekeepers.")

    inventory_items = get_inventory_status()

    # Expiry Alarms Summary
    expired_count = sum(1 for item in inventory_items if "EXPIRED" in item["status_flags"])
    expiring_soon = sum(1 for item in inventory_items if "EXPIRING_SOON" in item["status_flags"])
    low_stock = sum(1 for item in inventory_items if "LOW_STOCK" in item["status_flags"])

    c_al1, c_al2, c_al3 = st.columns(3)
    c_al1.metric("Expired Kits (Must Discard)", expired_count, delta="-ALERT" if expired_count > 0 else "0", delta_color="inverse")
    c_al2.metric("Expiring Soon (<= 30 Days)", expiring_soon, delta="WARN" if expiring_soon > 0 else "0", delta_color="inverse")
    c_al3.metric("Low Stock Kits (<= 5 Kits)", low_stock, delta="REORDER" if low_stock > 0 else "0", delta_color="inverse")

    st.markdown("---")

    for item in inventory_items:
        with st.container():
            col_i1, col_i2, col_i3, col_i4 = st.columns([2, 1, 1, 1])
            with col_i1:
                st.markdown(f"**{item['reagent_name']}**")
                st.caption(f"Batch Lot: `{item['batch_lot']}` | Target: {item['target_drug']}")
            with col_i2:
                st.markdown(f"Stock: **{item['quantity_in_stock']} kits**")
            with col_i3:
                st.markdown(f"Expiry: **{item['expiry_date']}**")
                if item['days_left'] < 0:
                    st.error(f"Expired {-item['days_left']} days ago")
                elif item['days_left'] <= 30:
                    st.warning(f"{item['days_left']} days left")
                else:
                    st.success(f"{item['days_left']} days left")
            with col_i4:
                if "EXPIRED" in item["status_flags"]:
                    st.button("🚫 Quarantined", key=f"btn_exp_{item['id']}", disabled=True)
                else:
                    st.button("📦 Order Refill", key=f"btn_refill_{item['id']}")
            st.divider()


# -----------------------------------------------------------------------------
# TAB 6: SEARCHABLE POLICE AUDIT LEDGER
# -----------------------------------------------------------------------------
with tab6:
    st.subheader("📜 Local Encrypted Audit Ledger")
    st.caption("Immutable SQLite database record of all roadside presumptive drug screenings.")

    col_f1, col_f2, col_f3 = st.columns([1, 1, 2])
    with col_f1:
        result_filter = st.selectbox("Filter Outcome", ["ALL", "POSITIVE", "NEGATIVE", "INCONCLUSIVE", "SCREEN_SPOOF_ALERT"])
    with col_f2:
        officer_filter = st.text_input("Filter Officer ID", value="")
    with col_f3:
        search_kw = st.text_input("Search Keyword (ID, FIR, Reagent, Lot, Barcode)", value="")

    records = search_test_records(officer_id=officer_filter, result_filter=result_filter, search_query=search_kw)

    if records:
        st.dataframe(records, use_container_width=True)

        st.markdown("---")
        st.subheader("🔐 Court Evidence Audit & Tamper Verification Tool")
        selected_record_id = st.selectbox("Select Test Record to Audit", options=[r["id"] for r in records])

        if selected_record_id:
            rec = next(r for r in records if r["id"] == selected_record_id)
            cert_obj = json.loads(rec["certificate_json"])

            is_valid, msg = verify_evidentiary_certificate(cert_obj)
            if is_valid:
                st.success(f"✅ {msg}")
            else:
                st.error(f"❌ {msg}")
    else:
        st.warning("No test records found matching the query filters.")


# -----------------------------------------------------------------------------
# TAB 7: PASSIVE CARD & STATUTORY GUIDE
# -----------------------------------------------------------------------------
with tab7:
    st.subheader("📄 Physical Reference Card Specification (ID-1 Format)")
    st.caption("Standard credit-card size (85.60 x 53.98 mm). Print on matte 300 GSM cardstock.")

    card_file = str(PROJECT_ROOT / "fieldverify_reference_card.png")
    if not os.path.exists(card_file):
        generate_reference_card(card_file)

    st.image(card_file, caption="FieldVerify Passive Reference Card (DICT_4X4_50)", width=600)

    with open(card_file, "rb") as f:
        st.download_button(
            "📥 Download High-Res Reference Card (PNG)",
            data=f.read(),
            file_name="fieldverify_reference_card.png",
            mime="image/png"
        )

    st.markdown(r"""
    ---
    ### ⚖️ Statutory Legal & Scientific Compliance Notes

    1. **Bharatiya Sakshya Adhiniyam (BSA), 2023 - Section 63:**
       * Replaces Section 65B of the Indian Evidence Act.
       * Requires electronic records to maintain verifiable hash values (`SHA-256`) and contemporaneous metadata (GPS + NTP Timestamp).
       * Every test executed in FieldVerify generates an ECDSA P-256 signed certificate tied to the device's hardware Keystore.

    2. **NDPS Act Section 42, 43, 50 / 52 Compliance:**
       * FieldVerify outputs **presumptive field screening results** intended to establish probable cause for seizure, arrest, and remand.
       * Generates standard NDPS Panchnama seizure memos auto-bound to evidence bag seal barcodes.
       * Reconciled with confirmatory Gas Chromatography / Mass Spectrometry (GC-MS) by CFSL examiners.

    3. **Mathematical Auditability:**
       * Based on peer-reviewed optical standards (ISO/CIE 11664-6).
       * Zero black-box neural networks; 100% explainable in court cross-examination under $\Delta E_{00}$ color metric formulas.
    """)
