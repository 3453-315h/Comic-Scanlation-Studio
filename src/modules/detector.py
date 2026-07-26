"""
Text Detection Module - Comic Translation Studio

Implements text bubble detection using OpenCV-based contour detection.
This is a lightweight, practical approach that works well for manga/comics.

For production, consider upgrading to:
- CRAFT (Character Region Awareness for Text Detection)
- DBNet (Differentiable Binarization)
- YOLOv8 fine-tuned on comic text
"""

# Lazy torch import
torch = None

# FIX: Monkeypatch DataLoader to prevent 'pin_memory' warning on CPU from Ultralytics
# We need to do this before Ultralytics imports torch.utils.data
try:
    import torch.utils.data
    _original_init = torch.utils.data.DataLoader.__init__

    def _patched_init(self, *args, **kwargs):
        if kwargs.get('pin_memory', False):
            import torch
            if not torch.cuda.is_available():
                kwargs['pin_memory'] = False
        _original_init(self, *args, **kwargs)

    torch.utils.data.DataLoader.__init__ = _patched_init
except ImportError:
    # Torch not installed or not found yet
    pass

from pathlib import Path
import cv2
import numpy as np
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)


class TextDetector:
    """Text detection using OpenCV contour-based detection
    
    This is a lightweight, efficient approach for manga/comic text detection.
    It works by:
    1. Converting to grayscale
    2. Adaptive thresholding
    3. Morphological operations to connect text
    4. Contour detection to find text regions
    """
    
    def __init__(self, model_name: str = "opencv-contour"):
        self.model_name = model_name
        
        # Determine device from Config with safe CUDA detection
        from ..core.config import Config
        device_setting = getattr(Config, 'AI_DEVICE', 'auto')
        
        if device_setting == "auto":
            self.device = self._safe_detect_device()
        else:
            import torch
            self.device = torch.device(device_setting)
            
        # Detection parameters (tuned for manga)
        self.min_area = 500  # Minimum bubble area in pixels
        self.max_area_ratio = 0.3  # Max 30% of image
        self.aspect_ratio_range = (0.2, 5.0)  # Width/height ratio
        
        logger.info(f"Initialized {self.model_name} text detector on {self.device}")
    
    @staticmethod
    def _safe_detect_device():
        """Safely detect the best available device.
        
        In frozen exe builds, CUDA may report as available but actually
        segfault when used. This method actually probes the device.
        """
        import sys
        
        import torch
        
        # In frozen exe, default to CPU unless CUDA actually works
        try:
            if torch.cuda.is_available():
                # Actually try to use CUDA to catch C-level failures
                _ = torch.zeros(1, device='cuda')
                logger.info("CUDA device verified and working")
                return torch.device("cuda")
        except Exception as e:
            logger.warning(f"CUDA reported available but failed probe: {e}")
        
        try:
            if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                return torch.device("mps")
        except Exception:
            pass
        
        return torch.device("cpu")
    
    def detect(self, image: np.ndarray, ignore_sfx: bool = True) -> List[dict]:
        """Detect text bubbles using robust Edge+Brightness analysis (Robust to panel borders)
        
        Args:
            image: Input image as numpy array (BGR or RGB)
            ignore_sfx: If True, filter out small regions
            
        Returns:
            List of TextBubble objects
        """
        # Import here to avoid circular import
        from ..core.project import TextBubble
        
        height, width = image.shape[:2]
        total_area = height * width
        
        # 1. Preprocessing
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
            
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # 2. Edge Detection (Canny) to find bubble outlines
        # 50, 150 are standard for high contrast manga
        edges = cv2.Canny(blurred, 50, 150)
        
        # Dilate edges to close small gaps in outlines
        kernel_edge = np.ones((3,3), np.uint8)
        edges_dilated = cv2.dilate(edges, kernel_edge, iterations=2)
        
        # 3. Find Contours 
        # CRITICAL: Use RETR_TREE to find bubbles nested inside panel borders
        contours, hierarchy = cv2.findContours(
            edges_dilated, 
            cv2.RETR_TREE, 
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        valid_bubbles = []
        # Lowered minimum area to catch small speech bubbles
        min_area = 400 if ignore_sfx else 200
        
        for i, cnt in enumerate(contours):
            # Geometric filtering
            x, y, w, h = cv2.boundingRect(cnt)
            area = w * h
            aspect = w / h if h > 0 else 0
            
            if area < min_area: continue
            if area > total_area * 0.4: continue # Ignore panels/page
            # Widened aspect ratio to catch long vertical or horizontal text
            if not (0.15 < aspect < 5.0): continue 
            
            # Solidity check (Bubbles are generally convex)
            hull = cv2.convexHull(cnt)
            hull_area = cv2.contourArea(hull)
            cnt_area = cv2.contourArea(cnt)
            solidity = cnt_area / hull_area if hull_area > 0 else 0
            
            # Lowered solidity to catch spiky shouting bubbles
            if solidity < 0.5: continue
            
            # Content Brightness Verification
            # Speech bubbles are white/bright. Dark regions are typically panels/art.
            # ⚡ Optimized: Use ROI-based masking instead of full-image np.zeros_like
            # to avoid huge memory allocations per contour.
            x_b, y_b, w_b, h_b = cv2.boundingRect(cnt)
            # Ensure ROI is within bounds
            x_b = max(0, x_b)
            y_b = max(0, y_b)
            w_b = min(width - x_b, w_b)
            h_b = min(height - y_b, h_b)

            if w_b <= 0 or h_b <= 0:
                continue

            roi_mask = np.zeros((h_b, w_b), dtype=np.uint8)
            cnt_offset = cnt - [x_b, y_b]
            cv2.drawContours(roi_mask, [cnt_offset], 0, 255, -1)

            roi = gray[y_b:y_b+h_b, x_b:x_b+w_b]
            mean_val = cv2.mean(roi, mask=roi_mask)[0]
            
            # Brightness threshold (relaxed significantly to 100 to allow for dark scans)
            if mean_val < 100: 
                continue
            
            # Additional check: Text texture? 
            # (Optional, but brightness + edges + shape is usually enough)
            
            # Confidence score
            confidence = (solidity * 0.5) + (min(1.0, mean_val/255.0) * 0.5)
            
            valid_bubbles.append(TextBubble(
                bbox=[x, y, x+w, y+h],
                text_original="", # Will be filled by OCR
                confidence=round(confidence, 2)
            ))
            
        # 4. Remove duplicates (NMS-like)
        # Nested contours can duplicate the same bubble (inner/outer edge)
        final_bubbles = []
        # Sort by area (largest first, to handle nesting correctly)
        valid_bubbles.sort(key=lambda b: (b.bbox[2]-b.bbox[0])*(b.bbox[3]-b.bbox[1]), reverse=True)
        
        for b in valid_bubbles:
            is_duplicate = False
            bx1, by1, bx2, by2 = b.bbox
            b_area = (bx2-bx1) * (by2-by1)
            
            for existing in final_bubbles:
                ex1, ey1, ex2, ey2 = existing.bbox
                e_area = (ex2-ex1) * (ey2-ey1)
                
                # Check Overlap
                ix1 = max(bx1, ex1)
                iy1 = max(by1, ey1)
                ix2 = min(bx2, ex2)
                iy2 = min(by2, ey2)
                
                if ix1 < ix2 and iy1 < iy2:
                    overlap_area = (ix2-ix1) * (iy2-iy1)
                    # If heavily overlapping (>80% of current bubble), it's a duplicate of a larger one
                    if overlap_area > 0.8 * b_area:
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                final_bubbles.append(b)
        
        # Sort top-bottom, left-right for reading order
        final_bubbles.sort(key=lambda b: (b.bbox[1], b.bbox[0]))
        
        logger.info(f"Detected {len(final_bubbles)} text regions (Robust)")
        return final_bubbles
    
    def _calculate_confidence(self, x1: int, y1: int, x2: int, y2: int, 
                            img_width: int, img_height: int) -> float:
        """Calculate confidence score for a detected region
        
        Factors:
        - Size (larger is more confident)
        - Position (central is more confident)
        - Aspect ratio (closer to square is speech bubble)
        """
        # Size score (0-1, normalized by image size)
        area = (x2 - x1) * (y2 - y1)
        img_area = img_width * img_height
        size_score = min(1.0, area / (img_area * 0.1))
        
        # Centrality score (0-1, higher if closer to center)
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        img_center_x = img_width / 2
        img_center_y = img_height / 2
        
        distance_from_center = np.sqrt(
            ((center_x - img_center_x) / img_width) ** 2 + 
            ((center_y - img_center_y) / img_height) ** 2
        )
        centrality_score = max(0, 1 - distance_from_center)
        
        # Aspect ratio score (closer to 1:1 or 3:2 is better)
        width = x2 - x1
        height = y2 - y1
        aspect = width / height if height > 0 else 1
        ideal_aspect = 1.5  # Typical speech bubble
        aspect_score = 1 - min(1, abs(aspect - ideal_aspect) / 2)
        
        # Weighted average
        confidence = (
            size_score * 0.5 + 
            centrality_score * 0.2 + 
            aspect_score * 0.3
        )
        
        return round(confidence, 3)


class YOLOTextDetector(TextDetector):
    """YOLO-based text detection using Ultralytics
    
    Uses YOLOv8/v11 for more accurate text detection compared to OpenCV contours.
    Supports both pretrained models and custom fine-tuned models.
    
    Usage:
        detector = YOLOTextDetector("yolov8n.pt")  # Use pretrained nano
        detector = YOLOTextDetector("manga-text-detector.pt")  # Use custom
    """
    
    def __init__(self, model_path: str = "yolov8n.pt", confidence_threshold: float = None):
        super().__init__(model_name="YOLO")
        
        # Import config to get default if not provided
        from ..core.config import Config
        self.confidence_threshold = confidence_threshold if confidence_threshold is not None else Config.YOLO_CONFIDENCE
        
        self.model_path = model_path
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load YOLO model from Ultralytics"""
        try:
            from ultralytics import YOLO
            
            # Check if model exists in models/yolo/
            model_path_obj = Path(self.model_path)
            
            # Define search paths in order of priority
            from ..core.config import Config
            search_paths = [
                model_path_obj,                                      # Absolute or CWD relative
                Config.MODELS_DIR / "yolo" / self.model_path,        # User models/yolo
                Config.MODELS_DIR / self.model_path,                 # User models root
                Config.BASE_DIR / "models" / "yolo" / self.model_path, # Bundled models
                Config.BASE_DIR / "_internal" / "models" / "yolo" / self.model_path, # PyInstaller _internal
                # Path.home() / ".scanlation_tool" / "models" / self.model_path # Global fallback
            ]
            
            found_path = None
            for p in search_paths:
                if p.exists():
                    found_path = str(p.resolve())
                    break
            
            if found_path:
                self.model_path = found_path
                logger.info(f"Loading YOLO model from: {self.model_path}")
                self.model = YOLO(self.model_path)
                logger.info(f"YOLO model loaded successfully")
            else:
                if not str(model_path_obj).endswith(".pt"):
                     raise FileNotFoundError(f"Model file not found: {self.model_path}")
                
                logger.warning(f"Model {self.model_path} not found locally, letting Ultralytics attempt download.")
                self.model = YOLO(self.model_path)

        except ImportError:
            logger.error(
                "ultralytics not installed. Install with: pip install ultralytics"
            )
            self.model = None  # Don't re-raise — fall back to OpenCV in detect()
        except Exception as e:
            logger.error(f"Failed to load YOLO model from {self.model_path}: {e}")
            self.model = None  # Don't re-raise — fall back to OpenCV in detect()
    
    def detect(self, image: np.ndarray, ignore_sfx: bool = True) -> List:
        """Detect text bubbles using YOLO
        
        Args:
            image: Input image as numpy array (BGR)
            ignore_sfx: If True, filter out small regions (likely sound effects)
            
        Returns:
            List of TextBubble objects with detected regions
        """
        from ..core.project import TextBubble
        
        if self.model is None:
            logger.warning("YOLO model not loaded, falling back to OpenCV")
            return super().detect(image, ignore_sfx)
        
        height, width = image.shape[:2]
        max_dim = max(height, width)
        # Round up to nearest 32
        inference_size = int(np.ceil(max_dim / 32) * 32)
        # Reverted to 3200 to prevent startup Access Violation crashes
        # 4096 might be causing issues with certain backend drivers or memory allocators
        inference_size = min(inference_size, 3200) 
        
        # Run YOLO inference with safe device handling
        try:
            results = self.model(image, verbose=False, conf=self.confidence_threshold, imgsz=inference_size, device=str(self.device))
        except Exception as e:
            logger.warning(f"YOLO inference failed on {self.device}: {e}")
            # Retry on CPU if non-CPU device failed
            if str(self.device).lower() != 'cpu':
                logger.info("Retrying YOLO inference on CPU...")
                import torch
                self.device = torch.device('cpu')
                # Explicitly pass device='cpu' to override model's device
                results = self.model(image, verbose=False, conf=self.confidence_threshold, imgsz=inference_size, device='cpu')
            else:
                raise
        
        bubbles = []
        
        for result in results:
            if result.boxes is None:
                continue
                
            for box in result.boxes:
                # Get bounding box coordinates
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                confidence = float(box.conf[0])
                
                # Ensure within image bounds
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(width, x2), min(height, y2)
                
                # Calculate area
                area = (x2 - x1) * (y2 - y1)
                
                # Filter small SFX if requested. Lowered area threshold to catch small bubbles.
                if ignore_sfx and area < 400:
                    continue
                
                bubble = TextBubble(
                    bbox=[x1, y1, x2, y2],
                    confidence=confidence
                )
                bubbles.append(bubble)
        
        # Sort by reading order (top to bottom, left to right for manga)
        bubbles.sort(key=lambda b: (b.bbox[1], b.bbox[0]))
        
        logger.info(f"YOLO detected {len(bubbles)} text regions")
        return bubbles


# Legacy alias for backward compatibility
AdvancedTextDetector = YOLOTextDetector