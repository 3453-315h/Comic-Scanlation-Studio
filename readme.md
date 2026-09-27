<div align="center">
  <img src="assets/splash.png" alt="Comic Scanlation Studio Logo" width="600">
</div>

# Comic Scanlation Studio

A powerful, local-first AI tool for automating the scanlation process: Detection, OCR, Translation, Inpainting, and Typesetting.

**Version**: 1.1.1

## ✨ Features

### AI-Powered Pipeline
-   **Text Detection**: YOLOv8 specialized for comic speech bubbles, with OpenCV fallback
-   **OCR**: MangaOCR (Japanese) + RapidOCR (80+ languages including Polish)
-   **Translation**: DeepL, OpenAI, Google, NLLB/Opus (offline)
-   **Inpainting**: LaMa AI removes text with **Guaranteed Border Protection** (structural edge-wipe) and optional **Pure White Fill Mode**.
-   **Imprinting**: **Elliptical Text Rendering** with auto-fit, CJK support, custom fonts, and **Independent Font Styling** (size/family per bubble).

### GPU Acceleration
-   **NVIDIA**: CUDA support
-   **AMD/Intel**: DirectML support (Windows)
-   **Apple**: MPS support (M1/M2)

### Export Formats
-   **Images**: PNG, JPG, WebP with **Configurable Export Quality**
-   **Archives**: CBZ (comic archive)
-   **Documents**: PDF

### Batch Processing
-   Process entire chapters in parallel
-   Configurable worker threads (1-16)

## 🧠 AI Model Reference & Security

Comic Scanlation Studio uses specialized AI models for speech bubble detection, OCR, translation, and inpainting. To protect user security, model artifacts are governed by cryptographic verification and scoped trust records:

| Task | Default/Recommended Model | Source / Architecture | Size | Trust & Acquisition Route |
| :--- | :--- | :--- | :--- | :--- |
| **Detection** | `comic-speech-bubble-detector.pt` / `.onnx` | `ogkalu/comic-speech-bubble-detector-yolov8m` (HuggingFace) | ~52 MB (.pt) / ~100 MB (.onnx) | **Unpinned**: Requires explicit user approval in Settings before download/use |
| **Detection (Offline)** | `opencv-robust` | OpenCV 5.0.0.93 Contour Detection (Built-in) | 0 MB | **Built-in**: Fully offline, zero downloads, zero weights |
| **OCR (Multi)** | `RapidOCR` (Default) | PaddleOCR Latin V5 / ONNX Runtime | ~10 MB | Standard model repository |
| **OCR (JA)** | `manga-ocr` | kha-white Vision Transformer | ~444 MB | HuggingFace snapshot |
| **Inpainting** | `LaMa` | PyTorch Hub Big-LaMa | ~200 MB | Torch Hub checkpoint |
| **Translation** | `Google Translate` (Default) | Google Translation API | 0 MB | Cloud API (requires network) |
| **Translation (Offline)** | `OPUS-MT` | Helsinki-NLP Transformer | ~300 MB | HuggingFace snapshot (offline) |
| **Translation (Offline)** | `NLLB-200` | Meta NLLB-200 distilled 600M | ~2.3 GB | HuggingFace snapshot (high quality offline) |

### 🔒 Model Approval, Persistence & Trust Verification

1. **Initial Acquisition & Explicit Approval**:
   - The specialized comic speech bubble detector does **not** have an official publisher-pinned digest in the registry.
   - **Fresh "Process All" does NOT auto-download this unverified default without prompt.** If unapproved, processing fails closed with a clear error advising the user to acquire and approve the model via **Settings > Manage AI Models** or select the offline OpenCV engine.
   - To acquire the model: navigate to **Settings > Manage AI Models** (Download Models dialog) and click **Download** for "Comic Bubble Detector".
   - A security dialog will display the source URL (`https://huggingface.co/ogkalu/comic-speech-bubble-detector-yolov8m/resolve/main/comic-speech-bubble-detector.pt`) and request explicit user confirmation.
   - Once approved, the file is downloaded in chunks with bounded timeouts, verified against stubs and size, and its cryptographic SHA-256 digest is persisted locally in `models/model_trust.json`.

2. **Reuse Across Restarts & ONNX Provenance**:
   - On every load, export, or subsequent session, the file's SHA-256 digest is re-checked against `models/model_trust.json`. If unchanged, the model loads immediately without prompting.
   - If converted to ONNX (`comic-speech-bubble-detector.onnx`), the local export links to the approved parent `.pt` hash and is recorded in `model_trust.json`.
   - If the file is replaced, altered, or corrupt, the application fails closed and refuses to execute unverified weights.

3. **Revoking Trust**:
   - You can revoke approval at any time by opening **Settings > Manage AI Models** and clicking **Revoke Model Trust**.
   - Alternatively, delete `models/model_trust.json` or call `src.core.security.revoke_approved_model()`.
   - Revoking trust for the base `.pt` automatically cascades to revoke derived `.onnx` models.

4. **100% Offline Alternative**:
   - In **Settings**, set **Detector** to `opencv` (`TextDetector("opencv-robust")`).
   - The built-in OpenCV 5 contour detector runs completely offline, requires no downloads or external dependencies, and preserves full comic processing capability without external models.

### ⚡ Hardware & GPU Acceleration

- **CPU**: Default execution provider. Always supported and stable across all platforms.
- **NVIDIA GPU (CUDA)**: Requires NVIDIA drivers, CUDA toolkit, and PyTorch CUDA build (`pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118`).
- **AMD / Intel / NVIDIA GPU (DirectML on Windows)**: Supported via `onnxruntime-directml` on Windows with DirectX 12 compatible GPUs.
- *Notice*: The application never mislabels a CPU run as DirectML or GPU. If DirectML is explicitly requested but `DmlExecutionProvider` is not available, the application raises a clear diagnostic error rather than silently masking execution as GPU.

## 🚀 Installation

### Option 1: Standalone Executable (Recommended)
Download `Comic Scanlation Studio.exe` from Releases. No installation required.

### Option 2: From Source
```bash
# Clone and setup
git clone https://github.com/3453-315h/Comic-Scanlation-Studio.git
cd Comic-Scanlation-Studio
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# For NVIDIA GPU (optional)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# For AMD/Intel GPU (optional, Windows)
pip install onnxruntime-directml
```

## 🎮 Usage

### Quick Start
1. Run `run.bat` or `python -m src.main`
2. **File > New Project** to create a project
3. Drag & drop manga pages
4. Click **Process All** to run the full pipeline
5. Edit results in the Page Editor
6. Export via **File > Export**

### Settings
-   **AI Device**: Auto / CPU / CUDA / MPS / DirectML
-   **Batch Processing**: Enable parallel mode for faster processing
-   **Models**: Download/manage AI models from Settings

## 📁 Directory Structure
```
├── assets/fonts/     # Custom fonts (.ttf/.otf)
├── models/           # AI models (auto-downloaded)
├── projects/         # Saved projects
└── config.json       # User settings
```

## 📜 License
All rights reserved. License terms to be confirmed by repository owner.
