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

## 🚀 Installation

### Option 1: Standalone Executable (Recommended)
Download `Comic Scanlation Studio.exe` from Releases. No installation required.

### Option 2: From Source
```bash
# Clone and setup
git clone https://github.com/your-repo/scanlation-tool.git
cd scanlation-tool
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
1. Run `Comic Scanlation Studio.exe` or `run.bat`
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

## 🛠️ Build from Source
```bash
# Build executable
.\build.bat
# Output: dist/Comic Scanlation Studio/
```

## 📜 License
[MIT License](LICENSE)
