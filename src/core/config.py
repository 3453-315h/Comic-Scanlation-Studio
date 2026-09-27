import os
import json
from pathlib import Path
from dotenv import load_dotenv



class Config:
    import sys
    if getattr(sys, 'frozen', False):
        # Running as compiled exe
        BASE_DIR = Path(sys._MEIPASS)
        # However, for user data (projects, models), we want a writable location
        # Usually AppData or a portable folder next to exe
        # Let's use the folder where the .exe is for portability
        PORTABLE_DIR = Path(sys.executable).parent
    else:
        BASE_DIR = Path(__file__).parent.parent.parent
        PORTABLE_DIR = BASE_DIR
    
    APP_VERSION = "1.1.1"

    # Read-only assets (bundled)
    ASSETS_DIR = BASE_DIR / "assets"
    
    # Writable directories (User data)
    # If frozen, use the folder containing the exe (Portable Mode)
    MODELS_DIR = PORTABLE_DIR / "models"
    PROJECTS_DIR = PORTABLE_DIR / "projects"
    CACHE_DIR = PORTABLE_DIR / "cache"
    TRANSLATION_CACHE_FILE = CACHE_DIR / "translation_cache.json"
    CONFIG_FILE = PORTABLE_DIR / "config.json"
    
    # AI Models
    DETECTOR_MODEL = "yolo-onnx"  # Options: "opencv", "yolo", "yolo-onnx"
    YOLO_MODEL_PATH = "comic-speech-bubble-detector.pt"  # Specialized model
    YOLO_CONFIDENCE = 0.10 # Lowered to 0.10 to improve recall for faint bubbles
    OCR_MODEL = "easyocr"
    INPAINTER_MODEL = "lama"
    
    # Translation
    # Options: "deepl", "google", "openai", "nllb", "opus", "offline"
    TRANSLATION_API = "google"
    OFFLINE_MODEL = "nllb"  # Options: "nllb" (high quality), "opus" (fast)
    DEFAULT_SOURCE_LANG = "ja"
    DEFAULT_TARGET_LANG = "en"
    DEEPL_API_KEY = os.getenv("DEEPL_API_KEY", "")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    
    # App Settings
    DEFAULT_FONT = "Arial"
    DEFAULT_FONT_SIZE = 24
    MAX_IMAGE_SIZE = 4096
    ENABLE_IMPRINT = True
    AUTO_STYLE = True # Enable smart style detection by default
    
    # Inpainting
    INPAINT_MASK_DILATION = 4 # Reset down to 4 (adds ~2-3px padding to catch ghosting but save small bubbles)
    INPAINT_PROTECT_BORDERS = False # Disabled to prevent skipping text that touches bbox edges
    INPAINT_GUIDED_MODE = True  # Use text-color-aware mask expansion
    INPAINT_MASK_BLUR = 5  # Gaussian blur kernel size for mask edges (0 to disable)
    INPAINT_WHITEN_MODE = False # Standard LaMa behavior (True = Pure White Fill)
    
    # OCR
    OCR_CONFIDENCE_THRESHOLD = 0.0 # Default loose (allow everything)
    OCR_PADDING = 20
    
    # Imprinting
    IMPRINT_PADDING = 5
    IMPRINT_LINE_SPACING = 1.2
    IMPRINT_BOX_EXPANSION = 0
    IMPRINT_SHAPE_WRAPPING = True

    # AI / Hardware
    AI_DEVICE = "auto" # auto, cpu, cuda, mps, directml

    # Batch Processing
    BATCH_PARALLEL_ENABLED = False
    BATCH_MAX_WORKERS = 2
    
    # Export Settings
    EXPORT_IMAGE_QUALITY = 90
    
    # Saveable settings (keys to persist in JSON)
    _SAVEABLE = [
        "DETECTOR_MODEL", "YOLO_MODEL_PATH", "YOLO_CONFIDENCE",
        "OCR_MODEL", "OCR_CONFIDENCE_THRESHOLD", "OCR_PADDING",
        "INPAINTER_MODEL", "INPAINT_MASK_DILATION", "INPAINT_PROTECT_BORDERS",
        "INPAINT_GUIDED_MODE", "INPAINT_MASK_BLUR", "INPAINT_WHITEN_MODE",
        "TRANSLATION_API", "OFFLINE_MODEL",
        "DEFAULT_SOURCE_LANG", "DEFAULT_TARGET_LANG",
        "DEFAULT_FONT", "DEFAULT_FONT_SIZE", "MAX_IMAGE_SIZE",
        "ENABLE_IMPRINT", "AUTO_STYLE",
        "IMPRINT_PADDING", "IMPRINT_LINE_SPACING", "IMPRINT_BOX_EXPANSION", "IMPRINT_SHAPE_WRAPPING",
        "AI_DEVICE",
        "BATCH_PARALLEL_ENABLED", "BATCH_MAX_WORKERS",
        "EXPORT_IMAGE_QUALITY"
    ]
    
    def __init__(self):
        """Initialize config and load saved settings"""
        self.load()
    
    @classmethod
    def initialize_dirs(cls):
        """Create necessary directories and configure model cache"""
        cls.MODELS_DIR.mkdir(parents=True, exist_ok=True)
        cls.PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for different model types
        (cls.MODELS_DIR / "huggingface").mkdir(exist_ok=True)
        (cls.MODELS_DIR / "easyocr").mkdir(exist_ok=True)
        (cls.MODELS_DIR / "yolo").mkdir(exist_ok=True)
        (cls.MODELS_DIR / "rapidocr").mkdir(exist_ok=True)
        (cls.MODELS_DIR / "torch").mkdir(exist_ok=True)
        
        # When frozen: copy bundled models from _internal/models/ to PORTABLE_DIR/models/
        # so they're accessible at the expected location next to the exe
        import sys
        if getattr(sys, 'frozen', False):
            cls._copy_bundled_models()
        
        # Configure model cache locations
        cls.setup_model_cache()
    
    @classmethod
    def _copy_bundled_models(cls):
        """Copy bundled models from BASE_DIR (inside _internal/) to PORTABLE_DIR/models/.
        
        PyInstaller puts bundled data files inside _internal/ (BASE_DIR),
        but the app expects user-accessible models in PORTABLE_DIR/models/.
        This copies them on first run without overwriting existing downloads.
        """
        import shutil
        bundled_models = cls.BASE_DIR / "models"
        if not bundled_models.exists():
            return
        
        for src_file in bundled_models.rglob("*"):
            if not src_file.is_file():
                continue
            # Compute relative path and destination
            rel_path = src_file.relative_to(bundled_models)
            dest_file = cls.MODELS_DIR / rel_path
            
            # Only copy if destination doesn't already exist (don't overwrite user downloads)
            if not dest_file.exists():
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.copy2(str(src_file), str(dest_file))
                except Exception as e:
                    print(f"Warning: Could not copy bundled model {rel_path}: {e}")
    
    @classmethod
    def setup_model_cache(cls):
        """Configure all model libraries to use local models folder."""
        models_dir = str(cls.MODELS_DIR.absolute())
        
        # HuggingFace models (MangaOCR, NLLB, OPUS, etc.)
        hf_cache = str(cls.MODELS_DIR / "huggingface")
        os.environ["HF_HOME"] = hf_cache
        os.environ["TRANSFORMERS_CACHE"] = hf_cache
        os.environ["HF_DATASETS_CACHE"] = hf_cache
        
        # EasyOCR models
        easyocr_cache = str(cls.MODELS_DIR / "easyocr")
        os.environ["EASYOCR_MODULE_PATH"] = easyocr_cache
        
        # YOLO models (ultralytics)
        # YOLO downloads to current directory by default, we handle this in detector.py
    
    def save(self):
        """Save current settings to config file"""
        data = {}
        for key in self._SAVEABLE:
            value = getattr(self, key, None)
            if value is not None:
                data[key] = value
        
        try:
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save config: {e}")
    
    def load(self):
        """Load settings from config file"""
        if not self.CONFIG_FILE.exists():
            return
        
        try:
            with open(self.CONFIG_FILE, 'r') as f:
                data = json.load(f)
            
            for key, value in data.items():
                if key in self._SAVEABLE:
                    setattr(self, key, value)
        except Exception as e:
            print(f"Warning: Could not load config: {e}")
