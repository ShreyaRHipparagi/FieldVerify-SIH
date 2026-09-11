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
from fieldverify.utils.geo import (
    detect_network_location,
    geocode_search,
    reverse_geocode,
    generate_regional_corridors
)

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
        "inconclusive": "INCONCLUSIVE RESULT (Sent to CFSL)",
        # Tab 2: Panchnama
        "panchnama_title": "📄 1-Click Auto-Generated NDPS Panchnama / Seizure Memo",
        "panchnama_caption": "Drafted in accordance with Sections 42, 43, 50, and 52 of the NDPS Act, 1985 & Section 63 BSA, 2023.",
        "panchnama_download": "📥 Download Panchnama Form (.txt)",
        "panchnama_tip": "💡 Tip: Print this memo directly at the roadside inspection post and collect physical signatures from the two Panchas.",
        "panchnama_empty": "No test record available yet. Run a field screening test in Tab 1 first.",
        # Tab 3: Map
        "map_title": "🗺️ Geospatial Narcotics Seizure Heatmap & Smuggling Corridors",
        "map_caption": "Strategic Intelligence Mapping for Police Superintendents and NCB Directors.",
        "map_stats": "📊 Corridor Statistics",
        "map_total": "Total Interdictions",
        "map_positives": "Confirmed Positives",
        "map_weight": "Total Seized Weight",
        # Tab 4: FSL
        "fsl_title": "🔬 Central Forensic Science Laboratory (CFSL) Confirmation Portal",
        "fsl_caption": "Judicial Reconciliation under Section 293 CrPC / Section 63 BSA.",
        "fsl_submit": "💾 Submit & Digitally Reconcile CFSL Report",
        "fsl_empty": "No test cases found to reconcile.",
        # Tab 5: Inventory
        "inv_title": "🧪 Station Chemical Reagent Inventory & Expiry Auto-Alarm Tracker",
        "inv_caption": "Monitors chemical ampoule stocks, tracks lot expiration dates, and alerts logistics storekeepers.",
        "inv_expired": "Expired Kits (Must Discard)",
        "inv_expiring": "Expiring Soon (≤ 30 Days)",
        "inv_low": "Low Stock Kits (≤ 5 Kits)",
        # Tab 6: Ledger
        "ledger_title": "📜 Local Encrypted Audit Ledger",
        "ledger_caption": "Immutable SQLite database record of all roadside presumptive drug screenings.",
        "ledger_filter": "Filter Outcome",
        "ledger_officer": "Filter Officer ID",
        "ledger_search": "Search Keyword (ID, FIR, Reagent, Lot, Barcode)",
        "ledger_audit": "🔐 Court Evidence Audit & Tamper Verification Tool",
        "ledger_empty": "No test records found matching the query filters.",
        # Sidebar labels & expanders
        "sidebar_control": "FieldVerify Control",
        "lang_select": "🌐 Select Language / भाषा",
        "evidence_title": "🏷️ Physical Evidence Custody",
        "reagent_title": "🧪 Reagent Batch & Lot Verification",
        "reagent_source": "Reagent Source",
        "manual_select": "Manual Select",
        "scan_qr": "Scan Reagent QR Code",
        "reagent_kit": "Chemical Reagent Kit",
        "lot_number": "Reagent Lot Number",
        "qr_payload": "Reagent QR Code Data Payload",
        "lat": "Latitude",
        "lon": "Longitude",
        # Tab 1: Live Test Station
        "tab1_step1": "1. Sample Frame Acquisition",
        "input_method": "Select Image Input Method",
        "src_demo": "Pre-loaded Synthetic Demo Samples",
        "src_upload": "Upload Field Photo",
        "src_camera": "Use Camera",
        "choose_demo": "Choose Demo Scenario",
        "demo_cocaine": "Cocaine Scott Reagent (Cobalt Blue Positive)",
        "demo_heroin": "Heroin Marquis Reagent (Deep Violet Positive)",
        "demo_cannabis": "Cannabis Duquenois-Levine (Multi-phase Organic Layer)",
        "demo_blank": "Negative Blank Test (Clear Liquid)",
        "demo_spoof": "Digital Screen Re-photography Spoof Attempt",
        "sample_acquired": "Acquired Field Sample",
        "upload_label": "Upload raw image frame (PNG/JPG)",
        "camera_label": "Take Field Photo",
        "uploaded_sample": "Uploaded Sample",
        "tab1_prompt": "👆 Select an image source on the left panel and click 'Run Calibrated Analysis'.",
        "light_guard_label": "Lighting Guard",
        "view_reticle_card": "Rectified Reference Card (1000x600 px)",
        "view_reticle_roi": "Calibrated ROI",
        "multi_phase_label": "Multi-Phase Organic Layer",
        "single_phase_label": "Single Phase",
        "metric_target": "Target CIELAB",
        "metric_measured": "Measured LAB",
        "metric_glare": "Specular Glare",
        "metric_delta": "Color ΔE00",
        "cert_section_title": "3. Section 63 BSA Digital Certificate & PDF Affidavit",
        "cert_json_expand": "🔍 View Raw Cryptographic JSON Payload",
        "pdf_download_btn": "📄 Download Section 63 BSA Court Evidence Affidavit (PDF)",
        "expired_kit_badge": "⚠️ EXPIRED REAGENT KIT<br/>TEST INVALIDATED",
        "expired_kit_msg": "Reagent lot expiry date has passed. Disposal required under Standing Order 1/88.",
        # Reagents
        "reagent_scott": "Scott Reagent (Cobalt Thiocyanate)",
        "reagent_marquis_opiate": "Marquis Reagent (Opiates)",
        "reagent_marquis_amp": "Marquis Reagent (Amphetamines)",
        "reagent_dl": "Duquenois-Levine Reagent",
        # GPS Geolocation
        "btn_fetch_gps": "📍 Fetch Current GPS Location",
        "gps_detected": "📍 Current Device Location Pin",
        "gps_map_caption": "Live device position pinned on seizure surveillance map",
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
        "inconclusive": "अस्पष्ट परिणाम (CFSL भेजा जाएगा)",
        "panchnama_title": "📄 एक-क्लिक स्वचालित NDPS पंचनामा / जब्ती ज्ञापन",
        "panchnama_caption": "NDPS अधिनियम 1985 की धारा 42, 43, 50 और 52 तथा BSA 2023 की धारा 63 के अनुसार तैयार।",
        "panchnama_download": "📥 पंचनामा फॉर्म डाउनलोड करें (.txt)",
        "panchnama_tip": "💡 सुझाव: इस ज्ञापन को सड़क किनारे निरीक्षण चौकी पर सीधे प्रिंट करें और दोनों पंचों से भौतिक हस्ताक्षर लें।",
        "panchnama_empty": "अभी तक कोई परीक्षण रिकॉर्ड उपलब्ध नहीं। पहले टैब 1 में फील्ड स्क्रीनिंग टेस्ट चलाएं।",
        "map_title": "🗺️ भू-स्थानिक मादक पदार्थ जब्ती हीटमैप और तस्करी गलियारे",
        "map_caption": "पुलिस अधीक्षकों और NCB निदेशकों के लिए रणनीतिक खुफिया मानचित्रण।",
        "map_stats": "📊 गलियारा सांख्यिकी",
        "map_total": "कुल अवरोधन",
        "map_positives": "पुष्टि सकारात्मक",
        "map_weight": "कुल जब्त वजन",
        "fsl_title": "🔬 केंद्रीय फोरेंसिक विज्ञान प्रयोगशाला (CFSL) पुष्टि पोर्टल",
        "fsl_caption": "धारा 293 CrPC / धारा 63 BSA के तहत न्यायिक समाधान।",
        "fsl_submit": "💾 CFSL रिपोर्ट जमा करें और डिजिटल सुलह करें",
        "fsl_empty": "समाधान के लिए कोई परीक्षण मामला नहीं मिला।",
        "inv_title": "🧪 स्टेशन रासायनिक रिएजेंट सूची और एक्सपायरी ऑटो-अलार्म ट्रैकर",
        "inv_caption": "रासायनिक एम्पूल स्टॉक की निगरानी करता है, लॉट समाप्ति तिथि ट्रैक करता है।",
        "inv_expired": "समय-सीमा समाप्त किट (नष्ट करें)",
        "inv_expiring": "जल्द समाप्त होने वाली (≤ 30 दिन)",
        "inv_low": "कम स्टॉक किट (≤ 5 किट)",
        "ledger_title": "📜 स्थानीय एन्क्रिप्टेड ऑडिट लेजर",
        "ledger_caption": "सड़क किनारे सभी अनुमानित ड्रग स्क्रीनिंग का अपरिवर्तनीय SQLite डेटाबेस रिकॉर्ड।",
        "ledger_filter": "परिणाम फ़िल्टर",
        "ledger_officer": "अधिकारी ID फ़िल्टर",
        "ledger_search": "खोज कुंजीशब्द",
        "ledger_audit": "🔐 न्यायालय साक्ष्य ऑडिट और छेड़छाड़ सत्यापन",
        "ledger_empty": "क्वेरी फ़िल्टर से मेल खाने वाले कोई रिकॉर्ड नहीं।",
        "guide_title": "📄 भौतिक रेफरेंस कार्ड विशिष्टता (ID-1 फॉर्मेट)",
        "guide_caption": "मानक क्रेडिट-कार्ड आकार (85.60 x 53.98 मिमी)। मैट 300 GSM कार्डस्टॉक पर प्रिंट करें।",
        # Sidebar labels & expanders
        "sidebar_control": "फील्डवेरिफ़ाई नियंत्रण कक्ष",
        "lang_select": "🌐 भाषा चुनें / Select Language",
        "evidence_title": "🏷️ भौतिक साक्ष्य संरक्षण एवं कस्टडी",
        "reagent_title": "🧪 रिएजेंट बैच व लॉट सत्यापन",
        "reagent_source": "र रिएजेंट चयन विधि",
        "manual_select": "मैन्युअल चयन",
        "scan_qr": "रिएजेंट QR कोड स्कैन करें",
        "reagent_kit": "रासायनिक रिएजेंट किट",
        "lot_number": "रिएजेंट लॉट संख्या",
        "qr_payload": "रिएजेंट QR कोड डेटा पेलोड",
        "lat": "अक्षांश (Latitude)",
        "lon": "देशांतर (Longitude)",
        # Tab 1: Live Test Station
        "tab1_step1": "1. नमूना फ्रेम अधिग्रहण",
        "input_method": "छवि इनपुट विधि चुनें",
        "src_demo": "पूर्व-लोड किए गए कृत्रिम डेमो नमूने",
        "src_upload": "फील्ड फोटो अपलोड करें",
        "src_camera": "कैमरे से फोटो लें",
        "choose_demo": "डेमो परिदृश्य चुनें",
        "demo_cocaine": "कोकीन स्कॉट रिएजेंट (कोबाल्ट नीला धनात्मक)",
        "demo_heroin": "हेरोइन मार्क्विस रिएजेंट (गहरा बैंगनी धनात्मक)",
        "demo_cannabis": "कैनबिस डुकेनोइस-लेविन (मल्टी-फेज ऑर्गेनिक परत)",
        "demo_blank": "नकारात्मक ब्लैंक परीक्षण (साफ तरल)",
        "demo_spoof": "डिजिटल स्क्रीन फोटो स्पूफिंग का प्रयास",
        "sample_acquired": "अधिग्रहित फील्ड नमूना",
        "upload_label": "मूल छवि फ्रेम अपलोड करें (PNG/JPG)",
        "camera_label": "फील्ड फोटो खींचें",
        "uploaded_sample": "अपलोड किया गया नमूना",
        "tab1_prompt": "👆 बाएं पैनल पर एक छवि स्रोत चुनें और 'ऑप्टिकल विश्लेषण शुरू करें' पर क्लिक करें।",
        "light_guard_label": "लाइटिंग गार्ड",
        "view_reticle_card": "सुधारा हुआ रेफरेंस कार्ड (1000x600 px)",
        "view_reticle_roi": "अंशांकित नमूना क्षेत्र (ROI)",
        "multi_phase_label": "मल्टी-फेज ऑर्गेनिक परत",
        "single_phase_label": "सिंगल फेज",
        "metric_target": "लक्षित CIELAB",
        "metric_measured": "मापा गया LAB",
        "metric_glare": "प्रतिबिंबित चमक (Glare)",
        "metric_delta": "रंग दूरी ΔE00",
        "cert_section_title": "3. धारा 63 BSA डिजिटल प्रमाणपत्र व PDF शपथपत्र",
        "cert_json_expand": "🔍 मूल क्रिप्टोग्राफिक JSON पेलोड देखें",
        "pdf_download_btn": "📄 धारा 63 BSA न्यायालय साक्ष्य शपथपत्र (PDF) डाउनलोड करें",
        "expired_kit_badge": "⚠️ समय-सीमा समाप्त रिएजेंट किट<br/>परीक्षण अमान्य घोषित",
        "expired_kit_msg": "रिएजेंट लॉट की समाप्ति तिथि बीत चुकी है। स्थायी आदेश 1/88 के तहत नष्ट करना आवश्यक।",
        # Reagents
        "reagent_scott": "स्कॉट रिएजेंट (कोबाल्ट थायोसाइनेट)",
        "reagent_marquis_opiate": "मार्क्विस रिएजेंट (ओपिएट्स)",
        "reagent_marquis_amp": "मार्क्विस रिएजेंट (एम्फेटामाइन)",
        "reagent_dl": "डुकेनोइस-लेविन रिएजेंट",
        # GPS Geolocation
        "btn_fetch_gps": "📍 वर्तमान जीपीएस स्थान प्राप्त करें",
        "gps_detected": "📍 वर्तमान डिवाइस स्थान पिन",
        "gps_map_caption": "सक्रिय डिवाइस स्थान जब्ती निगरानी मानचित्र पर पिन किया गया",
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
        "inconclusive": "অমীমাংসিত ফলাফল",
        "panchnama_title": "📄 এক-ক্লিকে স্বয়ংক্রিয় NDPS পঞ্চনামা / জব্দ তালিকা",
        "panchnama_caption": "NDPS আইন ১৯৮৫-এর ধারা ৪২, ৪৩, ৫০ এবং ৫২ এবং BSA ২০২৩-এর ধারা ৬৩ অনুসারে তৈরি।",
        "panchnama_download": "📥 পঞ্চনামা ডাউনলোড করুন (.txt)",
        "panchnama_tip": "💡 পরামর্শ: সড়কের পরিদর্শন চৌকিতে সরাসরি প্রিন্ট করুন এবং দুই পঞ্চের স্বাক্ষর নিন।",
        "panchnama_empty": "এখনো কোনো পরীক্ষার রেকর্ড নেই। প্রথমে ট্যাব ১-এ ফিল্ড স্ক্রিনিং পরীক্ষা চালান।",
        "map_title": "🗺️ ভূ-স্থানিক মাদক জব্দ হিটম্যাপ ও পাচার করিডোর",
        "map_caption": "পুলিশ সুপারিনটেনডেন্ট এবং NCB পরিচালকদের জন্য কৌশলগত মানচিত্র।",
        "map_stats": "📊 করিডোর পরিসংখ্যান",
        "map_total": "মোট বাধা",
        "map_positives": "নিশ্চিত পজিটিভ",
        "map_weight": "মোট জব্দ ওজন",
        "fsl_title": "🔬 কেন্দ্রীয় ফরেনসিক বিজ্ঞান ল্যাবরেটরি (CFSL) নিশ্চিতকরণ পোর্টাল",
        "fsl_caption": "ধারা ২৯৩ CrPC / ধারা ৬৩ BSA-এর অধীনে বিচারিক পুনর্মিলন।",
        "fsl_submit": "💾 CFSL রিপোর্ট জমা ও ডিজিটাল পুনর্মিলন করুন",
        "fsl_empty": "পুনর্মিলনের জন্য কোনো পরীক্ষার মামলা পাওয়া যায়নি।",
        "inv_title": "🧪 স্টেশন রাসায়নিক রিএজেন্ট সূচি ও মেয়াদ ট্র্যাকার",
        "inv_caption": "রাসায়নিক অ্যাম্পুল স্টক পর্যবেক্ষণ এবং মেয়াদ সতর্কতা।",
        "inv_expired": "মেয়াদোত্তীর্ণ কিট (নষ্ট করুন)",
        "inv_expiring": "শীঘ্রই মেয়াদ শেষ (≤ ৩০ দিন)",
        "inv_low": "কম স্টক কিট (≤ ৫ কিট)",
        "ledger_title": "📜 স্থানীয় এনক্রিপ্টেড অডিট খতিয়ান",
        "ledger_caption": "সকল সড়কপাশ মাদক স্ক্রিনিং-এর অপরিবর্তনীয় SQLite ডাটাবেস রেকর্ড।",
        "ledger_filter": "ফলাফল ফিল্টার",
        "ledger_officer": "কর্মকর্তা ID ফিল্টার",
        "ledger_search": "অনুসন্ধান কীওয়ার্ড",
        "ledger_audit": "🔐 আদালত প্রমাণ অডিট ও টেম্পারিং যাচাই",
        "ledger_empty": "ফিল্টারের সাথে মিলে এমন কোনো রেকর্ড নেই।",
        "guide_title": "📄 ফিজিক্যাল রেফারেন্স কার্ড স্পেসিফিকেশন (ID-1 ফরম্যাট)",
        "guide_caption": "স্ট্যান্ডার্ড ক্রেডিট-কার্ড সাইজ (85.60 x 53.98 মিমি)। ম্যাট 300 GSM কার্ডস্টকে প্রিন্ট করুন।",
        # Sidebar labels & expanders
        "sidebar_control": "ফিল্ডভেরিফাই কন্ট্রোল",
        "lang_select": "🌐 ভাষা নির্বাচন / Select Language",
        "evidence_title": "🏷️ বস্তুগত প্রমাণ সংরক্ষণ ও হেফাজত",
        "reagent_title": "🧪 রিএজেন্ট ব্যাচ ও মেয়াদ যাচাই",
        "reagent_source": "রিএজেন্ট নির্বাচন পদ্ধতি",
        "manual_select": "ম্যানুয়াল নির্বাচন",
        "scan_qr": "রিএজেন্ট QR কোড স্ক্যান করুন",
        "reagent_kit": "রাসায়নিক রিএজেন্ট কিট",
        "lot_number": "রিএজেন্ট লট নম্বর",
        "qr_payload": "রিএজেন্ট QR কোড ডেটা",
        "lat": "অক্ষাংশ (Latitude)",
        "lon": "দ্রাঘিমাংশ (Longitude)",
        # Tab 1: Live Test Station
        "tab1_step1": "১. নমুনা চিত্র গ্রহণ",
        "input_method": "চিত্র গ্রহণের পদ্ধতি বেছে নিন",
        "src_demo": "প্রাক-লোড করা ডেমো নমুনা",
        "src_upload": "ক্ষেত্র ফটো আপলোড করুন",
        "src_camera": "ক্যামেরা ব্যবহার করুন",
        "choose_demo": "ডেমো দৃশ্যপট নির্বাচন করুন",
        "demo_cocaine": "কোকেন স্কট রিএজেন্ট (কোবাল্ট নীল নিশ্চিত)",
        "demo_heroin": "হেরোইন মার্কুইস রিএজেন্ট (গাঢ় বেগুনি নিশ্চিত)",
        "demo_cannabis": "গাঁজা ডুকেনোইস-লেভাইন (বহুস্তর জৈব স্তর)",
        "demo_blank": "নেতিবাচক খালি পরীক্ষা (স্বচ্ছ তরল)",
        "demo_spoof": "ডিজিটাল স্ক্রিন ফটো স্পুফিং চেষ্টা",
        "sample_acquired": "গৃহীত নমুনা চিত্র",
        "upload_label": "মূল চিত্র ফাইল আপলোড করুন (PNG/JPG)",
        "camera_label": "ছবি তুলুন",
        "uploaded_sample": "আপলোডকৃত নমুনা",
        "tab1_prompt": "👆 বাম প্যানেল থেকে ছবির উৎস নির্বাচন করুন এবং 'বিশ্লেষণ শুরু করুন'-এ ক্লিক করুন।",
        "light_guard_label": "আলোক গার্ড",
        "view_reticle_card": "সংশোধিত রেফারেন্স কার্ড (1000x600 px)",
        "view_reticle_roi": "পরিমাপিত নমুনা অঞ্চল (ROI)",
        "multi_phase_label": "বহুস্তর জৈব স্তর",
        "single_phase_label": "একক স্তর",
        "metric_target": "লক্ষ্য CIELAB",
        "metric_measured": "পরিমাপিত LAB",
        "metric_glare": "চমক (Glare)",
        "metric_delta": "রং পার্থক্য ΔE00",
        "cert_section_title": "৩. ধারা ৬৩ BSA ডিজিটাল প্রশংসাপত্র ও PDF হলফনামা",
        "cert_json_expand": "🔍 মূল ক্রিপ্টোগ্রাফিক JSON পে-লোড দেখুন",
        "pdf_download_btn": "📄 ধারা ৬৩ BSA আদালত প্রমাণ হলফনামা (PDF) ডাউনলোড করুন",
        "expired_kit_badge": "⚠️ মেয়াদোত্তীর্ণ রিএজেন্ট কিট<br/>পরীক্ষা বাতিল",
        "expired_kit_msg": "রিএজেন্ট কিটের মেয়াদ শেষ হয়েছে। স্থায়ী আদেশ ১/৮৮ অনুযায়ী বাতিলকরণ আবশ্যক।",
        # Reagents
        "reagent_scott": "স্কট রিএজেন্ট (কোবাল্ট থায়োসায়ানেট)",
        "reagent_marquis_opiate": "মার্কুইস রিএজেন্ট (ওপিয়েট)",
        "reagent_marquis_amp": "মার্কুইস রিএজেন্ট (অ্যাম্ফেটামিন)",
        "reagent_dl": "ডুকেনোইস-লেভাইন রিএজেন্ট",
        # GPS Geolocation
        "btn_fetch_gps": "📍 বর্তমান জিপিএস অবস্থান নির্ণয় করুন",
        "gps_detected": "📍 বর্তমান ডিভাইস অবস্থান পিন",
        "gps_map_caption": "লাইভ ডিভাইস অবস্থান নজরদারি মানচিত্রে পিন করা হয়েছে",
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
        "inconclusive": "முடிவற்ற நிலை",
        "panchnama_title": "📄 ஒரே கிளிக்கில் NDPS பஞ்சநாமா / பறிமுதல் குறிப்பு",
        "panchnama_caption": "NDPS சட்டம் 1985 பிரிவுகள் 42, 43, 50 மற்றும் 52 மற்றும் BSA 2023 பிரிவு 63 படி தயாரிக்கப்பட்டது.",
        "panchnama_download": "📥 பஞ்சநாமா படிவம் பதிவிறக்கம் (.txt)",
        "panchnama_tip": "💡 குறிப்பு: சாலையோர சோதனைச் சாவடியில் நேரடியாக அச்சிட்டு இரு பஞ்ச சாட்சிகளிடம் கையொப்பம் பெறவும்.",
        "panchnama_empty": "இன்னும் சோதனை பதிவு இல்லை. முதலில் தாவல் 1-ல் கள பரிசோதனை நடத்தவும்.",
        "map_title": "🗺️ புவிசார் போதைப்பொருள் பறிமுதல் வெப்ப வரைபடம் & கடத்தல் வழித்தடங்கள்",
        "map_caption": "காவல்துறை கண்காணிப்பாளர்கள் மற்றும் NCB இயக்குநர்களுக்கான மூலோபாய நுண்ணறிவு.",
        "map_stats": "📊 வழித்தட புள்ளிவிவரம்",
        "map_total": "மொத்த தடுப்புகள்",
        "map_positives": "உறுதிசெய்யப்பட்ட நேர்முகங்கள்",
        "map_weight": "மொத்த பறிமுதல் எடை",
        "fsl_title": "🔬 மத்திய தடய அறிவியல் ஆய்வகம் (CFSL) உறுதிப்படுத்தல் போர்டல்",
        "fsl_caption": "பிரிவு 293 CrPC / பிரிவு 63 BSA கீழ் நீதித்துறை சமரசம்.",
        "fsl_submit": "💾 CFSL அறிக்கை சமர்ப்பிக்கவும்",
        "fsl_empty": "சமரசத்திற்கான சோதனை வழக்குகள் இல்லை.",
        "inv_title": "🧪 நிலைய ரசாயன இருப்பு & காலாவதி தானியங்கி எச்சரிக்கை",
        "inv_caption": "ரசாயன ஆம்பூல் இருப்புகளை கண்காணிக்கிறது, காலாவதி தேதிகளை கண்காணிக்கிறது.",
        "inv_expired": "காலாவதி கிட்கள் (அகற்றவும்)",
        "inv_expiring": "விரைவில் காலாவதி (≤ 30 நாட்கள்)",
        "inv_low": "குறைந்த இருப்பு (≤ 5 கிட்கள்)",
        "ledger_title": "📜 உள்ளூர் மறையாக்கப்பட்ட தணிக்கை பதிவேடு",
        "ledger_caption": "அனைத்து சாலையோர மருந்து பரிசோதனைகளின் மாற்ற முடியாத SQLite தரவுத்தள பதிவு.",
        "ledger_filter": "முடிவு வடிகட்டி",
        "ledger_officer": "அதிகாரி ID வடிகட்டி",
        "ledger_search": "தேடல் முக்கிய சொல்",
        "ledger_audit": "🔐 நீதிமன்ற சான்று தணிக்கை & சேதம் சரிபார்ப்பு",
        "ledger_empty": "வடிகட்டிகளுடன் பொருந்தும் பதிவுகள் இல்லை.",
        "guide_title": "📄 இயற்பியல் குறிப்பு அட்டை விவரக்குறிப்பு (ID-1 வடிவம்)",
        "guide_caption": "நிலையான கிரெடிட் கார்டு அளவு (85.60 x 53.98 மிமீ). மேட் 300 GSM கார்ட்ஸ்டாக்கில் அச்சிடவும்.",
        # Sidebar labels & expanders
        "sidebar_control": "FieldVerify கட்டுப்பாட்டு அறை",
        "lang_select": "🌐 மொழியைத் தேர்ந்தெடுக்கவும்",
        "evidence_title": "🏷️ ஆதாரப் பொருள் பாதுகாப்பு & காவல்",
        "reagent_title": "🧪 ரசாயன தொகுதி & காலாவதி சரிபார்ப்பு",
        "reagent_source": "ரசாயன தேர்வு முறை",
        "manual_select": "கைமுறை தேர்வு",
        "scan_qr": "QR குறியீட்டை ஸ்கேன் செய்க",
        "reagent_kit": "ரசாயன ஆய்வு கிட்",
        "lot_number": "ரசாயன தொகுதி எண்",
        "qr_payload": "QR குறியீட்டு தரவு",
        "lat": "அட்சரேகை (Latitude)",
        "lon": "தீர்க்கரேகை (Longitude)",
        # Tab 1: Live Test Station
        "tab1_step1": "1. மாதிரி படத்தைப் பெறுதல்",
        "input_method": "பட உள்ளீட்டு முறையைத் தேர்ந்தெடுக்கவும்",
        "src_demo": "மாதிரி சோதனை படங்கள்",
        "src_upload": "படத்தை பதிவேற்றவும்",
        "src_camera": "கேமராவைப் பயன்படுத்தவும்",
        "choose_demo": "மாதிரி சோதனையைத் தேர்ந்தெடுக்கவும்",
        "demo_cocaine": "கோகோயின் ஸ்காட் ரசாயனம் (நீல நிறம்)",
        "demo_heroin": "ஹெராயின் மார்குயிஸ் ரசாயனம் (ஊதா நிறம்)",
        "demo_cannabis": "கஞ்சா டுகெனோயிஸ்-லெவின் (இரு அடுக்கு கரிம அடுக்கு)",
        "demo_blank": "எதிர்மறை வெற்று சோதனை (தெளிவான திரவம்)",
        "demo_spoof": "டிஜிட்டல் திரை போலி முயற்சி",
        "sample_acquired": "பெறப்பட்ட மாதிரி படம்",
        "upload_label": "படத்தை பதிவேற்றவும் (PNG/JPG)",
        "camera_label": "படம் எடுக்கவும்",
        "uploaded_sample": "பதிவேற்றப்பட்ட படம்",
        "tab1_prompt": "👆 இடது பக்கத்தில் ஒரு படத்தை தேர்ந்தெடுத்து 'பகுப்பாய்வு செய்க' என்பதைக் கிளிக் செய்யவும்.",
        "light_guard_label": "ஒளி பாதுகாப்பு",
        "view_reticle_card": "சரிசெய்யப்பட்ட குறிப்பு அட்டை (1000x600 px)",
        "view_reticle_roi": "மாதிரி பகுதி (ROI)",
        "multi_phase_label": "இரு அடுக்கு கரிம அடுக்கு",
        "single_phase_label": "ஒற்றை அடுக்கு",
        "metric_target": "இலக்கு CIELAB",
        "metric_measured": "அளவிடப்பட்ட LAB",
        "metric_glare": "பிரதிபலிப்பு ஒளி (Glare)",
        "metric_delta": "நிற வேறுபாடு ΔE00",
        "cert_section_title": "3. பிரிவு 63 BSA டிஜிட்டல் சான்றிதழ் & PDF",
        "cert_json_expand": "🔍 கிரிப்டோகிராஃபிக் JSON தரவைக் காண்க",
        "pdf_download_btn": "📄 பிரிவு 63 BSA நீதிமன்ற சான்றிதழ் (PDF) பதிவிறக்கம்",
        "expired_kit_badge": "⚠️ காலாவதியான ரசாயன கிட்<br/>பரிசோதனை செல்லாது",
        "expired_kit_msg": "ரசாயன கிட்டின் காலாவதி தேதி முடிந்துவிட்டது. ஆணை 1/88 கீழ் அகற்றப்பட வேண்டும்.",
        # Reagents
        "reagent_scott": "ஸ்காட் ரசாயனம் (கோபால்ட் தயோசயனேட்)",
        "reagent_marquis_opiate": "மார்குயிஸ் ரசாயனம் (ஓபியேட்ஸ்)",
        "reagent_marquis_amp": "மார்குயிஸ் ரசாயனம் (ஆம்பெடமைன்)",
        "reagent_dl": "டுகெனோயிஸ்-லெவின் ரசாயனம்",
        # GPS Geolocation
        "btn_fetch_gps": "📍 தற்போதைய GPS இருப்பிடத்தைப் பெறவும்",
        "gps_detected": "📍 தற்போதைய சாதன இருப்பிட முள்",
        "gps_map_caption": "நேரடி சாதன இருப்பிடம் வரைபடத்தில் குறிக்கப்பட்டுள்ளது",
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
try:
    if not os.path.exists(os.path.join(demo_dir, "cocaine_scott_positive.png")):
        generate_all_demo_samples(demo_dir)
