
import logging
from pathlib import Path
import numpy as np
from typing import List, Optional
import time

from .detector import YOLOTextDetector
from ..core.config import Config

logger = logging.getLogger(__name__)

class DirectMLError(RuntimeError):
    """Raised when DirectML execution provider is unavailable or fails to initialize."""
    pass


class ONNXTextDetector(YOLOTextDetector):
    """
    ONNX Runtime implementation of YOLO text detector.
    
    Automatically exports the .pt model to .onnx if not present.
    Uses onnxruntime for inference (via Ultralytics wrapper or direct).
    Supports DirectML for AMD/Intel GPUs on Windows.
    """
    
    def __init__(self, model_path: str = "yolov8n.pt", confidence_threshold: float = None, device: Optional[str] = None):
        self.model_name = "YOLO-ONNX"
        from ..core.config import Config
        self.confidence_threshold = confidence_threshold if confidence_threshold is not None else Config.YOLO_CONFIDENCE
        self.device = device or getattr(Config, 'AI_DEVICE', 'auto')
        self.device_setting = self.device
        self.providers = ['CPUExecutionProvider']
        self.active_provider = 'CPUExecutionProvider'
        self.active_providers = self.providers
        self.session = None
        
        self.base_model_path = model_path
        self.onnx_path = self._get_onnx_path(model_path)
        
        try:
            if self.onnx_path and self.onnx_path.exists():
                logger.info(f"Found ONNX model: {self.onnx_path}")
                super().__init__(str(self.onnx_path), confidence_threshold, auto_acquire=False)
            else:
                logger.info(f"ONNX model not found for {model_path}. Loading PT to export...")
                super().__init__(model_path, confidence_threshold, auto_acquire=False)
                self._export_to_onnx()
        except RuntimeError as e:
            if "ultralytics" in str(e).lower():
                logger.info("ultralytics not installed; using ONNX Runtime direct session")
                self.model = None
            else:
                raise
        except Exception as e:
            logger.info(f"Base model init exception in ONNXTextDetector: {e}")
            self.model = None

        self.device = device or getattr(Config, 'AI_DEVICE', 'auto')
        self.device_setting = self.device
        self._configure_onnx_providers()

    def _configure_onnx_providers(self, device_override: Optional[str] = None):
        """Configure ONNX Runtime execution providers based on AI_DEVICE setting."""
        device = device_override or self.device_setting
        if str(device).lower() != 'directml':
            self.providers = ['CPUExecutionProvider']
            self.active_provider = 'CPUExecutionProvider'
            self.active_providers = self.providers
            return self.providers
            
        try:
            import onnxruntime as ort
        except ImportError:
            raise DirectMLError(
                "DirectML acceleration requested ('AI_DEVICE=directml'), but onnxruntime is not installed. "
                "Install onnxruntime-directml on Windows to use DirectML."
            )
            
        available_providers = ort.get_available_providers()
        logger.info(f"Available ONNX providers: {available_providers}")
        
        if 'DmlExecutionProvider' not in available_providers:
            raise DirectMLError(
                f"DirectML acceleration requested ('AI_DEVICE=directml'), but 'DmlExecutionProvider' is not available "
                f"in onnxruntime (available: {available_providers}). "
                f"DirectML requires onnxruntime-directml on a supported Windows system with a compatible GPU. "
                f"Never label a CPU run DirectML."
            )
            
        self.providers = ['DmlExecutionProvider', 'CPUExecutionProvider']
        self.active_providers = self.providers
        
        if self.onnx_path and self.onnx_path.exists():
            session = ort.InferenceSession(str(self.onnx_path), providers=self.providers)
            actual = session.get_providers()
            if 'DmlExecutionProvider' not in actual:
                raise DirectMLError(
                    f"DirectML requested, but ONNX Runtime fell back to {actual}. "
                    "Cannot label a CPU fallback as DirectML execution."
                )
            self.session = session
            self.active_provider = 'DmlExecutionProvider'
            if hasattr(self, 'model') and self.model is not None:
                if hasattr(self.model, 'model') and hasattr(self.model.model, 'session'):
                    self.model.model.session = session
                elif hasattr(self.model, 'predictor') and hasattr(self.model.predictor, 'model') and hasattr(self.model.predictor.model, 'session'):
                    self.model.predictor.model.session = session
        else:
            self.active_provider = 'DmlExecutionProvider'
        return self.providers
    
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
        if self.model is None:
            raise RuntimeError(
                "ONNX text detector model is not loaded. Cannot perform detection. "
                "Please acquire the model or select 'opencv' detector explicitly."
            )
        start_t = time.time()
        results = super().detect(image, ignore_sfx)
        dt = time.time() - start_t
        logger.debug(f"ONNX Detection time: {dt:.3f}s")
        return results

# Convenience alias
YOLOONNXDetector = ONNXTextDetector

