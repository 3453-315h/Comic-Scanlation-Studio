# Comic Scanlation Studio — Round 4 Final Verification Report

**Date**: 2026-09-27  
**Base Commit (Start SHA)**: `ab9f114960300b69f03f02f32d7cd522411e9a43`  
**Final Commit (Final SHA)**: `fe26a868f9f00bb69f043926b99f3d254a54907d`  
**Repository**: [https://github.com/3453-315h/Comic-Scanlation-Studio](https://github.com/3453-315h/Comic-Scanlation-Studio)  

---

## 1. Executive Summary & Plain Pipeline Statement

### Plain Pipeline Statement
- **Real-PC Scanlation Execution**: **PARTIALLY PASSED / BLOCKED ON NEURAL DEPENDENCIES**
  - **PASSED**: The real end-to-end pipeline was executed live using the built-in offline **OpenCV 5.0.0.93** contour detector, OpenCV Telea inpainter, Qt `TextImprinter` typesetting engine, portable `Project` persistence, CBZ archive export, PDF document export, and two-page batch processing with controlled failure handling. Pixel-level analysis confirmed proper inpaint text clearing and typesetting rendering.
  - **BLOCKED**: Full live execution of the PyTorch/DirectML AI models (**YOLOv8**, **MangaOCR**, **LaMa**, **RapidOCR**) cannot execute on this Linux host environment because heavy neural network packages (`torch`, `ultralytics`, `transformers`, `manga_ocr`, `simple_lama_inpainting`, `rapidocr_onnxruntime`) are **NOT installed** in the virtual environment, and `onnxruntime-directml` is Windows-only. The application cleanly diagnosed the missing dependencies, fell back safely, and refused to mislabel CPU runs as GPU.
- **Model Trust & Security Lifecycle**: **PASSED (100%)**
  - Scoped, revocable cryptographic decisions are stored in `models/model_trust.json`.
  - Zero broad booleans stored in `config.json`.
  - Both `.pt` and derived `.onnx` models fail closed if unapproved, modified, or tampered.
  - Revocation of base model cascades to derived ONNX exports.
- **Unit Test Suite**: **PASSED (85/85 tests passed in 1.13s)**
  - All 76 existing Round 1–3 tests preserved and passing.
  - 9 new Round 4 tests added in `tests/test_round4_trust.py`.

---

## 2. Environment Diagnostics

The following environment was inspected live via `sys`, `platform`, `cv2`, `PySide6`, and `onnxruntime`:

| Component | Status / Version | Notes |
| :--- | :--- | :--- |
| **Operating System** | `Linux-7.2.5-3-omarchy-x86_64-with-glibc2.44` | Linux x86_64 host |
| **Python** | `3.11.16` | Clang 22.1.3 |
| **GUI Framework** | `PySide6 6.11.2` / `Qt 6.11.2` | Clean headless offscreen operation |
| **OpenCV** | `5.0.0.93` (`cv2 5.0.0`) | `opencv-python-headless` |
| **ONNX Runtime** | `1.30.0` | Providers: `['AzureExecutionProvider', 'CPUExecutionProvider']` |
| **DirectML Provider** | `NOT AVAILABLE` | DirectML requires Windows DirectX 12 + `onnxruntime-directml` |
| **PyTorch (`torch`)** | `NOT INSTALLED` | Blocked on this Linux virtualenv |
| **Ultralytics (`ultralytics`)** | `NOT INSTALLED` | Blocked on this Linux virtualenv |
| **Transformers (`transformers`)** | `NOT INSTALLED` | Blocked on this Linux virtualenv |
| **MangaOCR (`manga_ocr`)** | `NOT INSTALLED` | Blocked on this Linux virtualenv |
| **LaMa Inpainting** | `NOT INSTALLED` | Blocked on this Linux virtualenv |
| **RapidOCR (`rapidocr_onnxruntime`)** | `NOT INSTALLED` | Blocked on this Linux virtualenv |
| **Googletrans (`googletrans`)** | `NOT INSTALLED` | Blocked on this Linux virtualenv |

---

## 3. Real Model Artifact Evaluation & Provenance

The official remote model URL for the specialized comic speech bubble detector was evaluated directly via streaming HTTP requests:

- **Source URL**: `https://huggingface.co/ogkalu/comic-speech-bubble-detector-yolov8m/resolve/main/comic-speech-bubble-detector.pt`
- **File Name**: `comic-speech-bubble-detector.pt`
- **Exact Size**: `52,079,361` bytes (~52.1 MB)
- **Computed SHA-256 Digest**: `10bc9f702698148e079fb4462a6b910fcd69753e04838b54087ef91d5633097b`
- **Verification Analysis**:
  - The model creator (`ogkalu`) does not publish a cryptographically signed checksum ledger or GPG signature on HuggingFace.
  - Computing a hash of the stream proves transport integrity at retrieval time, but does **not** constitute an independently verified publisher identity.
  - Therefore, the model remains **unpinned** in `DETECTOR_MODEL_REGISTRY`, requiring explicit, scoped user confirmation in **Settings > Manage AI Models**.
  - Once confirmed, the file's exact SHA-256 is recorded in `models/model_trust.json` and verified across every load and restart.

---

## 4. Numbered Fix Verification Matrix

### Item 1: Unverified-Model Consent Handoff & Scoped Trust Persistence
- **Status**: **PASS**
- **Changes**:
  - `src/core/security.py`: Implemented `compute_file_sha256()`, atomic `load_trust_records()`, `save_trust_records()`, `record_approved_model()`, `revoke_approved_model()`, and `is_model_trusted()`.
  - `src/modules/detector.py`: Updated `acquire_detector_model` and `YOLOTextDetector._load_model` to verify models against `models/model_trust.json` without requiring global `allow_unverified` flags. Unapproved weights raise `ModelNotFoundError` without prompting in non-interactive contexts.
  - `src/gui/dialogs/download_models_dialog.py`: Updated table to show `✓ Approved` when trusted and `⚠ Unapproved` if weights are present without trust. Added `_revoke_trust()` handler and GUI button to revoke stored decisions at will.
- **Evidence**:
  - `tests/test_round4_trust.py::test_record_and_verify_approved_model_persisted` PASSED
  - `tests/test_round4_trust.py::test_tampered_or_replaced_model_fails_closed` PASSED
  - `tests/test_round4_trust.py::test_restart_preserves_trust_decision` PASSED
  - `tests/test_round4_trust.py::test_download_models_dialog_revoke_trust_gui_action` PASSED

### Item 2: Close ONNX Trust Bypass & Validate Provenance
- **Status**: **PASS**
- **Changes**:
  - `src/modules/detector_onnx.py`:
    - Updated `__init__`: Registered detector models (such as `comic-speech-bubble-detector.onnx`) are validated via `is_registered_detector` and `is_model_trusted` before `super().__init__` or session creation.
    - Updated `_configure_onnx_providers`: Checks trust before instantiating `ort.InferenceSession`.
    - Updated `_export_to_onnx`: Links exported `.onnx` models to the approved parent `.pt` SHA-256 via `parent_sha256`.
  - `src/core/security.py`:
    - `is_model_trusted()` verifies that if an ONNX model specifies `parent_sha256`, the parent model record and physical parent file on disk must match.
    - `revoke_approved_model()` automatically cascade-revokes any child ONNX models referencing the revoked parent SHA.
- **Evidence**:
  - `tests/test_round4_trust.py::test_unapproved_onnx_cannot_bypass_gate_by_expected_name` PASSED
  - `tests/test_round4_trust.py::test_onnx_derived_model_provenance_and_validation` PASSED
  - `tests/test_round4_trust.py::test_revocation_cascades_from_parent_to_child` PASSED

### Item 3: Correct README First-Use Instructions & Hardware Accuracy
- **Status**: **PASS**
- **Changes**:
  - `readme.md`:
    - Clarified that the default detector is unpinned and will **never** silently auto-download on "Process All".
    - Provided clear step-by-step instructions for explicit download & approval via **Settings > Manage AI Models**.
    - Explained persistent trust storage in `models/model_trust.json`, reuse without prompts, and revocation via GUI or `security.py`.
    - Documented the 100% offline alternative: built-in **OpenCV 5** contour detector (`DETECTOR_MODEL="opencv"`).
    - Clarified hardware constraints: DirectML requires Windows and `onnxruntime-directml`; CPU runs are never mislabeled as DirectML or GPU.
    - Corrected model sizes: ~52 MB (.pt), ~100 MB (.onnx export).
- **Evidence**:
  - `tests/test_finding_11_metadata_coherence.py::test_version_coherence` PASSED
  - `tests/test_finding_11_metadata_coherence.py::test_readme_links_and_referenced_files` PASSED

### Item 4: Real-PC Scanlation Validation & Batch Processing
- **Status**: **PASS (Local OpenCV 5 Engine) / BLOCKED (Neural AI Weights on Linux)**
- **Script**: `scratch/validate_real_scanlation.py`
- **Results**:
  - Real OpenCV 5 Contour Detection: PASSED (detected bubble at `[147, 147, 654, 354]`, confidence 0.98).
  - Real Inpainting (OpenCV Telea): PASSED (237,132 pixel value modifications; original text cleared).
  - Real Typesetting (Qt `TextImprinter`): PASSED (8,613,267 pixel value modifications; text cleanly rendered).
  - Project Persistence: PASSED (`project.json` saved with relative paths, reloaded cleanly).
  - Archive/Document Export: PASSED (`export_output.cbz` 27,443 bytes; `export_output.pdf` 72,794 bytes).
  - Two-Page Batch with Controlled Failure: PASSED (Page 1 succeeded, Page 2 failed cleanly with `FileNotFoundError`, original Page 1 pixels preserved 100% intact).

### Item 5: Report & Git Hygiene
- **Status**: **PASS**
- **Changes**:
  - Created `report.md` in repository root.
  - Updated `.gitignore` to ignore `scratch/`, `.venv/`, and `comic-scanlation-round*.txt`.
  - Zero heavy weights, user trust records, or generated media committed to Git.

---

## 5. Detailed End-to-End Real Validation Evidence

The live validation script (`scratch/validate_real_scanlation.py`) produced the following exact results:

```json
{
  "environment": {
    "os": "Linux-7.2.5-3-omarchy-x86_64-with-glibc2.44",
    "python": "3.11.16",
    "machine": "x86_64",
    "cv2": "5.0.0",
    "pyside6": "6.11.2",
    "onnxruntime": "1.30.0",
    "onnx_providers": ["AzureExecutionProvider", "CPUExecutionProvider"],
    "torch": "NOT INSTALLED",
    "ultralytics": "NOT INSTALLED",
    "transformers": "NOT INSTALLED",
    "manga_ocr": "NOT INSTALLED",
    "simple_lama_inpainting": "NOT INSTALLED",
    "googletrans": "NOT INSTALLED"
  },
  "trust_lifecycle": {
    "untrusted_rejected": true,
    "approval_succeeded": true,
    "tamper_detected": true,
    "revocation_clean": true
  },
  "opencv_detection": {
    "status": "PASS",
    "bubbles_found": 1,
    "sample_box": [147, 147, 654, 354]
  },
  "inpaint_imprint": {
    "status": "PASS",
    "inpaint_diff": 237132,
    "imprint_diff": 8613267,
    "output_path": "/home/akarta/Projects/zOther/CSS/scratch/validation_run/page_01_translated.png"
  },
  "project_save_load": {
    "status": "PASS"
  },
  "export": {
    "cbz": {
      "status": "PASS",
      "size": 27443
    },
    "pdf": {
      "status": "PASS",
      "size": 72794
    }
  },
  "batch_processing": {
    "status": "PASS",
    "live_ocr_available": false,
    "total": 2,
    "succeeded": 1,
    "failed": 1,
    "p2_outcome_status": "failed"
  }
}
```

### Visual Verification
- Source page: `scratch/validation_run/page_01.png` (800x1000, 7,611 bytes). Contains black panel border and white speech bubble with text `"TEST SCANLATION BUBBLE"`.
- Inpainted intermediate: Bubble interior cleared using OpenCV Telea fast marching algorithm.
- Imprinted result: `scratch/validation_run/page_01_translated.png`. Contains new rendered Polish text `"PRZETŁUMACZONY TEKST"` fitted into the bubble geometry.
- Exports: Validated CBZ archive (`export_output.cbz`) and multi-page PDF (`export_output.pdf`) created cleanly via Pillow fallback when `img2pdf` is absent.

---

## 6. Unit Test Execution Details

**Execution Command**:
```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest -v
```

**Results**:
- Collected: **85 items**
- Passed: **85 items**
- Failed: **0 items**
- Execution time: **1.13 seconds**

### Test Breakdown by Module
1. `tests/test_finding_10_wasm_plugins.py`: 1 passed
2. `tests/test_finding_11_metadata_coherence.py`: 2 passed
3. `tests/test_finding_1_pipeline_progress.py`: 2 passed
4. `tests/test_finding_2_batch_dialog.py`: 3 passed
5. `tests/test_finding_3_batch_completion.py`: 2 passed
6. `tests/test_finding_4_detector_model_and_opencv5.py`: 6 passed
7. `tests/test_finding_5_ocr_failures.py`: 3 passed
8. `tests/test_finding_6_translation_failures.py`: 5 passed
9. `tests/test_finding_7_directml.py`: 3 passed
10. `tests/test_finding_8_project_paths.py`: 4 passed
11. `tests/test_finding_9_translation_cache.py`: 2 passed
12. `tests/test_qt_smoke.py`: 1 passed
13. `tests/test_round2_item1_default_bootstrap_integrity.py`: 5 passed
14. `tests/test_round2_item2_directml_inference.py`: 4 passed
15. `tests/test_round2_item3_batch_outcomes.py`: 3 passed
16. `tests/test_round2_item4_ui_failure_surfacing.py`: 5 passed
17. `tests/test_round2_item5_multiprocess_cache_locking.py`: 4 passed
18. `tests/test_round3_fixes.py`: 21 passed
19. `tests/test_round4_trust.py` (New): 9 passed

---

## 7. Next Steps for Nick on his Windows Environment

When Nick runs the application on his own Windows PC:

1. **Install Full Neural Dependencies** (if desired):
   ```powershell
   .\venv\Scripts\activate
   pip install -r requirements.txt
   
   # For AMD or Intel GPU acceleration on Windows:
   pip install onnxruntime-directml
   
   # For NVIDIA GPU acceleration on Windows:
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
   ```

2. **First-Use Model Approval**:
   - Open **Settings > Manage AI Models**.
   - Under "Comic Bubble Detector", click **Download**.
   - Review the unpinned model warning dialog showing the HuggingFace URL and click **Yes** to approve.
   - The file will be downloaded, verified, and saved to `models/model_trust.json`.
   - On all future runs, the model will load instantly without any security prompts.

3. **100% Offline Alternative (Zero Downloads)**:
   - Nick can also choose to run completely offline without downloading any AI models by selecting **Detector: opencv** in **Settings**. The OpenCV 5 engine runs entirely locally on CPU with zero network calls and zero model downloads.