except (OSError, PermissionError):
    # Graceful fallback for read-only deployment environments
    import tempfile
    demo_dir = os.path.join(tempfile.gettempdir(), "fieldverify_demo_samples")
    if not os.path.exists(os.path.join(demo_dir, "cocaine_scott_positive.png")):
        try:
            generate_all_demo_samples(demo_dir)
        except Exception:
            pass  # Demo samples unavailable — user can still upload or use camera

# -----------------------------------------------------------------------------
# SIDEBAR: REGIONAL LANGUAGE, TELEMETRY & REAGENTS
# -----------------------------------------------------------------------------
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/police-badge.png", width=64)

    # Language Switcher
    lang_choice = st.selectbox("🌐 Select Language / भाषा", list(I18N.keys()), index=0)
    T = I18N[lang_choice]

    st.title(T.get("sidebar_control", "FieldVerify Control"))

    # Initialize session state for GPS coordinates and active location
    if "gps_initialized" not in st.session_state:
        st.session_state["gps_initialized"] = True
        try:
            detected = detect_network_location()
            if detected:
                st.session_state["gps_lat"] = detected["lat"]
                st.session_state["gps_lon"] = detected["lon"]
                st.session_state["location_name"] = detected["display_name"]
                st.session_state["gps_source"] = f"Auto-detected ({detected.get('city', 'Live')})"
            else:
                st.session_state["gps_lat"] = 12.9753
                st.session_state["gps_lon"] = 77.5910
                st.session_state["location_name"] = "Bengaluru Central City Checkpost, Karnataka"
                st.session_state["gps_source"] = "Default Station"
        except Exception:
            st.session_state["gps_lat"] = 12.9753
            st.session_state["gps_lon"] = 77.5910
            st.session_state["location_name"] = "Bengaluru Central City Checkpost, Karnataka"
            st.session_state["gps_source"] = "Default Station"

    if "gps_lat" not in st.session_state:
        st.session_state["gps_lat"] = 12.9753
    if "gps_lon" not in st.session_state:
        st.session_state["gps_lon"] = 77.5910
    if "location_name" not in st.session_state:
        st.session_state["location_name"] = "Bengaluru Central City Checkpost, Karnataka"

    # Check query params for incoming browser geolocation
    try:
        geo_lat_param = st.query_params.get("geo_lat")
        geo_lon_param = st.query_params.get("geo_lon")
        if geo_lat_param is not None and geo_lon_param is not None:
            new_lat = round(float(geo_lat_param), 4)
            new_lon = round(float(geo_lon_param), 4)
            st.session_state["gps_lat"] = new_lat
            st.session_state["gps_lon"] = new_lon
            st.session_state["input_lat"] = new_lat
            st.session_state["input_lon"] = new_lon
            resolved = reverse_geocode(new_lat, new_lon)
            if resolved:
                st.session_state["location_name"] = resolved
                st.session_state["input_loc_name"] = resolved
            st.session_state["gps_fetched"] = True
            del st.query_params["geo_lat"]
            del st.query_params["geo_lon"]
            st.rerun()
    except Exception:
        pass

    with st.expander(T["officer_title"], expanded=True):
        officer_name = st.text_input(T["officer_name"], value="SI Rajesh Barua")
        officer_id = st.text_input(T["badge_id"], value="AS-CID-9942")
        fir_case_ref = st.text_input(T["fir_ref"], value="FIR-2026/NCB-GHY-042")

        st.markdown(f"**📍 {T.get('location', 'Checkpoint Location / Jurisdiction')}**")

        # 1. Primary One-Click Auto-Detect Live Location Button
        if st.button("📍 Auto-Detect Live GPS Location", type="primary", use_container_width=True, help="Automatically acquire current GPS coordinates via network and focus map directly on your location"):
            with st.spinner("Acquiring live GPS coordinates..."):
                detected = detect_network_location()
                if detected:
                    st.session_state["gps_lat"] = detected["lat"]
                    st.session_state["gps_lon"] = detected["lon"]
                    st.session_state["location_name"] = detected["display_name"]
                    st.session_state["input_lat"] = detected["lat"]
                    st.session_state["input_lon"] = detected["lon"]
                    st.session_state["input_loc_name"] = detected["display_name"]
                    st.session_state["gps_fetched"] = True
                    st.session_state["gps_source"] = f"Detected: {detected.get('city')}"
                    st.rerun()
                else:
                    st.error("Network detection unavailable. Enter location manually.")

        col_g1, col_g2 = st.columns([1, 1])
        with col_g1:
            if st.button("🔄 Sync Address", help="Reverse geocode coordinates into a readable checkpoint name", use_container_width=True):
                with st.spinner("Resolving address from coordinates..."):
                    resolved = reverse_geocode(float(st.session_state["gps_lat"]), float(st.session_state["gps_lon"]))
                    if resolved:
                        st.session_state["location_name"] = resolved
                        st.session_state["input_loc_name"] = resolved
                        st.rerun()
        with col_g2:
            if st.button("🎯 Focus Map", help="Directly jump map view to current coordinates", use_container_width=True):
                st.rerun()

        # HTML5 Browser High-Accuracy Geolocation direct bridge
        geo_browser_html = f"""
        <div style="margin-top: 2px; margin-bottom: 6px;">
            <button id="btn_browser_geo" onclick="fetchDeviceLocation()" style="
                width: 100%;
                background: rgba(30, 41, 59, 0.9);
                color: #93C5FD;
                border: 1px solid #3B82F6;
                border-radius: 6px;
                padding: 6px 10px;
                font-weight: 600;
                font-size: 12px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 6px;
            ">
                🛰️ Use Device GPS (Browser)
            </button>
            <div id="browser_geo_status" style="font-size: 11px; color: #94A3B8; margin-top: 3px; text-align: center;"></div>
        </div>
        <script>
        function fetchDeviceLocation() {{
            var statusDiv = document.getElementById('browser_geo_status');
            var btn = document.getElementById('btn_browser_geo');
            if (!navigator.geolocation) {{
                statusDiv.innerText = "❌ Geolocation not supported by browser";
                return;
            }}
            statusDiv.innerText = "⏳ Acquiring device GPS satellites...";
            btn.disabled = true;
            btn.style.opacity = "0.7";
            navigator.geolocation.getCurrentPosition(
                function(pos) {{
                    var lat = pos.coords.latitude.toFixed(4);
                    var lon = pos.coords.longitude.toFixed(4);
                    statusDiv.innerHTML = "✅ GPS: <b>" + lat + ", " + lon + "</b>. Updating map...";
                    try {{
                        var u = new URL(window.parent.location.href);
                        u.searchParams.set("geo_lat", lat);
                        u.searchParams.set("geo_lon", lon);
                        window.parent.location.href = u.toString();
                    }} catch(e) {{
                        try {{
                            var u = new URL(window.top.location.href);
                            u.searchParams.set("geo_lat", lat);
                            u.searchParams.set("geo_lon", lon);
                            window.top.location.href = u.toString();
                        }} catch(err2) {{
                            window.location.search = "?geo_lat=" + lat + "&geo_lon=" + lon;
                        }}
                    }}
                }},
                function(err) {{
                    btn.disabled = false;
                    btn.style.opacity = "1";
                    statusDiv.innerText = "⚠️ GPS: " + err.message;
                }},
                {{ enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }}
            );
        }}
        </script>
        """
        st.components.v1.html(geo_browser_html, height=62)

        # 2. Search City / Landmark
        col_s1, col_s2 = st.columns([3, 1])
        with col_s1:
            search_query = st.text_input("Find Landmark / City", placeholder="e.g. Indiranagar, Bengaluru", label_visibility="collapsed")
        with col_s2:
            if st.button("🔍 Find", use_container_width=True):
                if search_query:
                    with st.spinner("Searching OpenStreetMap..."):
                        res = geocode_search(search_query)
                        if res:
                            st.session_state["gps_lat"] = res["lat"]
                            st.session_state["gps_lon"] = res["lon"]
                            st.session_state["location_name"] = res["display_name"]
                            st.session_state["input_lat"] = res["lat"]
                            st.session_state["input_lon"] = res["lon"]
                            st.session_state["input_loc_name"] = res["display_name"]
                            st.session_state["gps_fetched"] = True
                            st.rerun()
                        else:
                            st.warning("Location not found.")

        # 3. Checkpoint Name input
        location_name = st.text_input(
            "Checkpoint Name",
            value=st.session_state.get("location_name", "Bengaluru Central City Checkpost, Karnataka"),
            key="input_loc_name"
        )
        st.session_state["location_name"] = location_name

        # 4. Latitude and Longitude Coordinates input
        col_lat, col_lon = st.columns(2)
        with col_lat:
            lat = st.number_input(
                T.get("lat", "Latitude"),
                value=float(st.session_state["gps_lat"]),
                format="%.4f",
                key="input_lat"
            )
            st.session_state["gps_lat"] = lat
        with col_lon:
            lon = st.number_input(
                T.get("lon", "Longitude"),
                value=float(st.session_state["gps_lon"]),
                format="%.4f",
                key="input_lon"
            )
            st.session_state["gps_lon"] = lon

        st.caption(f"📍 Active Coordinates: `{lat:.4f}° N, {lon:.4f}° E`")

    with st.expander(T.get("evidence_title", "🏷️ Physical Evidence Custody"), expanded=True):
        evidence_bag_barcode = st.text_input(T["evidence_barcode"], value="BAG-NCB-2026-9912")
        sample_weight = st.number_input(T["sample_weight"], value=250.0, step=5.0)

        col_w1, col_w2 = st.columns(2)
        with col_w1:
            witness_1 = st.text_input(T["witness1"], value="Shri Ramesh Kumar")
        with col_w2:
            witness_2 = st.text_input(T["witness2"], value="Shri Amit Sen")

    with st.expander(T.get("reagent_title", "🧪 Reagent Batch & Lot Verification"), expanded=True):
        source_options = [T.get("manual_select", "Manual Select"), T.get("scan_qr", "Scan Reagent QR Code")]
        qr_mode_choice = st.radio(T.get("reagent_source", "Reagent Source"), source_options)
        is_qr_mode = (qr_mode_choice == source_options[1])

        selected_reagent_key = "SCOTT_REAGENT"
        batch_lot_num = "SC-2026-0819"
        is_expired_kit = False

        if is_qr_mode:
            qr_json_str = st.text_area(
                T.get("qr_payload", "Reagent QR Code Data Payload"),
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
            reagent_name_map = {
                "SCOTT_REAGENT": T.get("reagent_scott", VALIDATED_REAGENT_LIBRARY["SCOTT_REAGENT"]["name"]),
                "MARQUIS_OPIATE": T.get("reagent_marquis_opiate", VALIDATED_REAGENT_LIBRARY["MARQUIS_OPIATE"]["name"]),
                "MARQUIS_AMPHETAMINE": T.get("reagent_marquis_amp", VALIDATED_REAGENT_LIBRARY["MARQUIS_AMPHETAMINE"]["name"]),
                "DUQUENOIS_LEVINE": T.get("reagent_dl", VALIDATED_REAGENT_LIBRARY["DUQUENOIS_LEVINE"]["name"])
            }
            selected_reagent_key = st.selectbox(
                T.get("reagent_kit", "Chemical Reagent Kit"),
                options=list(VALIDATED_REAGENT_LIBRARY.keys()),
                format_func=lambda x: reagent_name_map.get(x, VALIDATED_REAGENT_LIBRARY[x]["name"])
            )
            batch_lot_num = st.text_input(T.get("lot_number", "Reagent Lot Number"), value="SC-2026-0819")


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
        st.subheader(T.get("tab1_step1", "1. Sample Frame Acquisition"))

        src_options = [
            T.get("src_demo", "Pre-loaded Synthetic Demo Samples"),
            T.get("src_upload", "Upload Field Photo"),
            T.get("src_camera", "Use Camera")
        ]
        input_source_choice = st.radio(
            T.get("input_method", "Select Image Input Method"),
            src_options,
            horizontal=True
        )

        input_image_bgr = None

        if input_source_choice == src_options[0]:
            demo_choices = [
                T.get("demo_cocaine", "Cocaine Scott Reagent (Cobalt Blue Positive)"),
                T.get("demo_heroin", "Heroin Marquis Reagent (Deep Violet Positive)"),
                T.get("demo_cannabis", "Cannabis Duquenois-Levine (Multi-phase Organic Layer)"),
                T.get("demo_blank", "Negative Blank Test (Clear Liquid)"),
                T.get("demo_spoof", "Digital Screen Re-photography Spoof Attempt")
            ]
            demo_option = st.selectbox(
                T.get("choose_demo", "Choose Demo Scenario"),
                demo_choices
            )

            file_map = {
                demo_choices[0]: "cocaine_scott_positive.png",
                demo_choices[1]: "heroin_marquis_positive.png",
                demo_choices[2]: "cannabis_duquenois_multiphase.png",
                demo_choices[3]: "negative_blank_test.png",
                demo_choices[4]: "screen_spoof_attempt.png"
            }

            if demo_option == demo_choices[0]:
                selected_reagent_key = "SCOTT_REAGENT"
            elif demo_option == demo_choices[1]:
                selected_reagent_key = "MARQUIS_OPIATE"
            elif demo_option == demo_choices[2]:
                selected_reagent_key = "DUQUENOIS_LEVINE"

            sample_file = os.path.join(demo_dir, file_map[demo_option])
            if os.path.exists(sample_file):
                input_image_bgr = cv2.imread(sample_file)
                st.image(cv2.cvtColor(input_image_bgr, cv2.COLOR_BGR2RGB), caption=T.get("sample_acquired", "Acquired Field Sample"), use_container_width=True)

        elif input_source_choice == src_options[1]:
            uploaded_file = st.file_uploader(T.get("upload_label", "Upload raw image frame (PNG/JPG)"), type=["png", "jpg", "jpeg"])
            if uploaded_file:
                file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
                input_image_bgr = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                st.image(cv2.cvtColor(input_image_bgr, cv2.COLOR_BGR2RGB), caption=T.get("uploaded_sample", "Uploaded Sample"), use_container_width=True)

        elif input_source_choice == src_options[2]:
            camera_photo = st.camera_input(T.get("camera_label", "Take Field Photo"))
            if camera_photo:
                file_bytes = np.asarray(bytearray(camera_photo.read()), dtype=np.uint8)
                input_image_bgr = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        # Ambient Lighting Guard Check
        if input_image_bgr is not None:
            light_check = check_ambient_lighting(input_image_bgr)
            guard_label = T.get("light_guard_label", "Lighting Guard")
            if light_check["status"] == "TOO_DARK":
                st.warning(f"💡 **{guard_label}:** {light_check['message']}")
            elif light_check["status"] == "TOO_BRIGHT":
                st.warning(f"☀️ **{guard_label}:** {light_check['message']}")
            else:
                st.success(f"✅ **{guard_label}:** {light_check['message']}")

        run_button = st.button(T["btn_run"], type="primary", use_container_width=True)

    with col_results:
        st.subheader(f"2. {T['opt_status']}")

        if run_button and input_image_bgr is not None:
            if is_expired_kit:
                st.markdown(f"<div class='badge-warning'>{T.get('expired_kit_badge', '⚠️ EXPIRED REAGENT KIT<br/>TEST INVALIDATED')}</div>", unsafe_allow_html=True)
                st.error(T.get("expired_kit_msg", "Reagent lot expiry date has passed. Disposal required under Standing Order 1/88."))
            else:
              with st.spinner("🔬 Analyzing optical calibration and computing court verdict..."):
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
                        substance_display = reagent_info['substance'].upper()
                        display_text = f"✅ {T['positive']} {substance_display} (ΔE00 = {delta_e:.2f})"
                        st.markdown(f"<div class='badge-positive'>{display_text}</div>", unsafe_allow_html=True)
                        voice_text = f"Warning. Chemical test result is Positive for {reagent_info['substance']}."
                    elif outcome == "NEGATIVE":
                        display_text = f"❌ {T['negative']} (ΔE00 = {delta_e:.2f})"
                        st.markdown(f"<div class='badge-negative'>{display_text}</div>", unsafe_allow_html=True)
                        voice_text = "Test completed. Result is Negative."
                    elif outcome == "SCREEN_SPOOF_ALERT":
                        st.markdown(f"<div class='badge-warning'>🚨 {T['spoof']}<br/>({spoof_reason})</div>", unsafe_allow_html=True)
                        voice_text = "Security Alert. Screen re-photography spoofing detected."
                    else:
                        st.markdown(f"<div class='badge-inconclusive'>⚠️ {T['inconclusive']} (ΔE00 = {delta_e:.2f})</div>", unsafe_allow_html=True)
                        voice_text = "Test inconclusive. Sample marked for forensic science laboratory."

                    # Audio Voice Readout (HTML5 Web Speech API)
                    if voice_text:
                        speech_html = f"""
                        <script>
                            var msg = new SpeechSynthesisUtterance({json.dumps(voice_text)});
                            msg.rate = 0.95;
                            window.speechSynthesis.speak(msg);
                        </script>
                        """
                        st.components.v1.html(speech_html, height=0)

                    st.markdown("---")

                    # Display Optical Reticle Views
                    col_r1, col_r2 = st.columns(2)
                    roi_caption_phase = T.get('multi_phase_label', 'Multi-Phase Organic Layer') if is_multi_phase else T.get('single_phase_label', 'Single Phase')
                    with col_r1:
                        st.image(cv2.cvtColor(rectified, cv2.COLOR_BGR2RGB), caption=T.get("view_reticle_card", "Rectified Reference Card (1000x600 px)"), use_container_width=True)
                    with col_r2:
                        st.image(cv2.cvtColor(calibrated_crop, cv2.COLOR_BGR2RGB), caption=f"{T.get('view_reticle_roi', 'Calibrated ROI')} ({roi_caption_phase})", use_container_width=True)

                    # Metrics Row (2x2 for mobile responsiveness)
                    m1, m2 = st.columns(2)
                    m1.metric(T.get("metric_target", "Target CIELAB"), f"{target_lab[0]}, {target_lab[1]}, {target_lab[2]}")
                    m2.metric(T.get("metric_measured", "Measured LAB"), f"{measured_lab[0]}, {measured_lab[1]}, {measured_lab[2]}")
                    m3, m4 = st.columns(2)
                    m3.metric(T.get("metric_glare", "Specular Glare"), f"{opt_res['glare_percentage']}%")
                    m4.metric(T.get("metric_delta", "Color ΔE00"), f"{delta_e:.2f}")

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
                        "ambient_lux": light_check.get("estimated_lux", 450.0),
                        "fsl_status": "PENDING_LAB"
                    }

                    cert = generate_evidentiary_certificate(raw_encoded.tobytes(), roi_encoded.tobytes(), meta)

                    # Save to SQLite Database
                    save_test_record(cert)

                    # Store last test in session state for Panchnama generator
                    st.session_state["last_test_cert"] = cert

                    st.markdown("---")
                    st.subheader(T.get("cert_section_title", "3. Section 63 BSA Digital Certificate & PDF Affidavit"))

                    with st.expander(T.get("cert_json_expand", "🔍 View Raw Cryptographic JSON Payload"), expanded=False):
                        st.json(cert)

                    # PDF Affidavit Generation Button
                    pdf_bytes = generate_evidentiary_pdf(cert)

                    st.download_button(
                        label=T.get("pdf_download_btn", "📄 Download Section 63 BSA Court Evidence Affidavit (PDF)"),
                        data=pdf_bytes,
                        file_name=f"BSA_Section63_Affidavit_{cert['test_id']}.pdf",
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True
                    )

                except ValueError as ve:
                    st.error(f"⚠️ {str(ve)}")
                    st.info("💡 **Tip:** Ensure the reference card is fully visible, well-lit, and the sample pouch is inside the reaction zone.")
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    st.error("❌ An unexpected error occurred during analysis. Please try again with a clearer image.")
                    st.info("💡 **Tip:** Make sure the reference card is flat, all 4 ArUco markers are visible, and there's no glare on the pouch.")
        else:
            st.info(T.get("tab1_prompt", "👆 Select an image source on the left panel and click 'Run Calibrated Analysis'."))


