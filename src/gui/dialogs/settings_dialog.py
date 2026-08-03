"""
Settings Dialog - Comic Translation Studio

Provides UI for configuring:
- Detection settings (OpenCV vs YOLO)
- Translation backend (DeepL, Google, OpenAI, NLLB, OPUS)
- Language settings
"""

import os

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


class SettingsDialog(QDialog):
    """Application settings dialog"""

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Settings")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        self.init_ui()
        self.load_settings()

    def init_ui(self):
        """Initialize the dialog UI"""
        layout = QVBoxLayout(self)

        # Tab widget for different setting categories
        tabs = QTabWidget()

        # Detection tab
        tabs.addTab(self.create_detection_tab(), "Detection")

        # Translation tab
        tabs.addTab(self.create_translation_tab(), "Translation")

        # OCR tab
        tabs.addTab(self.create_ocr_tab(), "OCR")

        # General tab
        tabs.addTab(self.create_general_tab(), "General")

        layout.addWidget(tabs)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_settings)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def create_detection_tab(self) -> QWidget:
        """Create detection settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Detector selection
        detector_group = QGroupBox("Text Detector")
        detector_layout = QFormLayout(detector_group)

        self.detector_combo = QComboBox()
        self.detector_combo.addItems(["opencv", "yolo", "yolo-onnx"])
        self.detector_combo.currentTextChanged.connect(self.on_detector_changed)
        self.detector_combo.setToolTip("Select the method for finding speech bubbles.\n"
                                     " - YOLO: Best accuracy, uses AI model (PyTorch).\n"
                                     " - YOLO-ONNX: Faster inference, exports model to ONNX.\n"
                                     " - OpenCV: Classic algorithm, faster but less accurate.")
        detector_layout.addRow("Detector:", self.detector_combo)

        layout.addWidget(detector_group)

        # YOLO settings
        self.yolo_group = QGroupBox("YOLO Settings")
        yolo_layout = QFormLayout(self.yolo_group)

        self.yolo_model_combo = QComboBox()
        self.yolo_model_combo.addItems([
            "comic-speech-bubble-detector.pt (Specialized - Recommended)",
            "yolov8n.pt (Nano - Fast)",
            "yolov8s.pt (Small)",
            "yolov8m.pt (Medium)",
            "yolov8l.pt (Large - Accurate)",
            "Custom model..."
        ])
        self.yolo_model_combo.setToolTip("Select the AI model variant.\n"
                                       "Specialized models work best on comics.\n"
                                       "Larger models (L) are more accurate but slower.")
        yolo_layout.addRow("Model:", self.yolo_model_combo)

        self.yolo_confidence = QDoubleSpinBox()
        self.yolo_confidence.setRange(0.05, 0.95)
        self.yolo_confidence.setSingleStep(0.05)
        self.yolo_confidence.setValue(0.25)
        self.yolo_confidence.setToolTip("Minimum confidence (0-1) to accept a detection.\n"
                                      "Lower: Finds more bubbles but maybe some false positives.\n"
                                      "Higher: Stricter, might miss faint bubbles.")
        yolo_layout.addRow("Confidence Threshold:", self.yolo_confidence)

        layout.addWidget(self.yolo_group)

        # OpenCV settings
        self.opencv_group = QGroupBox("OpenCV Settings")
        opencv_layout = QFormLayout(self.opencv_group)

        self.min_area = QSpinBox()
        self.min_area.setRange(100, 5000)
        self.min_area.setValue(500)
        self.min_area.setToolTip("Minimum size (pixels) for a region to be considered a bubble.\n"
                               "Increase to filter out small noise.")
        opencv_layout.addRow("Min Bubble Area (px):", self.min_area)

        self.ignore_sfx = QCheckBox("Ignore small regions (SFX)")
        self.ignore_sfx.setChecked(True)
        self.ignore_sfx.setToolTip("Attempt to filter out small text or sound effects that aren't full speech bubbles.")
        opencv_layout.addRow("", self.ignore_sfx)

        layout.addWidget(self.opencv_group)

        layout.addStretch()
        return widget

    def create_translation_tab(self) -> QWidget:
        """Create translation settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Translation API
        api_group = QGroupBox("Translation Backend")
        api_layout = QFormLayout(api_group)

        self.translation_combo = QComboBox()
        self.translation_combo.addItems([
            "deepl",
            "google",
            "openai",
            "nllb (Offline - High Quality)",
            "opus (Offline - Fast)"
        ])
        self.translation_combo.currentTextChanged.connect(self.on_translation_changed)
        self.translation_combo.setToolTip("Select the translation engine:\n"
                                        " - DeepL/OpenAI: High quality, requires API key.\n"
                                        " - Google: Free (limited), good quality.\n"
                                        " - NLLB/OPUS: Run locally on your PC (offline).")
        api_layout.addRow("Backend:", self.translation_combo)

        layout.addWidget(api_group)

        # Language settings
        lang_group = QGroupBox("Languages")
        lang_layout = QFormLayout(lang_group)

        # Language codes with full names
        LANGUAGES = [
            ("ja", "Japanese"),
            ("ko", "Korean"),
            ("zh-cn", "Chinese (Simplified)"),
            ("zh-tw", "Chinese (Traditional)"),
            ("en", "English"),
            ("fr", "French"),
            ("de", "German"),
            ("es", "Spanish"),
            ("it", "Italian"),
            ("pt", "Portuguese"),
            ("nl", "Dutch"),
            ("pl", "Polish"),
            ("ru", "Russian"),
            ("uk", "Ukrainian"),
            ("cs", "Czech"),
            ("ro", "Romanian"),
            ("hu", "Hungarian"),
            ("sv", "Swedish"),
            ("da", "Danish"),
            ("no", "Norwegian"),
            ("fi", "Finnish"),
            ("el", "Greek"),
            ("tr", "Turkish"),
            ("ar", "Arabic"),
            ("th", "Thai"),
            ("vi", "Vietnamese"),
            ("id", "Indonesian"),
        ]

        self.source_lang = QComboBox()
        for code, name in LANGUAGES:
            self.source_lang.addItem(f"{code} - {name}", code)
        self.source_lang.setToolTip("Original language of the comic.")
        lang_layout.addRow("Source Language:", self.source_lang)

        self.target_lang = QComboBox()
        for code, name in LANGUAGES:
            self.target_lang.addItem(f"{code} - {name}", code)
        self.target_lang.setToolTip("Language to translate into.")
        lang_layout.addRow("Target Language:", self.target_lang)

        layout.addWidget(lang_group)

        # API Keys
        self.api_key_group = QGroupBox("API Keys")
        api_key_layout = QFormLayout(self.api_key_group)

        self.deepl_key = QLineEdit()
        self.deepl_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.deepl_key.setPlaceholderText("Enter DeepL API key...")
        self.deepl_key.setToolTip("Your DeepL authentication key.")
        api_key_layout.addRow("DeepL API Key:", self.deepl_key)

        self.openai_key = QLineEdit()
        self.openai_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.openai_key.setPlaceholderText("Enter OpenAI API key...")
        self.openai_key.setToolTip("Your OpenAI API key (for GPT translation).")
        api_key_layout.addRow("OpenAI API Key:", self.openai_key)

        layout.addWidget(self.api_key_group)

        # Offline model info
        self.offline_info = QGroupBox("Offline Translation Info")
        offline_layout = QVBoxLayout(self.offline_info)
        info_label = QLabel(
            "NLLB (High Quality): Downloads ~2.3GB model on first use\n"
            "OPUS (Fast): Downloads ~300MB model on first use\n\n"
            "Models are cached locally after download."
        )
        info_label.setWordWrap(True)
        offline_layout.addWidget(info_label)
        self.offline_info.setVisible(False)

        layout.addWidget(self.offline_info)

        layout.addStretch()
        return widget

    def create_ocr_tab(self) -> QWidget:
        """Create OCR settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        ocr_group = QGroupBox("OCR Engine")
        ocr_layout = QFormLayout(ocr_group)

        self.ocr_combo = QComboBox()
        self.ocr_combo.addItems([
            "manga_ocr (Japanese/Asian - Recommended)",
            "RapidOCR (PaddleOCR - High Quality)"
        ])
        self.ocr_combo.currentTextChanged.connect(self.on_ocr_changed)
        self.ocr_combo.setToolTip("OCR Engine Selection:\n"
                                " - manga_ocr: Best for Japanese/Vertical text.\n"
                                " - RapidOCR: Best for English/European/Horizontal text (supports Polish).")
        ocr_layout.addRow("OCR Model:", self.ocr_combo)

        self.ocr_info = QLabel(
            "MangaOCR is specialized for Japanese manga text.\n"
            "Model downloads (~444MB) on first use."
        )
        self.ocr_info.setWordWrap(True)
        ocr_layout.addRow("", self.ocr_info)

        layout.addWidget(ocr_group)

        # Advanced OCR Settings
        adv_ocr_group = QGroupBox("Advanced OCR Settings")
        adv_ocr_layout = QFormLayout(adv_ocr_group)

        self.ocr_confidence = QDoubleSpinBox()
        self.ocr_confidence.setRange(0.0, 1.0)
        self.ocr_confidence.setSingleStep(0.05)
        self.ocr_confidence.setValue(getattr(self.config, 'OCR_CONFIDENCE_THRESHOLD', 0.0))
        self.ocr_confidence.setToolTip("Minimum confidence score to accept text.\nSet to 0.0 to accept everything (recommended for manga with handwritten fonts).")
        adv_ocr_layout.addRow("Confidence Threshold:", self.ocr_confidence)

        self.ocr_padding = QSpinBox()
        self.ocr_padding.setRange(0, 100)
        self.ocr_padding.setSingleStep(5)
        self.ocr_padding.setSuffix(" px")
        self.ocr_padding.setValue(getattr(self.config, 'OCR_PADDING', 20))
        self.ocr_padding.setToolTip("Pixels to expand the detected text box before OCR.\n"
                                    "Increase if text is being cut off at the edges.")
        adv_ocr_layout.addRow("OCR Padding:", self.ocr_padding)

        layout.addWidget(adv_ocr_group)

        # Inpainting settings
        inpaint_group = QGroupBox("Inpainting")
        inpaint_layout = QFormLayout(inpaint_group)

        self.inpaint_combo = QComboBox()
        self.inpaint_combo.addItems([
            "LaMa (AI - Best Quality)",
            "Telea (OpenCV - Fast/Stable)",
            "Navier-Stokes (OpenCV - Smoother)"
        ])
        self.inpaint_combo.setToolTip("Inpainting Method:\n"
                                    " - LaMa: High quality AI, but requires more resources.\n"
                                    " - Telea/NS: Fast, reliable, no download needed.")
        inpaint_layout.addRow("Inpaint Method:", self.inpaint_combo)

        layout.addWidget(inpaint_group)

        # Advanced Inpainting Settings
        adv_inpaint_group = QGroupBox("Advanced Inpainting Settings")
        adv_layout = QFormLayout(adv_inpaint_group)

        self.mask_dilation = QSpinBox()
        self.mask_dilation.setRange(1, 20)
        self.mask_dilation.setValue(5)
        self.mask_dilation.setToolTip("Pixels to expand the text mask by before inpainting.\n"
                                    "Increase if bits of text letters remain visible.\n"
                                    "Decrease if too much background is being erased.")
        adv_layout.addRow("Mask Dilation (Strength):", self.mask_dilation)

        self.protect_borders = QCheckBox("Protect Speech Bubble Borders")
        self.protect_borders.setChecked(True)
        self.protect_borders.setToolTip("Prevent inpainting from erasing speech bubble outlines.\n"
                                      "Uncheck if borders are being detected as text.")
        adv_layout.addRow("", self.protect_borders)

        self.guided_mode = QCheckBox("Guided Inpainting (Reduce Ghosting)")
        self.guided_mode.setChecked(True)
        self.guided_mode.setToolTip("Expand mask toward text-colored pixels.\n"
                                   "Helps catch anti-aliased text edges and reduces ghosting artifacts.")
        adv_layout.addRow("", self.guided_mode)

        self.mask_blur = QSpinBox()
        self.mask_blur.setRange(0, 15)
        self.mask_blur.setSingleStep(2)
        self.mask_blur.setValue(5)
        self.mask_blur.setToolTip("Gaussian blur applied to mask edges (0 = disabled).\n"
                                 "Helps create smoother transitions and reduces hard edges.\n"
                                 "Use odd values (3, 5, 7...) for best results.")
        adv_layout.addRow("Mask Edge Blur:", self.mask_blur)

        self.whiten_mode = QCheckBox("Pure White Background Fill (LaMa Mode)")
        self.whiten_mode.setChecked(False)
        self.whiten_mode.setToolTip("Force the inpainted area to be pure white instead of guessing the background.\n"
                                   "Useful for standard manga with clean white speech bubbles.")
        adv_layout.addRow("", self.whiten_mode)

        layout.addWidget(adv_inpaint_group)

        layout.addStretch()
        return widget

    def create_general_tab(self) -> QWidget:
        """Create general settings tab (Imprinting)"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Display / Export
        display_group = QGroupBox("Display & Export")
        display_layout = QFormLayout(display_group)

        self.max_image_size = QSpinBox()
        self.max_image_size.setRange(1024, 8192)
        self.max_image_size.setSingleStep(512)
        self.max_image_size.setValue(4096)
        self.max_image_size.setToolTip("Maximum dimension for processing/display.\nLarge images are resized to fit this limit.")
        display_layout.addRow("Max Image Size:", self.max_image_size)

        self.export_quality = QSpinBox()
        self.export_quality.setRange(0, 100)
        self.export_quality.setValue(90)
        self.export_quality.setToolTip("Image quality (0-100) used when exporting to JPEG or WebP formats.\nHigher values look better but increase file size.")
        display_layout.addRow("Export JPG/WebP Quality:", self.export_quality)

        layout.addWidget(display_group)

        # AI / Hardware
        ai_group = QGroupBox("AI Acceleration")
        ai_layout = QFormLayout(ai_group)

        self.ai_device = QComboBox()
        self.ai_device.addItems(["auto", "cpu", "cuda", "mps", "directml"])
        self.ai_device.setToolTip("Hardware device for AI models (YOLO, MangaOCR, etc.).\n"
                                " - Auto: Detects best available (CUDA > MPS > CPU).\n"
                                " - CUDA: NVIDIA GPU.\n"
                                " - MPS: Mac M1/M2 GPU.\n"
                                " - DirectML: AMD/Intel GPU (Windows).\n"
                                " - CPU: Force processor only.")
        ai_layout.addRow("Inference Device:", self.ai_device)

        layout.addWidget(ai_group)

        # Batch Processing
        batch_group = QGroupBox("Batch Processing")
        batch_layout = QFormLayout(batch_group)

        self.batch_parallel = QCheckBox("Enable Parallel Processing")
        self.batch_parallel.setToolTip("Process multiple pages at once.\n"
                                     "Faster, but uses more CPU/RAM.")
        batch_layout.addRow("", self.batch_parallel)

        self.batch_workers = QSpinBox()
        self.batch_workers.setRange(1, 16)
        self.batch_workers.setValue(2)
        self.batch_workers.setToolTip("Number of concurrent pages to process.\n"
                                    "Recommended: 2-4 for most systems.")
        batch_layout.addRow("Max Workers:", self.batch_workers)

        # Connect signal
        self.batch_parallel.toggled.connect(self.batch_workers.setEnabled)

        layout.addWidget(batch_group)

        # Model Management
        model_btn = QPushButton("Manage AI Models (Download/Remove)")
        model_btn.clicked.connect(self.open_model_manager)
        layout.addWidget(model_btn)

        # Imprinting Settings
        imprint_group = QGroupBox("Text Imprinting & Styling")
        imprint_layout = QFormLayout(imprint_group)

        self.enable_imprint = QCheckBox("Enable Automatic Imprinting")
        self.enable_imprint.setToolTip("Automatically place translated text onto the image after inpainting.")
        imprint_layout.addRow("", self.enable_imprint)

        self.auto_style = QCheckBox("Auto-Detect Text Styles")
        self.auto_style.setToolTip("Attempt to match original font colors and styles automatically.")
        imprint_layout.addRow("", self.auto_style)

        self.default_font = QComboBox()
        self.default_font.addItems(["Arial", "Comic Sans MS", "Manga Temple", "Wild Words"])
        self.default_font.setToolTip("Font used for rendering translated text.")
        imprint_layout.addRow("Default Font:", self.default_font)

        self.default_font_size = QSpinBox()
        self.default_font_size.setRange(8, 72)
        self.default_font_size.setValue(24)
        self.default_font_size.setToolTip("Default font size (in pixels) for text if auto-sizing is disabled or fails.")
        imprint_layout.addRow("Default Font Size:", self.default_font_size)

        self.imprint_padding = QSpinBox()
        self.imprint_padding.setRange(0, 50)
        self.imprint_padding.setValue(5)
        self.imprint_padding.setToolTip("White space padding inside the speech bubble (pixels).\nPrevents text from touching bubble edges.")
        imprint_layout.addRow("Text Padding:", self.imprint_padding)

        self.line_spacing = QDoubleSpinBox()
        self.line_spacing.setRange(0.8, 3.0)
        self.line_spacing.setSingleStep(0.1)
        self.line_spacing.setValue(1.2)
        self.line_spacing.setToolTip("Vertical spacing between lines of text (1.0 = standard).")
        imprint_layout.addRow("Line Spacing:", self.line_spacing)

        self.box_expansion = QSpinBox()
        self.box_expansion.setRange(-20, 50)
        self.box_expansion.setValue(0)
        self.box_expansion.setToolTip("Expand detected bubble box by N pixels.\n"
                                    " - Positive: Makes bubble larger.\n"
                                    " - Negative: Shrinks bubble area.\n"
                                    "Useful if detection is too tight cutting off text.")
        imprint_layout.addRow("Bubble Box Expansion:", self.box_expansion)

        self.shape_wrapping = QCheckBox("Shape-Aware Wrapping (Elliptical)")
        self.shape_wrapping.setToolTip("Try to fit text into an elliptical shape instead of a rectangle.\n"
                                     "Best for standard comic speech bubbles.")
        imprint_layout.addRow("", self.shape_wrapping)

        layout.addWidget(imprint_group)

        layout.addStretch()
        return widget

    def on_detector_changed(self, detector: str):
        """Toggle YOLO/OpenCV settings visibility"""
        is_yolo = "yolo" in detector
        self.yolo_group.setEnabled(is_yolo)
        self.opencv_group.setEnabled(not is_yolo)

    def on_translation_changed(self, backend: str):
        """Toggle API key / offline info visibility"""
        is_offline = "nllb" in backend or "opus" in backend
        self.api_key_group.setVisible(not is_offline)
        self.offline_info.setVisible(is_offline)

    def on_ocr_changed(self, ocr: str):
        """Update OCR info text based on selection"""
        if "RapidOCR" in ocr:
            self.ocr_info.setText(
                "RapidOCR (based on PaddleOCR) offers high-accuracy commercial-grade recognition.\n"
                "Supports 80+ languages including vertical text."
            )
        else:
            self.ocr_info.setText(
                "MangaOCR is specialized for Japanese manga text.\n"
                "Model downloads (~444MB) on first use."
            )

    def open_model_manager(self):
        """Open the model download dialog"""
        from .download_models_dialog import DownloadModelsDialog
        dialog = DownloadModelsDialog(self)
        dialog.exec()

    def load_settings(self):
        """Load current settings into UI"""
        # Detector
        detector = getattr(self.config, 'DETECTOR_MODEL', 'opencv')
        idx = self.detector_combo.findText(detector)
        if idx >= 0:
            self.detector_combo.setCurrentIndex(idx)

        # YOLO settings
        self.yolo_confidence.setValue(getattr(self.config, 'YOLO_CONFIDENCE', 0.25))

        # Restore YOLO model selection
        yolo_model = getattr(self.config, 'YOLO_MODEL_PATH', 'comic-speech-bubble-detector.pt')
        for i in range(self.yolo_model_combo.count()):
            if self.yolo_model_combo.itemText(i).startswith(yolo_model.replace('.pt', '')):
                self.yolo_model_combo.setCurrentIndex(i)
                break

        # Translation
        translation_api = getattr(self.config, 'TRANSLATION_API', 'deepl')
        for i in range(self.translation_combo.count()):
            if self.translation_combo.itemText(i).startswith(translation_api):
                self.translation_combo.setCurrentIndex(i)
                break

        # Languages - use findData since we store code as item data
        src_lang = getattr(self.config, 'DEFAULT_SOURCE_LANG', 'ja')
        idx = self.source_lang.findData(src_lang)
        if idx >= 0:
            self.source_lang.setCurrentIndex(idx)

        tgt_lang = getattr(self.config, 'DEFAULT_TARGET_LANG', 'en')
        idx = self.target_lang.findData(tgt_lang)
        if idx >= 0:
            self.target_lang.setCurrentIndex(idx)

        # API Keys from env
        self.deepl_key.setText(os.getenv('DEEPL_API_KEY', ''))
        self.openai_key.setText(os.getenv('OPENAI_API_KEY', ''))

        # OCR model and confidence
        ocr_model = getattr(self.config, 'OCR_MODEL', 'manga_ocr')
        search_term = "RapidOCR" if ocr_model == "easyocr" else ocr_model

        for i in range(self.ocr_combo.count()):
            if self.ocr_combo.itemText(i).startswith(search_term):
                self.ocr_combo.setCurrentIndex(i)
                break

        self.ocr_confidence.setValue(getattr(self.config, 'OCR_CONFIDENCE_THRESHOLD', 0.0))
        self.ocr_padding.setValue(getattr(self.config, 'OCR_PADDING', 20))

        # General / Imprinting
        self.max_image_size.setValue(getattr(self.config, 'MAX_IMAGE_SIZE', 4096))
        self.export_quality.setValue(getattr(self.config, 'EXPORT_IMAGE_QUALITY', 90))

        ai_device = getattr(self.config, 'AI_DEVICE', 'auto')
        idx = self.ai_device.findText(ai_device)
        if idx >= 0:
            self.ai_device.setCurrentIndex(idx)

        self.enable_imprint.setChecked(getattr(self.config, 'ENABLE_IMPRINT', True))
        self.auto_style.setChecked(getattr(self.config, 'AUTO_STYLE', True))

        default_font = getattr(self.config, 'DEFAULT_FONT', 'Arial')
        idx = self.default_font.findText(default_font)
        if idx >= 0:
            self.default_font.setCurrentIndex(idx)

        self.default_font_size.setValue(getattr(self.config, 'DEFAULT_FONT_SIZE', 24))
        self.imprint_padding.setValue(getattr(self.config, 'IMPRINT_PADDING', 5))
        self.line_spacing.setValue(getattr(self.config, 'IMPRINT_LINE_SPACING', 1.2))
        self.box_expansion.setValue(getattr(self.config, 'IMPRINT_BOX_EXPANSION', 0))
        self.shape_wrapping.setChecked(getattr(self.config, 'IMPRINT_SHAPE_WRAPPING', False))

        # Batch
        self.batch_parallel.setChecked(getattr(self.config, 'BATCH_PARALLEL_ENABLED', False))
        self.batch_workers.setValue(getattr(self.config, 'BATCH_MAX_WORKERS', 2))
        self.batch_workers.setEnabled(self.batch_parallel.isChecked())

        # Inpainting
        self.mask_dilation.setValue(getattr(self.config, 'INPAINT_MASK_DILATION', 5))
        self.protect_borders.setChecked(getattr(self.config, 'INPAINT_PROTECT_BORDERS', True))
        self.guided_mode.setChecked(getattr(self.config, 'INPAINT_GUIDED_MODE', True))
        self.mask_blur.setValue(getattr(self.config, 'INPAINT_MASK_BLUR', 5))
        self.whiten_mode.setChecked(getattr(self.config, 'INPAINT_WHITEN_MODE', False))

        # Trigger visibility updates
        self.on_detector_changed(self.detector_combo.currentText())
        self.on_translation_changed(self.translation_combo.currentText())
        self.on_ocr_changed(self.ocr_combo.currentText())

    def save_settings(self):
        """Save settings and close dialog"""
        # Update config object
        self.config.DETECTOR_MODEL = self.detector_combo.currentText()
        self.config.YOLO_CONFIDENCE = self.yolo_confidence.value()

        # Save YOLO model path (extract just the model file name)
        yolo_model_text = self.yolo_model_combo.currentText()
        # Extract "yolov8l.pt" from "yolov8l.pt (Large - Accurate)"
        if yolo_model_text.startswith("Custom"):
            # Custom model - keep current path or prompt for file
            pass
        else:
            model_file = yolo_model_text.split()[0]  # Get "yolov8l.pt"
            self.config.YOLO_MODEL_PATH = model_file

        # Parse translation backend
        translation_text = self.translation_combo.currentText()
        if "nllb" in translation_text:
            self.config.TRANSLATION_API = "nllb"
        elif "opus" in translation_text:
            self.config.TRANSLATION_API = "opus"
        else:
            self.config.TRANSLATION_API = translation_text

        self.config.DEFAULT_SOURCE_LANG = self.source_lang.currentData()
        self.config.DEFAULT_TARGET_LANG = self.target_lang.currentData()
        self.config.MAX_IMAGE_SIZE = self.max_image_size.value()
        self.config.EXPORT_IMAGE_QUALITY = self.export_quality.value()

        ocr_text = self.ocr_combo.currentText()
        if "RapidOCR" in ocr_text:
            self.config.OCR_MODEL = "easyocr"
        else:
            self.config.OCR_MODEL = "manga_ocr"

        self.config.OCR_CONFIDENCE_THRESHOLD = self.ocr_confidence.value()
        self.config.OCR_PADDING = self.ocr_padding.value()

        # Inpainting Settings
        # Extract model key from combo text
        inpaint_text = self.inpaint_combo.currentText()
        if "LaMa" in inpaint_text:
            self.config.INPAINTER_MODEL = "lama"
        elif "Telea" in inpaint_text:
            self.config.INPAINTER_MODEL = "telea"
        elif "Navier-Stokes" in inpaint_text:
            self.config.INPAINTER_MODEL = "ns"

        self.config.INPAINT_MASK_DILATION = self.mask_dilation.value()
        self.config.INPAINT_PROTECT_BORDERS = self.protect_borders.isChecked()
        self.config.INPAINT_GUIDED_MODE = self.guided_mode.isChecked()
        self.config.INPAINT_MASK_BLUR = self.mask_blur.value()
        self.config.INPAINT_WHITEN_MODE = self.whiten_mode.isChecked()

        # AI Device
        self.config.AI_DEVICE = self.ai_device.currentText()

        # Imprinting
        self.config.ENABLE_IMPRINT = self.enable_imprint.isChecked()
        self.config.AUTO_STYLE = self.auto_style.isChecked()
        self.config.DEFAULT_FONT = self.default_font.currentText()
        self.config.DEFAULT_FONT_SIZE = self.default_font_size.value()
        self.config.IMPRINT_PADDING = self.imprint_padding.value()
        self.config.IMPRINT_LINE_SPACING = self.line_spacing.value()
        self.config.IMPRINT_BOX_EXPANSION = self.box_expansion.value()
        self.config.IMPRINT_SHAPE_WRAPPING = self.shape_wrapping.isChecked()

        # Batch
        self.config.BATCH_PARALLEL_ENABLED = self.batch_parallel.isChecked()
        self.config.BATCH_MAX_WORKERS = self.batch_workers.value()

        # Persist config to file
        self.config.save()

        # Set API keys as env vars for current session
        if self.deepl_key.text():
            os.environ['DEEPL_API_KEY'] = self.deepl_key.text()
        if self.openai_key.text():
            os.environ['OPENAI_API_KEY'] = self.openai_key.text()

        QMessageBox.information(
            self,
            "Settings Saved",
            "Settings have been saved for this session.\n"
            "Note: API keys are stored in environment only."
        )

        self.accept()
