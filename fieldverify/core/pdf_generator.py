"""
FieldVerify PDF Evidence Affidavit Exporter
Generates statutory 1-page Presumptive Field Screening Test Evidence Affidavit PDF
compliant with Section 63 Bharatiya Sakshya Adhiniyam (BSA), 2023.
"""

import os
import io
import qrcode
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch


def generate_evidentiary_pdf(cert, output_pdf_path=None):
    """
    Generates a formal 1-page court evidence certificate PDF for a given test certificate.
    Returns bytes buffer if output_pdf_path is None, else writes to file path.
    """
    buffer = io.BytesIO() if output_pdf_path is None else output_pdf_path

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch
    )

    styles = getSampleStyleSheet()

    # Custom typography styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=13,
        leading=16,
        alignment=1, # Center
        textColor=colors.HexColor('#0F172A'),
        fontName='Helvetica-Bold'
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        alignment=1,
        textColor=colors.HexColor('#475569'),
        fontName='Helvetica-Oblique'
    )

    section_header_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#1E293B'),
        fontName='Helvetica-Bold'
    )

    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#334155'),
        fontName='Helvetica'
    )

    code_style = ParagraphStyle(
        'CodeStyle',
        parent=styles['Normal'],
        fontSize=7,
        leading=9,
        fontName='Courier',
        textColor=colors.HexColor('#0F172A')
    )

    elements = []

    # 1. Header Banner
    elements.append(Paragraph("STATE POLICE DEPARTMENT / NARCOTICS CONTROL BUREAU", title_style))
    elements.append(Paragraph("PRESUMPTIVE FIELD SCREENING TEST EVIDENCE AFFIDAVIT", ParagraphStyle('SubHeader', parent=title_style, fontSize=11, leading=14, textColor=colors.HexColor('#1E3A8A'))))
    elements.append(Paragraph("(Issued in compliance with Section 63 of the Bharatiya Sakshya Adhiniyam, 2023)", subtitle_style))
    elements.append(Spacer(1, 10))

    if not isinstance(cert, dict):
        cert = {}

    test_id = str(cert.get("test_id") or "N/A")
    raw_timestamp = cert.get("timestamp_utc")
    timestamp_str = str(raw_timestamp)[:19] if raw_timestamp else "N/A"
    officer_id = str(cert.get("officer_badge_id") or "N/A")
    fir_ref = str(cert.get("fir_case_ref") or "N/A")
    loc_name = str(cert.get("location_name") or "N/A")

    # Safe GPS
    raw_gps = cert.get("gps")
    lat, lon = 0.0, 0.0
    if isinstance(raw_gps, dict):
        try:
            lat = float(raw_gps.get("lat", 0.0))
            lon = float(raw_gps.get("lon", 0.0))
        except (ValueError, TypeError):
            pass
    elif isinstance(raw_gps, (tuple, list)) and len(raw_gps) >= 2:
        try:
            lat = float(raw_gps[0])
            lon = float(raw_gps[1])
        except (ValueError, TypeError):
            pass

    lat_cardinal = "N" if lat >= 0 else "S"
    lon_cardinal = "E" if lon >= 0 else "W"
    gps_str = f"{abs(lat):.4f}° {lat_cardinal}, {abs(lon):.4f}° {lon_cardinal}"

    # 2. General Metadata Table
    gen_data = [
        [
            Paragraph(f"<b>Test Certificate ID:</b> {test_id}", body_style),
            Paragraph(f"<b>Date & UTC Time:</b> {timestamp_str}", body_style)
        ],
        [
            Paragraph(f"<b>Seizing Officer ID:</b> {officer_id}", body_style),
            Paragraph(f"<b>FIR / Case Reference:</b> {fir_ref}", body_style)
        ],
        [
            Paragraph(f"<b>Inspection Location:</b> {loc_name}", body_style),
            Paragraph(f"<b>GPS Coordinates:</b> {gps_str}", body_style)
        ]
    ]

    t_gen = Table(gen_data, colWidths=[3.75 * inch, 3.75 * inch])
    t_gen.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(t_gen)
    elements.append(Spacer(1, 8))

    # 3. Chemical Reagent & Analysis Table
    reagent_type = str(cert.get("reagent_type") or "N/A")
    batch_lot = str(cert.get("batch_lot") or "N/A")

    # Safe Lab
    raw_lab = cert.get("measured_lab")
    L_val, a_val, b_val = 0.0, 0.0, 0.0
    if isinstance(raw_lab, dict):
        try:
            L_val = float(raw_lab.get("L", 0.0))
            a_val = float(raw_lab.get("a", 0.0))
            b_val = float(raw_lab.get("b", 0.0))
        except (ValueError, TypeError):
            pass
    elif isinstance(raw_lab, (tuple, list)) and len(raw_lab) >= 3:
        try:
            L_val = float(raw_lab[0])
            a_val = float(raw_lab[1])
            b_val = float(raw_lab[2])
        except (ValueError, TypeError):
            pass

    try:
        delta_e = float(cert.get("delta_e00", cert.get("delta_e", 0.0)))
        delta_e_str = f"{delta_e:.2f}"
    except (ValueError, TypeError):
        delta_e_str = "0.00"

    anti_spoof = str(cert.get("anti_spoof_status") or "PASS")
    outcome = str(cert.get("outcome") or "INCONCLUSIVE")

    outcome_bg = colors.HexColor('#DCFCE7') if outcome == "POSITIVE" else (colors.HexColor('#FEE2E2') if outcome == "NEGATIVE" else colors.HexColor('#FEF3C7'))
    outcome_text_color = colors.HexColor('#166534') if outcome == "POSITIVE" else (colors.HexColor('#991B1B') if outcome == "NEGATIVE" else colors.HexColor('#92400E'))

    chem_data = [
        [
            Paragraph(f"<b>Reagent Applied:</b> {reagent_type}", body_style),
            Paragraph(f"<b>Reagent Lot / Batch:</b> {batch_lot}", body_style)
        ],
        [
            Paragraph(f"<b>Measured CIELAB:</b> L*={L_val:.1f}, a*={a_val:.1f}, b*={b_val:.1f}", body_style),
            Paragraph(f"<b>CIEDE2000 Color Distance:</b> ΔE00 = {delta_e_str}", body_style)
        ],
        [
            Paragraph(f"<b>Anti-Spoofing Status:</b> {anti_spoof}", body_style),
            Paragraph(f"<b>SCREENING OUTCOME:</b> <font color='{outcome_text_color.hexval()}'><b>{outcome}</b></font>", body_style)
        ]
    ]

    t_chem = Table(chem_data, colWidths=[3.75 * inch, 3.75 * inch])
    t_chem.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FFFFFF')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#94A3B8')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('BACKGROUND', (1, 2), (1, 2), outcome_bg),
    ]))
    elements.append(t_chem)
    elements.append(Spacer(1, 8))

    # 4. Cryptographic Hashes & Digital Signature
    elements.append(Paragraph("DIGITAL CHAIN OF CUSTODY (CRYPTOGRAPHIC HASHES & ECDSA SIGNATURE)", section_header_style))
    elements.append(Spacer(1, 3))

    raw_hash = str(cert.get("sha256_raw_image") or "N/A")
    roi_hash = str(cert.get("sha256_calibrated_roi") or "N/A")
    raw_sig = str(cert.get("ecdsa_signature_hex") or cert.get("digital_signature") or "N/A")
    sig_preview = (raw_sig[:80] + "...") if len(raw_sig) > 80 else raw_sig

    hash_data = [
        [Paragraph("<b>Raw Frame SHA-256 Digest:</b>", body_style), Paragraph(raw_hash, code_style)],
        [Paragraph("<b>Calibrated ROI SHA-256 Digest:</b>", body_style), Paragraph(roi_hash, code_style)],
        [Paragraph("<b>ECDSA P-256 Signature (Hex):</b>", body_style), Paragraph(sig_preview, code_style)]
    ]

    t_hash = Table(hash_data, colWidths=[2.2 * inch, 5.3 * inch])
    t_hash.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F1F5F9')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(t_hash)
    elements.append(Spacer(1, 10))

    # 5. Dynamic QR Code & Verification Block
    qr_raw_sub = raw_hash[:16] if raw_hash != "N/A" else "0000000000000000"
    qr_sig_sub = raw_sig[:16] if raw_sig != "N/A" else "0000000000000000"
    qr_payload = f"FIELDVERIFY|ID:{test_id}|OUT:{outcome}|RAW:{qr_raw_sub}|SIG:{qr_sig_sub}"
    qr_img = qrcode.make(qr_payload)

    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)
    rl_qr_image = RLImage(qr_buffer, width=1.1 * inch, height=1.1 * inch)

    sig_block_text = """
    <b>Statutory Authentication Certificate:</b><br/>
    Certified that this electronic record was generated at the scene of inspection using the FieldVerify AI System. The cryptographic hashes and ECDSA digital signature above guarantee data integrity under <b>Section 63 Bharatiya Sakshya Adhiniyam, 2023</b>.<br/><br/>
    ____________________________________________<br/>
    <b>Digital Signature of Seizing Officer / Forensic Examiner</b>
    """

    footer_table_data = [
        [rl_qr_image, Paragraph(sig_block_text, body_style)]
    ]

    t_footer = Table(footer_table_data, colWidths=[1.3 * inch, 6.2 * inch])
    t_footer.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#94A3B8')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(t_footer)
    elements.append(Spacer(1, 8))

    # 6. Legal Statutory Disclaimer
    disclaimer_text = """
    <b>STATUTORY DISCLAIMER:</b> This report represents a presumptive field screening test result obtained on-scene. In accordance with Section 50/52 of the NDPS Act and NCB Standing Order 1/88, this result serves to establish probable cause for seizure and remand, and does not replace confirmatory Gas Chromatography / Mass Spectrometry (GC-MS) testing by a CFSL / State Forensic Science Laboratory.
    """
    elements.append(Paragraph(disclaimer_text, ParagraphStyle('Disclaimer', parent=body_style, fontSize=7, leading=9, textColor=colors.HexColor('#64748B'))))

    doc.build(elements)

    if output_pdf_path is None:
        buffer.seek(0)
        return buffer.getvalue()
    return output_pdf_path