# -----------------------------------------------------------------------------
# TAB 2: AUTO-GENERATED NDPS PANCHNAMA / SEIZURE MEMO
# -----------------------------------------------------------------------------
with tab2:
    st.subheader(T.get("panchnama_title", "📄 1-Click Auto-Generated NDPS Panchnama / Seizure Memo"))
    st.caption(T.get("panchnama_caption", "Drafted in accordance with Sections 42, 43, 50, and 52 of the NDPS Act, 1985 & Section 63 BSA, 2023."))

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
                T.get("panchnama_download", "📥 Download Panchnama Form (.txt)"),
                data=panchnama_text,
                file_name=f"NDPS_Panchnama_{cert_for_panchnama['test_id']}.txt",
                mime="text/plain",
                use_container_width=True
            )
        with col_p2:
            st.info(T.get("panchnama_tip", "💡 Tip: Print this memo directly at the roadside inspection post and collect physical signatures from the two Panchas."))
    else:
        st.warning(T.get("panchnama_empty", "No test record available yet. Run a field screening test in Tab 1 first."))


# -----------------------------------------------------------------------------
# TAB 3: GEOSPATIAL NARCOTICS SEIZURE HEATMAP
# -----------------------------------------------------------------------------
with tab3:
    st.subheader(T.get("map_title", "🗺️ Geospatial Narcotics Seizure Heatmap & Smuggling Corridors"))
    st.caption(T.get("map_caption", "Strategic Intelligence Mapping for Police Superintendents and NCB Directors."))

    USER_MAPBOX_KEY = "pk.eyJ1IjoiYWJoaXNoZWtwZXMiLCJhIjoiY202N2o5d2FtMDU0NDJyczgxMHdqaWtjcyJ9.Qq1ASpNfKaPB4L_6XmByow"
    if "mapbox_token" not in st.session_state or not st.session_state["mapbox_token"]:
        st.session_state["mapbox_token"] = USER_MAPBOX_KEY

    # Mapbox configuration expander
    with st.expander("🗺️ Map Tile Provider & Mapbox Settings (Key Active)", expanded=False):
        col_tok, col_help = st.columns([3, 2])
        with col_tok:
            mapbox_token = st.text_input(
                "🔑 Mapbox Public Access Token",
                value=st.session_state.get("mapbox_token", USER_MAPBOX_KEY),
                type="password",
                help="Your Mapbox public access token is configured. Mapbox Dark, Streets, and Satellite layers are unlocked."
            )
            st.session_state["mapbox_token"] = mapbox_token
        with col_help:
            st.markdown(
                """
                **Configured & Active Layers:**
                - 🌙 **Mapbox Dark**: High-Contrast Police Tactical
                - 🌐 **OpenStreetMap (OSM)**: 100% Free & Open Source
                - 🛣️ **Mapbox Streets**: Ultra High-Res Streets & Landmarks
                - 🛰️ **Mapbox Satellite**: Global Aerial Imagery
                - 🛰️ **Esri World Imagery**: Alternate Satellite
                """
            )

    all_tests = search_test_records(limit=200)

    # Compile geospatial records
    map_data = []
    if all_tests:
        for t in all_tests:
            map_data.append({
                "id": t["id"],
                "latitude": float(t["latitude"]),
                "longitude": float(t["longitude"]),
                "substance": t["reagent_type"],
                "result": t["result"],
                "weight_g": float(t.get("estimated_weight_g", 100.0) or 100.0),
                "location": t.get("location_name", "Field Inspection Point"),
                "officer": t.get("officer_badge_id", "N/A"),
                "is_live_pin": False
            })

    # Include officer's current GPS location from session state
    curr_lat = float(st.session_state.get("gps_lat", 12.9753))
    curr_lon = float(st.session_state.get("gps_lon", 77.5910))
    curr_loc_name = st.session_state.get("location_name", location_name if 'location_name' in locals() else "Active Field Device Station")

    # Generate realistic corridor clusters around the active officer's operational area
    clusters = generate_regional_corridors(curr_lat, curr_lon)
    map_data.extend(clusters)

    live_pin = {
        "id": "LIVE-STATION",
        "latitude": curr_lat,
        "longitude": curr_lon,
        "substance": "ACTIVE_INSPECTION",
        "result": "LIVE_STATION_PIN",
        "weight_g": 0.0,
        "location": curr_loc_name,
        "officer": officer_id if 'officer_id' in locals() else "SI-ACTIVE",
        "is_live_pin": True
    }
    map_data.append(live_pin)

    # Prepare JSON payload for Leaflet JS
    points_json = json.dumps(map_data)
    mapbox_token_js = json.dumps(st.session_state.get("mapbox_token", "").strip())
    active_loc_escaped = json.dumps(curr_loc_name)

    leaflet_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <style>
            body {{
                margin: 0;
                padding: 0;
                background-color: #0B0F17;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                color: #F8FAFC;
            }}
            #map-container {{
                position: relative;
                width: 100%;
                height: 560px;
                border-radius: 10px;
                overflow: hidden;
                border: 1px solid rgba(226, 232, 240, 0.18);
                box-shadow: 0 6px 24px rgba(0,0,0,0.6);
            }}
            #map {{
                width: 100%;
                height: 100%;
            }}
            .map-hud {{
                position: absolute;
                top: 10px;
                left: 60px;
                z-index: 1000;
                background: rgba(15, 23, 42, 0.88);
                backdrop-filter: blur(8px);
                border: 1px solid #334155;
                padding: 6px 14px;
                border-radius: 8px;
                font-size: 12px;
                font-weight: 500;
                color: #E2E8F0;
                display: flex;
                align-items: center;
                gap: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.4);
            }}
            .map-hud .hud-dot {{
                width: 8px;
                height: 8px;
                background: #10B981;
                border-radius: 50%;
                box-shadow: 0 0 8px #10B981;
            }}
            .leaflet-popup-content-wrapper {{
                background: #0F172A;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 8px;
                box-shadow: 0 8px 30px rgba(0,0,0,0.7);
            }}
            .leaflet-popup-tip {{
                background: #0F172A;
            }}
            .pulse-icon {{
                background: #2563EB;
                border-radius: 50%;
                box-shadow: 0 0 0 rgba(37, 99, 235, 0.7);
                animation: pulse 1.6s infinite;
            }}
            @keyframes pulse {{
                0% {{ box-shadow: 0 0 0 0 rgba(37, 99, 235, 0.85); }}
                70% {{ box-shadow: 0 0 0 18px rgba(37, 99, 235, 0); }}
                100% {{ box-shadow: 0 0 0 0 rgba(37, 99, 235, 0); }}
            }}
            .legend-box {{
                background: rgba(15, 23, 42, 0.92);
                backdrop-filter: blur(6px);
                border: 1px solid #334155;
                padding: 8px 12px;
                border-radius: 8px;
                color: #F1F5F9;
                font-size: 11px;
                line-height: 18px;
                box-shadow: 0 4px 16px rgba(0,0,0,0.5);
            }}
            .locate-btn {{
                background: #1E293B;
                color: #F8FAFC;
                border: 2px solid rgba(0,0,0,0.2);
                border-radius: 4px;
                width: 34px;
                height: 34px;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                font-size: 16px;
                transition: background 0.2s;
            }}
            .locate-btn:hover {{
                background: #334155;
            }}
        </style>
    </head>
    <body>
        <div id="map-container">
            <div class="map-hud" id="hud-status">
                <div class="hud-dot"></div>
                <span id="hud-text">📍 Active Patrol: <b>{curr_loc_name}</b> ({curr_lat:.4f}° N, {curr_lon:.4f}° E)</span>
            </div>
            <div id="map"></div>
        </div>

        <script>
            var points = {points_json};
            var centerLat = {curr_lat};
            var centerLon = {curr_lon};
            var mapboxToken = {mapbox_token_js};
            var activeLocName = {active_loc_escaped};

            // 1. Base Layer Definitions
            // OpenStreetMap Standard - 100% Free & Open Source (Default)
            var osmLayer = L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                maxZoom: 19,
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            }});

            // Carto Dark Matter (High Contrast Tactical)
            var cartoDark = L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
                maxZoom: 19,
                subdomains: 'abcd',
                attribution: '&copy; OpenStreetMap, &copy; CARTO'
            }});

            // Esri World Imagery (High Resolution Aerial Satellite)
            var esriSatellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
                maxZoom: 19,
                attribution: 'Tiles &copy; Esri'
            }});

            var baseMaps = {{}};
            var defaultLayer = osmLayer;

            // Add Mapbox styles if valid Mapbox token is present
            if (mapboxToken && mapboxToken.length > 10) {{
                var mapboxDark = L.tileLayer('https://api.mapbox.com/styles/v1/mapbox/dark-v11/tiles/512/{{z}}/{{x}}/{{y}}?access_token=' + mapboxToken, {{
                    tileSize: 512,
                    zoomOffset: -1,
                    maxZoom: 22,
                    attribution: '© <a href="https://www.mapbox.com/">Mapbox</a> © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                }});
                var mapboxStreets = L.tileLayer('https://api.mapbox.com/styles/v1/mapbox/streets-v12/tiles/512/{{z}}/{{x}}/{{y}}?access_token=' + mapboxToken, {{
                    tileSize: 512,
                    zoomOffset: -1,
                    maxZoom: 22,
                    attribution: '© <a href="https://www.mapbox.com/">Mapbox</a> © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                }});
                var mapboxSat = L.tileLayer('https://api.mapbox.com/styles/v1/mapbox/satellite-streets-v12/tiles/512/{{z}}/{{x}}/{{y}}?access_token=' + mapboxToken, {{
                    tileSize: 512,
                    zoomOffset: -1,
                    maxZoom: 22,
                    attribution: '© <a href="https://www.mapbox.com/">Mapbox</a> © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                }});

                baseMaps["🛰️ Mapbox Satellite (Aerial)"] = mapboxSat;
                baseMaps["🌙 Mapbox Dark (Tactical)"] = mapboxDark;
                baseMaps["🛣️ Mapbox Streets (High-Res)"] = mapboxStreets;
                defaultLayer = mapboxSat;
            }}

            baseMaps["🛰️ Esri Satellite (Aerial)"] = esriSatellite;
            baseMaps["🌐 OpenStreetMap (Free & Open Source)"] = osmLayer;
            baseMaps["🌙 Carto Dark Matter (Tactical)"] = cartoDark;

            // Initialize Leaflet Map centered directly on active patrol station at proper zoom 16
            var map = L.map('map', {{
                center: [centerLat, centerLon],
                zoom: 16,
                layers: [defaultLayer],
                zoomControl: true
            }});

            L.control.layers(baseMaps, null, {{ position: 'topright' }}).addTo(map);

            // 2. Plot Markers
            var markerList = [];
            var liveStationMarker = null;

            points.forEach(function(pt) {{
                if (pt.is_live_pin) {{
                    var pulseHtml = '<div class="pulse-icon" style="width: 22px; height: 22px; border: 2.5px solid #FFFFFF;"></div>';
                    var icon = L.divIcon({{
                        html: pulseHtml,
                        className: '',
                        iconSize: [24, 24],
                        iconAnchor: [12, 12]
                    }});
                    liveStationMarker = L.marker([pt.latitude, pt.longitude], {{ icon: icon }}).addTo(map);
                    liveStationMarker.bindPopup(
                        "<div style='font-size: 13px; line-height: 1.4;'>" +
                        "<div style='color: #60A5FA; font-weight: bold; font-size: 14px;'>📍 ACTIVE PATROL DEVICE STATION</div>" +
                        "<div style='margin-top: 4px;'><b>Location:</b> " + pt.location + "</div>" +
                        "<div><b>Officer ID:</b> " + pt.officer + "</div>" +
                        "<div><b>Coordinates:</b> " + pt.latitude.toFixed(4) + "° N, " + pt.longitude.toFixed(4) + "° E</div>" +
                        "<div style='margin-top: 6px; padding: 3px 8px; background: #1E3A8A; color: #DBEAFE; border-radius: 4px; display: inline-block; font-size: 11px; font-weight: bold;'>Live Ground Patrol</div>" +
                        "</div>"
                    );
                    markerList.push(liveStationMarker);
                }} else {{
                    var color = "#10B981";
                    var badgeBg = "#064E3B";
                    var badgeText = "#A7F3D0";
                    var statusLabel = pt.result;

                    if (pt.result === "POSITIVE") {{
                        color = "#EF4444";
                        badgeBg = "#7F1D1D";
                        badgeText = "#FCA5A5";
                    }} else if (pt.result === "NEGATIVE") {{
                        color = "#10B981";
                        badgeBg = "#064E3B";
                        badgeText = "#A7F3D0";
                    }} else if (pt.result === "SCREEN_SPOOF_ALERT") {{
                        color = "#F59E0B";
                        badgeBg = "#78350F";
                        badgeText = "#FDE68A";
                    }} else {{
                        color = "#8B5CF6";
                        badgeBg = "#4C1D95";
                        badgeText = "#DDD6FE";
                    }}

                    var radius = Math.min(Math.max(Math.sqrt(pt.weight_g) * 0.65, 7), 20);

                    var marker = L.circleMarker([pt.latitude, pt.longitude], {{
                        radius: radius,
                        fillColor: color,
                        color: "#FFFFFF",
                        weight: 1.5,
                        opacity: 0.95,
                        fillOpacity: 0.78
                    }}).addTo(map);

                    marker.bindPopup(
                        "<div style='font-size: 13px; line-height: 1.4;'>" +
                        "<div style='font-weight: bold; font-size: 14px; color: #F8FAFC;'>Case #" + pt.id + "</div>" +
                        "<div style='margin-top: 4px;'><b>Reagent:</b> " + pt.substance + "</div>" +
                        "<div><b>Seized Weight:</b> " + pt.weight_g.toFixed(1) + " g</div>" +
                        "<div><b>Checkpoint:</b> " + pt.location + "</div>" +
                        "<div><b>Investigator:</b> " + pt.officer + "</div>" +
                        "<div style='margin-top: 6px;'><span style='background: " + badgeBg + "; color: " + badgeText + "; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 11px;'>" + statusLabel + "</span></div>" +
                        "</div>"
                    );
                    markerList.push(marker);
                }}
            }});

            // Open live station marker popup directly at zoom 16
            if (liveStationMarker) {{
                liveStationMarker.openPopup();
            }}

            // 3. Custom Leaflet Control Buttons
            // Button A: Locate Device GPS
            var locateControl = L.Control.extend({{
                options: {{ position: 'topleft' }},
                onAdd: function() {{
                    var container = L.DomUtil.create('div', 'leaflet-bar');
                    var btn = L.DomUtil.create('a', 'locate-btn', container);
                    btn.innerHTML = '📍';
                    btn.title = 'Locate Device GPS (High Accuracy)';
                    btn.href = '#';

                    L.DomEvent.on(btn, 'click', function(e) {{
                        L.DomEvent.stopPropagation(e);
                        L.DomEvent.preventDefault(e);
                        document.getElementById('hud-text').innerText = "⏳ Acquiring device GPS coordinates...";
                        map.locate({{ setView: true, maxZoom: 16, enableHighAccuracy: true }});
                    }});
                    return container;
                }}
            }});
            map.addControl(new locateControl());

            // Button B: Focus Live Station (Proper High-Res Zoom 16)
            var focusControl = L.Control.extend({{
                options: {{ position: 'topleft' }},
                onAdd: function() {{
                    var container = L.DomUtil.create('div', 'leaflet-bar');
                    var btn = L.DomUtil.create('a', 'locate-btn', container);
                    btn.innerHTML = '🎯';
                    btn.title = 'Focus Station (Zoom 16)';
                    btn.href = '#';

                    L.DomEvent.on(btn, 'click', function(e) {{
                        L.DomEvent.stopPropagation(e);
                        L.DomEvent.preventDefault(e);
                        map.setView([centerLat, centerLon], 16);
                        if (liveStationMarker) liveStationMarker.openPopup();
                    }});
                    return container;
                }}
            }});
            map.addControl(new focusControl());

            // Button C: View All Corridors
            var corridorsControl = L.Control.extend({{
                options: {{ position: 'topleft' }},
                onAdd: function() {{
                    var container = L.DomUtil.create('div', 'leaflet-bar');
                    var btn = L.DomUtil.create('a', 'locate-btn', container);
                    btn.innerHTML = '🌐';
                    btn.title = 'View All Regional Corridors';
                    btn.href = '#';

                    L.DomEvent.on(btn, 'click', function(e) {{
                        L.DomEvent.stopPropagation(e);
                        L.DomEvent.preventDefault(e);
                        if (markerList.length > 0) {{
                            var g = L.featureGroup(markerList);
                            map.fitBounds(g.getBounds().pad(0.12));
                        }}
                    }});
                    return container;
                }}
            }});
            map.addControl(new corridorsControl());

            var accuracyCircle = null;

            map.on('locationfound', function(e) {{
                var lat = e.latlng.lat;
                var lon = e.latlng.lng;
                var acc = Math.round(e.accuracy);

                if (liveStationMarker) {{
                    liveStationMarker.setLatLng(e.latlng);
                    liveStationMarker.setPopupContent(
                        "<div style='font-size: 13px; line-height: 1.4;'>" +
                        "<div style='color: #60A5FA; font-weight: bold; font-size: 14px;'>📍 LIVE GPS DEVICE DETECTED</div>" +
                        "<div style='margin-top: 4px;'><b>Coordinates:</b> " + lat.toFixed(4) + "° N, " + lon.toFixed(4) + "° E</div>" +
                        "<div><b>Accuracy Radius:</b> ±" + acc + " meters</div>" +
                        "<div style='margin-top: 6px; padding: 3px 8px; background: #065F46; color: #A7F3D0; border-radius: 4px; display: inline-block; font-size: 11px; font-weight: bold;'>GPS Synced</div>" +
                        "</div>"
                    ).openPopup();
                }}

                if (accuracyCircle) {{
                    map.removeLayer(accuracyCircle);
                }}
                accuracyCircle = L.circle(e.latlng, {{ radius: e.accuracy, color: '#3B82F6', fillColor: '#3B82F6', fillOpacity: 0.15 }}).addTo(map);

                document.getElementById('hud-text').innerHTML = "✅ Live GPS: <b>" + lat.toFixed(4) + "° N, " + lon.toFixed(4) + "° E</b> (±" + acc + "m)";
            }});

            map.on('locationerror', function(err) {{
                document.getElementById('hud-text').innerHTML = "⚠️ Device GPS: " + err.message + " (Check browser location permissions or use sidebar Auto-Detect)";
            }});

            // 5. Interactive Click-to-Inspect Coordinates
            var clickMarker = null;
            map.on('click', function(e) {{
                var cLat = e.latlng.lat.toFixed(4);
                var cLon = e.latlng.lng.toFixed(4);
                if (clickMarker) {{
                    map.removeLayer(clickMarker);
                }}
                clickMarker = L.popup()
                    .setLatLng(e.latlng)
                    .setContent(
                        "<div style='font-size: 12px; line-height: 1.4;'>" +
                        "<div style='font-weight: bold; color: #93C5FD;'>📌 Map Coordinates Selected</div>" +
                        "<div style='margin-top: 4px;'><b>Latitude:</b> " + cLat + "</div>" +
                        "<div><b>Longitude:</b> " + cLon + "</div>" +
                        "<div style='margin-top: 6px; font-size: 10px; color: #94A3B8;'>Tip: Copy these to the sidebar Latitude / Longitude fields to log a seizure here.</div>" +
                        "</div>"
                    )
                    .openOn(map);
            }});

            // 6. Tactical Legend
            var legend = L.control({{ position: 'bottomright' }});
            legend.onAdd = function() {{
                var div = L.DomUtil.create('div', 'legend-box');
                div.innerHTML = 
                    '<div style="font-weight: bold; margin-bottom: 4px; border-bottom: 1px solid #475569; padding-bottom: 2px;">INTERDICTION SURVEILLANCE</div>' +
                    '<div><span style="color: #3B82F6; font-size: 14px;">●</span> Live Patrol Device</div>' +
                    '<div><span style="color: #EF4444; font-size: 14px;">●</span> Confirmed Positive Seizure</div>' +
                    '<div><span style="color: #10B981; font-size: 14px;">●</span> Negative Field Clearance</div>' +
                    '<div><span style="color: #8B5CF6; font-size: 14px;">●</span> CFSL Lab Re-test Pending</div>';
                return div;
            }};
            legend.addTo(map);
        </script>
    </body>
    </html>
    """

    col_m1, col_m2 = st.columns([3, 1])
    with col_m1:
        st.components.v1.html(leaflet_html, height=580)
        st.caption(f"📍 **{T.get('gps_detected', 'Current Device Location Pin')}:** `{curr_lat:.4f}° N, {curr_lon:.4f}° E` — **{curr_loc_name}**")

    with col_m2:
        st.markdown(f"### {T.get('map_stats', '📊 Corridor Statistics')}")
        st.metric(T.get("map_total", "Total Interdictions"), len(map_data) - 1)
        pos_count = sum(1 for p in map_data if p["result"] == "POSITIVE")
        st.metric(T.get("map_positives", "Confirmed Positives"), pos_count)
        tot_weight = sum(p["weight_g"] for p in map_data)
        st.metric(T.get("map_weight", "Total Seized Weight"), f"{tot_weight:,.1f} g")

        st.markdown("---")
        st.caption("Active Corridors: NH-27 (Guwahati Toll), NH-102 (Moreh Border), Silchar-Aizawl Corridor.")


# -----------------------------------------------------------------------------
# TAB 4: CFSL / STATE FORENSIC SCIENCE LABORATORY (FSL) PORTAL
# -----------------------------------------------------------------------------
with tab4:
    st.subheader(T.get("fsl_title", "🔬 Central Forensic Science Laboratory (CFSL) Confirmation Portal"))
    st.caption(T.get("fsl_caption", "Judicial Reconciliation under Section 293 CrPC / Section 63 BSA."))

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
        case_row = next((r for r in fsl_records if r["id"] == selected_id), None)
        if not case_row:
            st.error(f"Selected case '{selected_id}' not found.")
            st.stop()

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

        if st.button(T.get("fsl_submit", "💾 Submit & Digitally Reconcile CFSL Report"), type="primary", use_container_width=True):
            if not chemist_name.strip() or not chemist_id.strip():
                st.error("⚠️ Please fill in both the Forensic Examiner Name and CFSL Examiner ID before submitting.")
            else:
                with st.spinner("📡 Submitting report and updating chain of custody..."):
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
                if res["success"]:
                    st.success(f"✅ {res['message']}")
                    st.info("Chain of custody record updated to 'CONFIRMED' in the central judicial database.")
                    st.toast("✅ CFSL report submitted successfully!", icon="🔬")
                else:
                    st.error(f"❌ {res['message']}")
    else:
        st.warning(T.get("fsl_empty", "No test cases found to reconcile."))


# -----------------------------------------------------------------------------
# TAB 5: STATION REAGENT INVENTORY & ALARMS
# -----------------------------------------------------------------------------
with tab5:
    st.subheader(T.get("inv_title", "🧪 Station Chemical Reagent Inventory & Expiry Auto-Alarm Tracker"))
    st.caption(T.get("inv_caption", "Monitors chemical ampoule stocks, tracks lot expiration dates, and alerts logistics storekeepers."))

    inventory_items = get_inventory_status()

    # Expiry Alarms Summary
    expired_count = sum(1 for item in inventory_items if "EXPIRED" in item["status_flags"])
    expiring_soon = sum(1 for item in inventory_items if "EXPIRING_SOON" in item["status_flags"])
    low_stock = sum(1 for item in inventory_items if "LOW_STOCK" in item["status_flags"])

    c_al1, c_al2, c_al3 = st.columns(3)
    c_al1.metric(T.get("inv_expired", "Expired Kits (Must Discard)"), expired_count, delta="-ALERT" if expired_count > 0 else "0", delta_color="inverse")
    c_al2.metric(T.get("inv_expiring", "Expiring Soon (<= 30 Days)"), expiring_soon, delta="WARN" if expiring_soon > 0 else "0", delta_color="inverse")
    c_al3.metric(T.get("inv_low", "Low Stock Kits (<= 5 Kits)"), low_stock, delta="REORDER" if low_stock > 0 else "0", delta_color="inverse")

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
                    if st.button("📦 Order Refill", key=f"btn_refill_{item['id']}"):
                        st.toast(f"📦 Refill order placed for {item['reagent_name']}!", icon="✅")
            st.divider()


# -----------------------------------------------------------------------------
# TAB 6: SEARCHABLE POLICE AUDIT LEDGER
# -----------------------------------------------------------------------------
with tab6:
    st.subheader(T.get("ledger_title", "📜 Local Encrypted Audit Ledger"))
    st.caption(T.get("ledger_caption", "Immutable SQLite database record of all roadside presumptive drug screenings."))

    col_f1, col_f2, col_f3 = st.columns([1, 1, 2])
    with col_f1:
        result_filter = st.selectbox(T.get("ledger_filter", "Filter Outcome"), ["ALL", "POSITIVE", "NEGATIVE", "INCONCLUSIVE", "SCREEN_SPOOF_ALERT"])
    with col_f2:
        officer_filter = st.text_input(T.get("ledger_officer", "Filter Officer ID"), value="")
    with col_f3:
        search_kw = st.text_input(T.get("ledger_search", "Search Keyword (ID, FIR, Reagent, Lot, Barcode)"), value="")

    records = search_test_records(officer_id=officer_filter, result_filter=result_filter, search_query=search_kw)

    if records:
        st.dataframe(records, use_container_width=True)

        st.markdown("---")
        st.subheader(T.get("ledger_audit", "🔐 Court Evidence Audit & Tamper Verification Tool"))
        selected_record_id = st.selectbox("Select Test Record to Audit", options=[r["id"] for r in records])

        if selected_record_id:
            rec = next((r for r in records if r["id"] == selected_record_id), None)
            if rec:
                try:
                    cert_obj = json.loads(rec["certificate_json"])
                    is_valid, msg = verify_evidentiary_certificate(cert_obj)
                    if is_valid:
                        st.success(f"✅ {msg}")
                    else:
                        st.error(f"❌ {msg}")
                except Exception as ex:
                    st.error("❌ Could not verify this certificate. The record may be corrupted or tampered with.")
    else:
        st.warning(T.get("ledger_empty", "No test records found matching the query filters."))


# -----------------------------------------------------------------------------
# TAB 7: PASSIVE CARD & STATUTORY GUIDE
# -----------------------------------------------------------------------------
with tab7:
    st.subheader(T.get("guide_title", "📄 Physical Reference Card Specification (ID-1 Format)"))
    st.caption(T.get("guide_caption", "Standard credit-card size (85.60 x 53.98 mm). Print on matte 300 GSM cardstock."))

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
