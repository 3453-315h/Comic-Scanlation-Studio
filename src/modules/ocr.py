"""
OCR Module - Comic Translation Studio

Implements manga/comic OCR using manga-ocr model.
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Lazy imports
MangaOcr = None
RapidOCR = None


class MangaOCR:
    """OCR using manga-ocr model"""
    
    def __init__(self, model_name: str = "manga_ocr"):
        self.model_name = model_name
        self.mocr = None
        self.confidence = 0.0
        self._load_model()
    
    def _load_model(self):
        """Load manga-ocr model"""
        try:
            from manga_ocr import MangaOcr
            
            # Determine device
            from ..core.config import Config
            device_setting = getattr(Config, 'AI_DEVICE', 'auto')
            device = "cpu"
            
            if device_setting == "auto":
                import torch
                if torch.cuda.is_available():
                    device = "cuda"
                elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                    device = "mps"
            else:
                device = device_setting
                
            logger.info(f"Loading {self.model_name} on {device}...")
            self.mocr = MangaOcr(device=device)
            logger.info("MangaOCR model loaded successfully")
            
        except ImportError:
            logger.warning("manga_ocr not installed. Install with: pip install manga-ocr")
        except Exception as e:
            logger.error(f"Failed to load MangaOCR: {e}")
    
    def recognize(self, image: np.ndarray, bbox: list) -> str:
        """Recognize text in the bbox region"""
        if self.mocr is None:
            logger.warning("MangaOCR not loaded, text recognition unavailable")
            return ""
        
        # Validate bbox
        if not isinstance(bbox, list) or len(bbox) != 4:
            logger.error(f"Invalid bbox format: {bbox}")
            return ""
        
        # Extract region of interest
        x1, y1, x2, y2 = bbox
        roi = image[y1:y2, x1:x2]
        
        # Convert to PIL Image
        from PIL import Image
        pil_image = Image.fromarray(cv2.cvtColor(roi, cv2.COLOR_BGR2RGB))
        
        try:
            text = self.mocr(pil_image)
            # Note: manga_ocr doesn't provide confidence scores
            # We estimate based on text length (longer = more confident)
            self.confidence = min(0.95, 0.5 + len(text) * 0.05)
            return text.strip()
        except Exception as e:
            logger.error(f"OCR error: {e}")
            original_text = "ERROR" # Fallback if error
            self.confidence = 0.0
            return ""


class EasyOCR:
    """
    Wrapper for RapidOCR (PaddleOCR ONNX).
    Kept name 'EasyOCR' for backward compatibility. 
    NOTE: This does NOT use the 'easyocr' pip package.
    """
    
    def __init__(self, languages: list = None, config=None):
        # Languages argument is kept for compatibility but RapidOCR auto-detects
        self.reader = None
        self.confidence = 0.0
        self.config = config
        self._load_model()
    
    def _load_model(self):
        """Load RapidOCR reader"""
        try:
            from rapidocr_onnxruntime import RapidOCR
            logger.info("Loading RapidOCR (PaddleOCR ONNX)...")
            
            # Determine device
            from ..core.config import Config
            device_setting = getattr(Config, 'AI_DEVICE', 'auto')
            use_cuda = False
            
            if device_setting == "cuda":
                use_cuda = True
            elif device_setting == "auto":
                import torch
                if torch.cuda.is_available():
                    use_cuda = True
            
            # Paths to custom Latin model (better for Polish)
            from ..core.config import Config
            model_path = Config.MODELS_DIR / "rapidocr" / "latin_PP-OCRv5_rec_infer.onnx"
            dict_path = Config.MODELS_DIR / "rapidocr" / "latin_v5_dict.txt"
            
            # Helper to check file existence
            has_custom = model_path.exists() and dict_path.exists()
            
            # Configure CUDA providers if requested
            # RapidOCR usually auto-detects if onnxruntime-gpu is installed, 
            # but we can try to force or just log.
            # RapidOCR init args: det_use_cuda, cls_use_cuda, rec_use_cuda
            
            kwargs = {
                'det_use_cuda': use_cuda,
                'cls_use_cuda': use_cuda,
                'rec_use_cuda': use_cuda,
                'det_model_path': None,
                'cls_model_path': None,
                'rec_model_path': None
            }
            
            if has_custom:
                logger.info(f"Using custom Latin V5 model: {model_path} (CUDA={use_cuda})")
                kwargs['rec_model_path'] = str(model_path)
                kwargs['rec_keys_path'] = str(dict_path)
                
            self.reader = RapidOCR(**kwargs)
            
            logger.info("RapidOCR loaded successfully")
        except ImportError:
             logger.error("rapidocr_onnxruntime not installed")
        except Exception as e:
            logger.error(f"Failed to load RapidOCR: {e}")
            
    def recognize(self, image: np.ndarray, bbox: list) -> str:
        """Recognize text in the bbox region"""
        if self.reader is None:
            return "OCR engine not loaded"
            
        # 1. Padding to ensure text edges are captured
        # 2. Convert to grayscale for better contrast
        # 3. Simple thresholding might help if image is noisy
        
        # Extract ROI
        x1, y1, x2, y2 = bbox
        
        # Add padding (10%)
        h, w = image.shape[:2]
        pad_x = int((x2 - x1) * 0.1)
        pad_y = int((y2 - y1) * 0.1)
        
        x1 = max(0, x1 - pad_x)
        y1 = max(0, y1 - pad_y)
        x2 = min(w, x2 + pad_x)
        y2 = min(h, y2 + pad_y)
        
        roi = image[y1:y2, x1:x2]
        
        try:
            # RapidOCR returns list of results: [[[[pt, pt, pt, pt], "text", confidence], ...]]
            # We treat the whole ROI as one text block
            result, elapse = self.reader(roi)
            
            if not result:
                return ""
            
            # Combine all detected text lines
            combined_text = " ".join([line[1] for line in result])
            
            # Calculate average confidence
            confs = [line[2] for line in result]
            self.confidence = sum(confs) / len(confs) if confs else 0.0
            
            return combined_text.strip()
            
        except Exception as e:
            logger.error(f"RapidOCR error: {e}")
            return ""

# Alias for compatibility
RapidOCR_Module = EasyOCR