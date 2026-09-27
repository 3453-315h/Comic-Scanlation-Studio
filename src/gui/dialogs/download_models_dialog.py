"""
Download Models Dialog - Comic Translation Studio

Shows available models with their locations and sizes.
Provides download buttons for each model.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget,
    QLabel, QPushButton, QGroupBox, QFormLayout,
    QProgressBar, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QApplication
)
from PySide6.QtCore import Qt, QThread, Signal
from pathlib import Path
import os
import logging

logger = logging.getLogger(__name__)


class DownloadThread(QThread):
    """Background thread for downloading models"""
    progress = Signal(str)  # Status message
    finished_download = Signal(bool, str)  # success, message
    
    def __init__(self, model_name: str, model_type: str, allow_unverified: bool = False):
        super().__init__()
        self.model_name = model_name
        self.model_type = model_type
        self.allow_unverified = allow_unverified
    
    def run(self):
        try:
            if self.model_type == "OCR":
                self._download_ocr_model()
            elif self.model_type == "Detection":
                self._download_yolo_model()
            elif self.model_type == "Translation":
                self._download_translation_model()
            elif self.model_type == "Inpainting":
                self._download_inpaint_model()
            
            self.finished_download.emit(True, f"{self.model_name} downloaded successfully!")
        except Exception as e:
            self.finished_download.emit(False, f"Download failed: {e}")
    
    def _download_ocr_model(self):
        from ...core.config import Config
        
        if "MangaOCR" in self.model_name:
            self.progress.emit("Downloading MangaOCR model...")
            # Ensure proper cache dir for MangaOCR
            import os
            os.environ["HF_HOME"] = str(Config.MODELS_DIR / "huggingface")
            from manga_ocr import MangaOcr
            # This will trigger the download (to HF cache)
            MangaOcr()
        elif "RapidOCR" in self.model_name:
            self.progress.emit("Downloading RapidOCR model...")
            model_dir = Config.MODELS_DIR / "rapidocr"
            model_dir.mkdir(parents=True, exist_ok=True)
            
            # Download Latin V5 Model (using standard PP-OCRv4 as base + custom keys)
            files = {
                "latin_PP-OCRv5_rec_infer.onnx": "https://huggingface.co/SWHL/RapidOCR/resolve/main/PP-OCRv4/ch_PP-OCRv4_rec_infer.onnx", 
                "latin_v5_dict.txt": "https://raw.githubusercontent.com/PaddlePaddle/PaddleOCR/release/2.7/ppocr/utils/ppocr_keys_v1.txt"
            }
            
            import requests
            for filename, url in files.items():
                self.progress.emit(f"Downloading {filename}...")
                response = requests.get(url, stream=True)
                response.raise_for_status()
                with open(model_dir / filename, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
    
    def _download_yolo_model(self):
        from ...core.config import Config
        yolo_dir = Config.MODELS_DIR / "yolo"
        yolo_dir.mkdir(parents=True, exist_ok=True)

        if "Comic Bubble Detector" in self.model_name:
            model_file = "comic-speech-bubble-detector.pt"
            self.progress.emit(f"Acquiring {model_file}...")
            
            from ...modules.detector import acquire_detector_model
            dest_path = acquire_detector_model(
                model_name=model_file,
                target_dir=yolo_dir,
                timeout=60,
                allow_unverified=self.allow_unverified,
            )
            
            # Verify load with YOLO
            from ultralytics import YOLO
            YOLO(str(dest_path))
            
        else:
            # Standard YOLO models
            model_file = self.model_name.lower().replace("v", "v") + ".pt"
            self.progress.emit(f"Downloading {model_file}...")
            
            from ultralytics import YOLO
            # Download model (YOLO auto-downloads from ultralytics hub)
            model = YOLO(model_file)
            
            # Move to our folder if needed
            default_path = Path(model_file)
            if default_path.exists():
                import shutil
                dest = yolo_dir / model_file
                shutil.move(str(default_path), str(dest))
    
    def _download_translation_model(self):
        if "NLLB" in self.model_name:
            self.progress.emit("Downloading NLLB-200 model (2.3GB)...")
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
            model_name = "facebook/nllb-200-distilled-600M"
            AutoTokenizer.from_pretrained(model_name)
            AutoModelForSeq2SeqLM.from_pretrained(model_name)
        elif "OPUS" in self.model_name:
            self.progress.emit("Downloading OPUS-MT model...")
            from transformers import MarianMTModel, MarianTokenizer
            model_name = "Helsinki-NLP/opus-mt-ja-en"
            MarianTokenizer.from_pretrained(model_name)
            MarianMTModel.from_pretrained(model_name)
    
    def _download_inpaint_model(self):
        if "LaMa" in self.model_name:
            self.progress.emit("Downloading LaMa inpainting model (~200MB)...")
            from simple_lama_inpainting import SimpleLama
            # This triggers the model download
            SimpleLama()


class DownloadModelsDialog(QDialog):
    """Dialog for managing model downloads"""
    
    MODELS = [
        {
            "name": "MangaOCR",
            "description": "Japanese manga OCR (kha-white/manga-ocr-base)",
            "size": "~444 MB",
            "location": "./models/huggingface/models--kha-white--manga-ocr-base",
            "type": "OCR",
            "auto_download": True,
            # Must have snapshots/ with actual model data inside
            "check_path": "./models/huggingface/models--kha-white--manga-ocr-base/snapshots",
        },
        {
            "name": "RapidOCR",
            "description": "Fast CPU/GPU OCR (ONNX)",
            "size": "~10 MB",
            "location": "./models/rapidocr",
            "type": "OCR",
            "auto_download": True,
            # Must have the actual ONNX model file
            "check_path": "./models/rapidocr/latin_PP-OCRv5_rec_infer.onnx",
        },
        {
            "name": "Comic Bubble Detector",
            "description": "Specialized YOLOv8m for speech bubbles (ogkalu)",
            "size": "~50 MB",
            "location": "./models/yolo/comic-speech-bubble-detector.pt",
            "type": "Detection",
            "auto_download": True,
            "check_path": "./models/yolo/comic-speech-bubble-detector.pt",
        },
        {
            "name": "YOLOv8n",
            "description": "Nano model - fastest, least accurate",
            "size": "~6 MB",
            "location": "./models/yolo/yolov8n.pt",
            "type": "Detection",
            "auto_download": True,
            "check_path": "./models/yolo/yolov8n.pt",
        },
        {
            "name": "YOLOv8s",
            "description": "Small model - balanced speed/accuracy",
            "size": "~22 MB",
            "location": "./models/yolo/yolov8s.pt",
            "type": "Detection",
            "auto_download": True,
            "check_path": "./models/yolo/yolov8s.pt",
        },
        {
            "name": "YOLOv8m",
            "description": "Medium model - more accurate",
            "size": "~52 MB",
            "location": "./models/yolo/yolov8m.pt",
            "type": "Detection",
            "auto_download": True,
            "check_path": "./models/yolo/yolov8m.pt",
        },
        {
            "name": "YOLOv8l",
            "description": "Large model - most accurate, slower",
            "size": "~87 MB",
            "location": "./models/yolo/yolov8l.pt",
            "type": "Detection",
            "auto_download": True,
            "check_path": "./models/yolo/yolov8l.pt",
        },
        {
            "name": "LaMa",
            "description": "Large Mask Inpainting - AI text removal",
            "size": "~200 MB",
            "location": "./models/torch",
            "type": "Inpainting",
            "auto_download": True,
            # LaMa downloads to torch hub cache as big-lama/
            "check_path": "./models/torch/hub/checkpoints",
        },
        {
            "name": "NLLB-200",
            "description": "Meta's No Language Left Behind - high quality",
            "size": "~2.3 GB",
            "location": "./models/huggingface",
            "type": "Translation",
            "auto_download": False,
            # TRANSFORMERS_CACHE puts models directly in huggingface/ (no hub/ prefix)
            "check_path": "./models/huggingface/models--facebook--nllb-200-distilled-600M/snapshots",
        },
        {
            "name": "OPUS-MT",
            "description": "Helsinki-NLP translation models",
            "size": "~300 MB per language pair",
            "location": "./models/huggingface",
            "type": "Translation",
            "auto_download": False,
            # TRANSFORMERS_CACHE puts models directly in huggingface/ (no hub/ prefix)
            "check_path": "./models/huggingface/models--Helsinki-NLP--opus-mt-ja-en/snapshots",
        },
    ]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Download Models")
        self.setMinimumWidth(800)
        self.setMinimumHeight(500)
        
        self.download_thread = None
        self.download_buttons = []
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the dialog UI"""
        layout = QVBoxLayout(self)
        
        # Info label
        info_label = QLabel(
            "Models are downloaded automatically when first used. "
            "You can also download them manually using the buttons below."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)
        
        # Models table with 6 columns now (added Action)
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Model", "Type", "Size", "Location", "Status", "Action"
        ])
        
        # Configure table
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        
        self.table.setRowCount(len(self.MODELS))
        
        for row, model in enumerate(self.MODELS):
            # Model name + description
            name_item = QTableWidgetItem(f"{model['name']}\n{model['description']}")
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, name_item)
            
            # Type
            type_item = QTableWidgetItem(model['type'])
            type_item.setFlags(type_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 1, type_item)
            
            # Size
            size_item = QTableWidgetItem(model['size'])
            size_item.setFlags(size_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 2, size_item)
            
            # Location
            location = self._expand_path(model['location'])
            loc_item = QTableWidgetItem(location)
            loc_item.setFlags(loc_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            loc_item.setToolTip(location)
            self.table.setItem(row, 3, loc_item)
            
            # Status
            status = self._check_model_status(model)
            status_item = QTableWidgetItem(status)
            status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 4, status_item)
            
            # Download button
            is_downloaded = "✓" in status
            btn = QPushButton("✓ Downloaded" if is_downloaded else "Download")
            btn.setEnabled(not is_downloaded)
            btn.setProperty("model_index", row)
            btn.clicked.connect(lambda checked, r=row: self._download_model(r))
            self.table.setCellWidget(row, 5, btn)
            self.download_buttons.append(btn)
        
        self.table.resizeRowsToContents()
        layout.addWidget(self.table)
        
        # Storage info
        storage_group = QGroupBox("Storage Location")
        storage_layout = QFormLayout(storage_group)
        
        from ...core.config import Config
        models_path = Config.MODELS_DIR
        
        storage_layout.addRow("All Models:", QLabel(str(models_path)))
        storage_layout.addRow("├─ HuggingFace:", QLabel("models/huggingface/hub/"))
        storage_layout.addRow("├─ RapidOCR:", QLabel("models/rapidocr/"))
        storage_layout.addRow("├─ Torch:", QLabel("models/torch/hub/"))
        storage_layout.addRow("└─ YOLO:", QLabel("models/yolo/"))
        
        layout.addWidget(storage_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        refresh_btn = QPushButton("Refresh Status")
        refresh_btn.clicked.connect(self.refresh_status)
        btn_layout.addWidget(refresh_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
    
    def _expand_path(self, path: str) -> str:
        """Expand ~ and ./ in paths"""
        if path.startswith("~"):
            return str(Path.home() / path[2:])
        elif path.startswith("./"):
            from ...core.config import Config
            base = Config.PORTABLE_DIR
            return str(base / path[2:])
        return path
    
    def _check_model_status(self, model: dict) -> str:
        """Check if a model is actually downloaded and usable.
        
        Uses the 'check_path' key which points to a specific file or 
        directory that MUST exist for the model to be considered downloaded.
        This prevents false positives from empty parent directories or 
        unrelated lock files.
        """
        check_loc = model.get('check_path', model['location'])
        check_path = Path(self._expand_path(check_loc))
        
        try:
            if not check_path.exists():
                if model.get('auto_download'):
                    return "Auto-download on first use"
                return "Not downloaded"
            
            if check_path.is_file():
                # For files: verify it's not a 0-byte stub
                size = check_path.stat().st_size
                if size < 1024:  # Less than 1KB is suspicious for a model
                    return "⚠ Incomplete"
                size_mb = size / (1024 * 1024)
                return f"✓ Downloaded ({size_mb:.1f} MB)"
            
            if check_path.is_dir():
                # For directories (like HF snapshots/): check there are real files inside
                real_files = [
                    f for f in check_path.rglob("*") 
                    if f.is_file() and not f.name.startswith(".")
                ]
                if not real_files:
                    if model.get('auto_download'):
                        return "Auto-download on first use"
                    return "Not downloaded"
                
                # Calculate total size of actual model files
                total_size = sum(f.stat().st_size for f in real_files)
                if total_size < 1024:  # Less than 1KB total is suspicious
                    return "⚠ Incomplete"
                size_mb = total_size / (1024 * 1024)
                return f"✓ Downloaded ({size_mb:.1f} MB)"
            
        except Exception as e:
            logger.warning(f"Error checking model status for {model['name']}: {e}")
            return "⚠ Error checking"
        
        if model.get('auto_download'):
            return "Auto-download on first use"
        return "Not downloaded"
    
    def _download_model(self, row: int):
        """Start downloading a model"""
        if self.download_thread and self.download_thread.isRunning():
            QMessageBox.warning(self, "Download in Progress", 
                              "Please wait for the current download to finish.")
            return
        
        model = self.MODELS[row]
        allow_unverified = False

        if "Comic Bubble Detector" in model['name']:
            from ...modules.detector import DETECTOR_MODEL_REGISTRY
            reg = DETECTOR_MODEL_REGISTRY.get("comic-speech-bubble-detector.pt", {})
            source_url = reg.get("url", "https://huggingface.co/ogkalu/comic-speech-bubble-detector-yolov8m/resolve/main/comic-speech-bubble-detector.pt")
            pinned_sha = reg.get("sha256")
            if not pinned_sha:
                reply = QMessageBox.warning(
                    self,
                    "Security Notice: Unverified Model Weights",
                    f"The model '{model['name']}' from:\n{source_url}\n\n"
                    f"does not have a pinned cryptographic SHA-256 hash. Loading executable model weights "
                    f"can execute arbitrary code.\n\n"
                    f"Do you explicitly opt in to download and use this unverified model?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
                allow_unverified = True
        
        # Disable all download buttons during download
        for btn in self.download_buttons:
            btn.setEnabled(False)
        
        # Show progress
        self.progress_bar.setVisible(True)
        self.status_label.setVisible(True)
        self.status_label.setText(f"Downloading {model['name']}...")
        
        # Start download thread
        self.download_thread = DownloadThread(model['name'], model['type'], allow_unverified=allow_unverified)
        self.download_thread.progress.connect(self._on_progress)
        self.download_thread.finished_download.connect(
            lambda success, msg: self._on_download_finished(row, success, msg)
        )
        self.download_thread.start()
    
    def _on_progress(self, message: str):
        """Update progress message"""
        self.status_label.setText(message)
        QApplication.processEvents()
    
    def _on_download_finished(self, row: int, success: bool, message: str):
        """Handle download completion"""
        self.progress_bar.setVisible(False)
        self.status_label.setText(message)
        
        if success:
            # Update the status and button for this row
            self.table.item(row, 4).setText("✓ Downloaded")
            self.download_buttons[row].setText("✓ Downloaded")
            self.download_buttons[row].setEnabled(False)
            QMessageBox.information(self, "Download Complete", message)
        else:
            QMessageBox.critical(self, "Download Failed", message)
        
        # Re-enable buttons that aren't already downloaded
        self.refresh_status()
    
    def refresh_status(self):
        """Refresh the status of all models"""
        for row, model in enumerate(self.MODELS):
            status = self._check_model_status(model)
            self.table.item(row, 4).setText(status)
            
            is_downloaded = "✓" in status
            self.download_buttons[row].setText("✓ Downloaded" if is_downloaded else "Download")
            self.download_buttons[row].setEnabled(not is_downloaded)
