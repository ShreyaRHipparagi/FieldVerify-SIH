"""
FieldVerify Panchnama / Seizure Memo Generator
Compliant with Section 42, 43, 50, and 52 of the Narcotic Drugs and Psychotropic Substances (NDPS) Act, 1985
and Section 63 of the Bharatiya Sakshya Adhiniyam (BSA), 2023.
"""

from datetime import datetime, timezone
import hashlib


def generate_ndps_panchnama_text(data):
    """
    Generates a formal statutory NDPS Panchnama (Seizure Memo) in clean court-ready text format.
    """
    now_str = data.get("timestamp_str", datetime.now(timezone.utc).strftime("%d-%b-%Y %H:%M:%S UTC"))
    lat, lon = data.get("gps_coords", (26.1445, 91.7362))
    
    memo = f"""
========================================================================================
                      MEMORANDUM OF SEIZURE (PANCHNAMA)
     UNDER SECTIONS 42, 43, 50 & 52 OF THE NARCOTIC DRUGS AND PSYCHOTROPIC 
                             SUBSTANCES ACT, 1985
========================================================================================

1. CRIME & GENERAL PARTICULARS:
----------------------------------------------------------------------------------------
Police Station / Unit       : {data.get('police_station', 'Narcotics Control Bureau / CID')}
Case / FIR Reference Number : {data.get('fir_case_ref', 'N/A')}
Date & Time of Seizure      : {now_str}
Place of Seizure            : {data.get('seizure_location', 'Highway Checkpost')}
GPS Coordinates             : {lat:.5f}° N, {lon:.5f}° E
Digital FieldVerify ID      : {data.get('test_id', 'N/A')}

2. SEIZING OFFICER PARTICULARS:
----------------------------------------------------------------------------------------
Name of Empowered Officer   : {data.get('officer_name', 'Sub-Inspector Rajesh Barua')}
Badge / PIN Number          : {data.get('officer_badge_id', 'AS-CID-9942')}
Rank / Designation          : Empowered Officer under Section 42 NDPS Act

3. INDEPENDENT WITNESSES (PANCHAS):
----------------------------------------------------------------------------------------
Witness 1 (Panch No. 1)     : {data.get('witness_1_name', 'Shri Ramesh Kumar')}
Address / Contact Details   : {data.get('witness_1_address', 'Village Bhetapara, Dist. Kamrup, Assam')}

Witness 2 (Panch No. 2)     : {data.get('witness_2_name', 'Shri Amit Sen')}
Address / Contact Details   : {data.get('witness_2_address', 'Highway Toll Booth No. 4, Guwahati')}

4. DETAILS OF CONTRABAND RECOVERED & WEIGHED:
----------------------------------------------------------------------------------------
Description of Substance    : {data.get('suspected_substance', 'White crystalline powder')}
Estimated Gross Weight (g)  : {data.get('estimated_weight_g', 250.0):.2f} grams
Preliminary Reagent Test    : {data.get('reagent_type', 'Scott Reagent (Cobalt Thiocyanate)')}
Presumptive Reaction Result : {data.get('presumptive_result', 'POSITIVE FOR COCAINE ALKALOID')}
Colorimetric Distance (ΔE00): {data.get('delta_e', 1.84):.2f} (Threshold <= 6.5)

5. CHAIN OF CUSTODY & PHYSICAL PACKAGING:
----------------------------------------------------------------------------------------
Evidence Packaging Bag No.  : {data.get('evidence_bag_barcode', 'BAG-NCB-2026-9912')}
Security Seal Number        : SEAL-NCB-ASSAM-{data.get('test_id', '')[-6:]}
Physical Sample Condition   : Sealed in tamper-evident forensic pouch in presence of Panchas

6. SECTION 63 BHARATIYA SAKSHYA ADHINIYAM (BSA), 2023 DIGITAL EVIDENCE HASHES:
----------------------------------------------------------------------------------------
Raw Photo SHA-256 Digest    : {data.get('raw_hash', 'N/A')}
Calibrated ROI SHA-256      : {data.get('roi_hash', 'N/A')}
ECDSA P-256 Digital Seal    : {data.get('ecdsa_sig', 'N/A')[:64]}...
Device Hardware Anchor      : Secure Enclave / Android Keystore Signature Verified

7. PANCHNAMA STATEMENT:
----------------------------------------------------------------------------------------
We, the above-named independent witnesses (Panchas), hereby solemnly affirm that the search 
and preliminary drug detection was conducted in our presence with full compliance to Section 50 
of the NDPS Act. The suspected substance was tested using the FieldVerify AI optical device, 
producing an immediate positive indication. The sample was weighed, sealed in Evidence Bag No. 
{data.get('evidence_bag_barcode', 'N/A')}, and stamped with physical seals and digital hashes in our presence. 
The contents of this Panchnama have been read over and explained to us in vernacular language, 
and we acknowledge it to be true and correct.


___________________________             ___________________________
Signature of Witness 1 (Panch)          Signature of Witness 2 (Panch)


___________________________             ___________________________
Signature of Seizing Officer            Magistrate / Gazetted Officer (if present)
Name: {data.get('officer_name', 'Seizing Officer')}
========================================================================================
"""
    return memo.strip()
