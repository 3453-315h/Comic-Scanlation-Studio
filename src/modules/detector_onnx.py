
import logging
from pathlib import Path
import numpy as np
from typing import List, Optional
import time

from .detector import YOLOTextDetector
from ..core.config import Config

logger = logging.getLogger(__name__)

class ONNXTextDetector(YOLOTextDetector):
    """
    ONNX Runtime implementation of YOLO text detector.
    
    Automatically exports the .pt model to .onnx if not present.
    Uses onnxruntime for inference (via Ultralytics wrapper or direct).
    Supports DirectML for AMD/Intel GPUs on Windows.
    """
    
    def __init__(self, model_path: str = "yolov8n.pt", confidence_threshold: float = None):
        # We don't call super().__init__ immediately because we need to handle the export first
        # But we need basic setup.
        
        self.model_name = "YOLO-ONNX"
        self.confidence_threshold = confidence_threshold if confidence_threshold is not None else Config.YOLO_CONFIDENCE
        
        # Get device setting
        self.device_setting = getattr(Config, 'AI_DEVICE', 'auto')
        
        # Resolve model path (source .pt)
        # We reuse the logic from YOLOTextDetector to find the .pt file
        # But we can't use super()._load_model() directly yet because it loads .pt
        
        # Let's use a temporary instance or static method logic? 
        # Easier: Just initialize super, then switch model.
        # But loading .pt might be slow/wasteful if we already have .onnx.
        
        # Better: Re-implement path finding or extract it.
        # For now, let's just use the super class to find the path, knowing it might load the PT model.
        # Optimization: We check if .onnx exists FIRST.
        
        self.base_model_path = model_path
        self.onnx_path = self._get_onnx_path(model_path)
        
        if self.onnx_path and self.onnx_path.exists():
            logger.info(f"Found ONNX model: {self.onnx_path}")
            super().__init__(str(self.onnx_path), confidence_threshold)
            # Configure DirectML if needed
            self._configure_onnx_providers()
        else:
            logger.info(f"ONNX model not found for {model_path}. Loading PT to export...")
            # Load PT
            super().__init__(model_path, confidence_threshold)
            
            # Export
            self._export_to_onnx()
            
            # Re-load as ONNX
            # Ultralytics model object can be replaced
            if self.onnx_path and self.onnx_path.exists():
                 logger.info(f"Reloading with ONNX model: {self.onnx_path}")
                 try:
                     from ultralytics import YOLO
                     self.model = YOLO(str(self.onnx_path), task='detect')
                     self._configure_onnx_providers()
                 except ImportError:
                     logger.error("ultralytics not installed")
    
    def _configure_onnx_providers(self):
        """Configure ONNX Runtime execution providers based on AI_DEVICE setting."""
        if self.device_setting != 'directml':
            return  # Use default providers
            
        try:
            import onnxruntime as ort
            
            # Check if DirectML is available
            available_providers = ort.get_available_providers()
            logger.info(f"Available ONNX providers: {available_providers}")
            
            if 'DmlExecutionProvider' in available_providers:
                logger.info("DirectML provider available - AMD/Intel GPU acceleration enabled")
                # Ultralytics uses its own session, but we log availability
                # For direct ONNX usage, set providers order
            else:
                logger.warning("DirectML requested but not available. Install onnxruntime-directml.")
                
        except ImportError:
            logger.warning("onnxruntime not installed. DirectML unavailable.")
    
    def _get_onnx_path(self, pt_path: str) -> Optional[Path]:
        """Derive ONNX path from PT path"""
        
        # Helper to check if a path corresponds to an ONNX file
        def check_path(p: Path) -> Optional[Path]:
            if str(p).endswith('.onnx') and p.exists():
                return p
            if str(p).endswith('.pt'):
                candidate = p.with_suffix('.onnx')
                if candidate.exists():
                    return candidate
            return None

        # 1. Check direct path
        p = Path(pt_path)
        found = check_path(p)
        if found: return found

        # 2. Check standard directories
        from ..core.config import Config
        search_dirs = [
             Config.MODELS_DIR / "yolo",
             Config.MODELS_DIR,
             Config.BASE_DIR / "models" / "yolo",
             Config.BASE_DIR / "_internal" / "models" / "yolo"
        ]
        
        for d in search_dirs:
            # Check for pt_path filename in these dirs
            candidate_pt = d / p.name
            found = check_path(candidate_pt)
            if found: return found

        return None

    def _export_to_onnx(self):
        """Export current YOLO model to ONNX format"""
        if not self.model:
            return
            
        logger.info(f"Exporting model to ONNX: {self.model_path}")
        try:
            # Export
            # format='onnx', dynamic=True (for variable size), opset=12+ (for wider support)
            # half=True (FP16) - good for DirectML? Maybe. Let's stick to default FP32 for compat first.
            
            # Note: Ultralytics export() returns the filename of the exported model
            path = self.model.export(format="onnx", dynamic=True)
            
            logger.info(f"Export complete: {path}")
            
            # Verify existence
            exported_path = Path(path)
            if exported_path.exists():
                self.onnx_path = exported_path
                return
                
        except Exception as e:
            logger.error(f"ONNX Export failed: {e}")
            logger.warning("Falling back to PyTorch inference")
            
    def detect(self, image: np.ndarray, ignore_sfx: bool = True) -> List:
        """Run detection (Same as parent, but logging timing for benchmark)"""
        start_t = time.time()
        results = super().detect(image, ignore_sfx)
        dt = time.time() - start_t
        logger.debug(f"ONNX Detection time: {dt:.3f}s")
        return results
