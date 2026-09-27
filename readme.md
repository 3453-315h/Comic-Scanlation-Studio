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

## 🧠 AI Model Reference

The tool uses several specialized AI models. Verified models can be acquired automatically or managed via **Settings > Manage AI Models**. Unverified model weights require explicit user confirmation before download and execution.

| Task | Default/Recommended Model | Source | Size |
| :--- | :--- | :--- | :--- |
| **Detection** | `comic-speech-bubble-detector.onnx` | YOLO-ONNX (Specialized) | ~100 MB |
| **OCR (JA)** | `manga-ocr` | kha-white (Transformer) | ~444 MB |
| **OCR (Multi)** | `RapidOCR` (Default) | PaddleOCR (ONNX) | ~10 MB |
| **Inpainting** | `LaMa` | AI Masked Inpainting | ~200 MB |
| **Translation** | `Google Translate` (Default) | Google API | N/A |
| **Translation** | `NLLB-200` | Meta (High Quality Offline) | ~2.3 GB |
| **Translation** | `OPUS-MT` | Helsinki-NLP (Fast Offline) | ~300 MB |

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

# For AMD/Intel GPU (optional)
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
