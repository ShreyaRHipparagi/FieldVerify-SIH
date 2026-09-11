# BASELINE.md: FieldVerify AI Initial Quality & Architectural Baseline

## 1. System & Environment Baseline
- **Python Runtime**: Python 3.13.7 (64-bit on Windows)
- **Pytest Version**: pytest 9.1.1
- **Package Architecture**:
  - `fieldverify`: Root namespace package
    - `fieldverify.core`: Core forensic modules (`crypto.py`, `db.py`, `fsl.py`, `inventory.py`, `optical.py`, `panchnama.py`, `pdf_generator.py`, `reagent.py`)
    - `fieldverify.utils`: Utilities (`card_generator.py`, `sample_generator.py`)
  - `app.py`: Streamlit dashboard application (7 tabs: Field Test, Auto-Panchnama, Heatmap, CFSL Portal, Inventory, Audit Ledger, Reference Card)
  - `run_app.py`: Auto-launcher detecting local Wi-Fi IP and finding available ports
  - `tests/test_fieldverify.py`: Test suite containing 13 tests

## 2. Test Execution Baseline
- **Direct Pytest Command (`pytest -v`)**:
  - **Status**: FAILED (Collection Error)
  - **Cause**: `ModuleNotFoundError: No module named 'fieldverify'` due to lack of packaging/install configuration (`pyproject.toml` / `setup.py` / `pytest.ini` with `pythonpath = .`).
- **Module Pytest Command (`python -m pytest -v`)**:
  - **Total Tests**: 13
  - **Passed**: 13 (100%)
  - **Failed**: 0
  - **Errors**: 0
  - **Skipped**: 0
  - **Duration**: ~1.87 seconds
- **Test Coverage**:
  - `coverage` package is not installed in the current environment.

## 3. Static Analysis & Compilation
- **`python -m compileall -q .`**: Clean exit (0 syntax errors).
- **Linter / Type Checkers (`ruff`, `mypy`, `pylint`, `flake8`)**: Not installed in the environment.

## 4. Initial Architectural & Correctness Observations
1. **Packaging & Test Discovery**:
   - Running `pytest` without `python -m` fails because the project root is not in `sys.path`. A `pyproject.toml` or `pytest.ini` configuring `pythonpath = .` is needed.
   - Missing `requirements.txt` / `pyproject.toml` specifying dependencies (`streamlit`, `opencv-python`, `cryptography`, `reportlab`, `qrcode`, etc.).
2. **Database Concurrency & Resource Leaks**:
   - Several database functions open `sqlite3.connect(...)` without using context managers (`with conn:` or `try...finally: conn.close()`), risking leaked connections or uncommitted transactions during exceptions.
   - `sqlite3` does not enforce WAL mode or busy timeouts; concurrent access across Streamlit threads may cause `sqlite3.OperationalError: database is locked`.
3. **Cryptographic Key Lifetime & State**:
   - `_DEVICE_PRIVATE_KEY` in `crypto.py` is regenerated on every process restart. Any record signed in a previous process run cannot be verified with `_DEVICE_PUBLIC_KEY` unless `device_public_key_pem` embedded in the certificate is used.
   - In `verify_evidentiary_certificate`: if `public_key_pem is None: public_key_pem = cert_copy.get("device_public_key_pem")`. If the certificate embeds its own public key, an attacker who alters the record could also replace `device_public_key_pem` and re-sign it with their own key, and `verify_evidentiary_certificate` would return `SIGNATURE_VALID`!
4. **Optical Calibration & Coordinate Geometry**:
   - In `rectify_reference_card`: ArUco marker centers are mapped to `[0, 0]`, `[target_w, 0]`, `[target_w, target_h]`, `[0, target_h]`. But on the physical reference card, ArUco markers are placed inset with centers at `(70, 70)`, `(930, 70)`, `(930, 530)`, `(70, 530)`. Warping marker centers to canvas bounds distorts internal ROIs (e.g. White Patch and Pouch Zone).
   - In `calibrate_and_extract_color`: Glare mask definition `(v_channel >= 235) | (s_channel < 30)` treats low-saturation colors (e.g. pale white/gray reaction liquids, blank tests, white precipitates) as specular glare and discards them.
   - In `optical.ciede2000`: Hue difference calculation `abs(h1_p - h2_p) > 180` and `avg_h_p` standard CIE 2000 logic needs audit for edge cases near zero and 360 degrees.
5. **Panchnama & Data Type Robustness**:
   - In `panchnama.py`: `lat, lon = data.get("gps_coords", (26.1445, 91.7362))`. If `data["gps_coords"]` is passed as a dict `{"lat": ..., "lon": ...}` or if `gps_coords` is `None`, unpacking fails with `TypeError` or formatting fails with `TypeError: unsupported format string`.
6. **Reagent Expiry & Date Validation**:
   - In `reagent.py`: `exp_date = datetime.strptime(exp_str, "%Y-%m-%d")` evaluates midnight UTC `00:00:00`. Testing on the date of expiry causes false expiration alerts. Malformed date formats silently pass as unexpired.
7. **Streamlit App State & Concurrency**:
   - `st.session_state` values can be absent across tab navigation or reload, leading to `KeyError` or missing fallback.
