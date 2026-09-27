import logging
from pathlib import Path
import numpy as np
from typing import List, Optional
import time

from .detector import YOLOTextDetector, ModelNotFoundError, ModelAcquisitionError
from ..core.config import Config

logger = logging.getLogger(__name__)


class DirectMLError(RuntimeError):
    """Raised when DirectML execution provider is unavailable or fails to initialize."""
    pass


class ONNXTextDetector(YOLOTextDetector):
    """
    ONNX Runtime implementation of YOLO text detector.
    
    Automatically acquires the model or exports the .pt model to .onnx if not present.
    Uses onnxruntime for direct session inference.
    Supports DirectML for AMD/Intel GPUs on Windows.
    """
    
    def __init__(self, model_path: str = "comic-speech-bubble-detector.pt", confidence_threshold: float = None, device: Optional[str] = None):
        self.model_name = "YOLO-ONNX"
        from ..core.config import Config
        self.confidence_threshold = confidence_threshold if confidence_threshold is not None else Config.YOLO_CONFIDENCE
        self.device = device or getattr(Config, 'AI_DEVICE', 'auto')
        self.device_setting = self.device
        self.providers = ['CPUExecutionProvider']
        self.active_provider = 'CPUExecutionProvider'
        self.active_providers = self.providers
        self.session = None
        self.model = None
        
        self.base_model_path = model_path
        self.onnx_path = self._get_onnx_path(model_path)
        
        # 1. If ONNX model already exists, try loading it
        if self.onnx_path and self.onnx_path.exists():
            logger.info(f"Found existing ONNX model: {self.onnx_path}")
            try:
                super().__init__(str(self.onnx_path), self.confidence_threshold, device=self.device, auto_acquire=False)
            except RuntimeError as e:
                if "ultralytics" in str(e).lower():
                    logger.info("ultralytics not installed; using ONNX Runtime direct session exclusively")
                    self.model = None
                else:
                    raise
        else:
            # 2. Acquire or load base .pt model, then export to ONNX
            logger.info(f"ONNX model not found for '{model_path}'. Initializing base model with auto_acquire=True...")
            try:
                super().__init__(model_path, self.confidence_threshold, device=self.device, auto_acquire=True)
                self._export_to_onnx()
            except (ModelNotFoundError, ModelAcquisitionError):
                # Re-raise acquisition/not-found errors immediately so they surface before inference
                raise
            except RuntimeError as e:
                if "ultralytics" in str(e).lower():
                    if not (self.onnx_path and self.onnx_path.exists()):
                        raise RuntimeError(
                            f"ultralytics is required to convert '{model_path}' to ONNX format. "
                            "Please install ultralytics or provide a pre-exported .onnx model."
                        ) from e
                    self.model = None
                else:
                    raise

        self._configure_onnx_providers()

    def _configure_onnx_providers(self, device_override: Optional[str] = None):
        """Configure ONNX Runtime execution providers based on AI_DEVICE setting."""
        device = device_override or self.device_setting
        is_dml = str(device).lower() == 'directml'
        
        try:
            import onnxruntime as ort
        except ImportError:
            if is_dml:
                raise DirectMLError(
                    "DirectML acceleration requested ('AI_DEVICE=directml'), but onnxruntime is not installed. "
                    "Install onnxruntime-directml on Windows to use DirectML."
                )
            self.providers = ['CPUExecutionProvider']
            self.active_provider = 'CPUExecutionProvider'
            self.active_providers = self.providers
            return self.providers
            
        available_providers = ort.get_available_providers()
        logger.info(f"Available ONNX providers: {available_providers}")
        
        if is_dml:
            if 'DmlExecutionProvider' not in available_providers:
                raise DirectMLError(
                    f"DirectML acceleration requested ('AI_DEVICE=directml'), but 'DmlExecutionProvider' is not available "
                    f"in onnxruntime (available: {available_providers}). "
                    f"DirectML requires onnxruntime-directml on a supported Windows system with a compatible GPU. "
                    f"Never label a CPU run DirectML."
                )
            self.providers = ['DmlExecutionProvider', 'CPUExecutionProvider']
        else:
            self.providers = ['CPUExecutionProvider']

        self.active_providers = self.providers
        
        if self.onnx_path and self.onnx_path.exists():
            try:
                session = ort.InferenceSession(str(self.onnx_path), providers=self.providers)
                actual = session.get_providers()
                if is_dml and 'DmlExecutionProvider' not in actual:
                    raise DirectMLError(
                        f"DirectML requested, but ONNX Runtime fell back to {actual}. "
                        "Cannot label a CPU fallback as DirectML execution."
                    )
                self.session = session
                self.active_provider = actual[0] if actual else 'CPUExecutionProvider'
            except Exception as e:
                if isinstance(e, DirectMLError):
                    raise
                if is_dml:
                    raise DirectMLError(f"Failed to create DirectML session: {e}") from e
                logger.warning(f"Could not initialize ONNX Runtime session: {e}")
                self.session = None
                self.active_provider = 'CPUExecutionProvider'
        else:
            self.session = None
            if is_dml:
                raise DirectMLError(
                    "DirectML acceleration requested, but no ONNX model file was found or exported. "
                    "Cannot report DirectML active without a loaded ONNX session."
                )
            self.active_provider = 'CPUExecutionProvider'

        return self.providers
    
    def _get_onnx_path(self, pt_path: str) -> Optional[Path]:
        """Derive ONNX path from PT path"""
        def check_path(p: Path) -> Optional[Path]:
            if str(p).endswith('.onnx') and p.exists():
                return p
            if str(p).endswith('.pt'):
                candidate = p.with_suffix('.onnx')
                if candidate.exists():
                    return candidate
            return None

        p = Path(pt_path)
        found = check_path(p)
        if found:
            return found

        from ..core.config import Config
        search_dirs = [
            Config.MODELS_DIR / "yolo",
            Config.MODELS_DIR,
            Config.BASE_DIR / "models" / "yolo",
            Config.BASE_DIR / "_internal" / "models" / "yolo"
        ]
        
        for d in search_dirs:
            candidate_pt = d / p.name
            found = check_path(candidate_pt)
            if found:
                return found

        return None

    def _export_to_onnx(self):
        """Export current YOLO model to ONNX format"""
        if not self.model:
            return
            
        logger.info(f"Exporting model to ONNX: {self.model_path}")
        try:
            path = self.model.export(format="onnx", dynamic=True)
            logger.info(f"Export complete: {path}")
            exported_path = Path(path)
            if exported_path.exists():
                self.onnx_path = exported_path
                return
        except Exception as e:
            logger.error(f"ONNX Export failed: {e}")
            logger.warning("Falling back to PyTorch inference")
            
    def detect(self, image: np.ndarray, ignore_sfx: bool = True) -> List:
        """Run detection using direct ONNX Runtime session if available, or PyTorch fallback."""
        if self.session is None and self.model is None:
            raise RuntimeError(
                "ONNX text detector model is not loaded. Cannot perform detection. "
                "Please acquire the model or select 'opencv' detector explicitly."
            )

        if str(self.device_setting).lower() == 'directml' and (self.session is None or self.active_provider != 'DmlExecutionProvider'):
            raise DirectMLError(
                "DirectML inference requested, but no active DirectML session is available. "
                "Cannot fall back silently to CPU."
            )

        if self.session is not None:
            start_t = time.time()
            bubbles = self._detect_onnx_session(image, ignore_sfx)
            dt = time.time() - start_t
            logger.debug(f"Direct ONNX Detection time ({self.active_provider}): {dt:.3f}s")
            return bubbles

        start_t = time.time()
        results = super().detect(image, ignore_sfx)
        dt = time.time() - start_t
        logger.debug(f"PyTorch Detection time: {dt:.3f}s")
        return results

    def _detect_onnx_session(self, image: np.ndarray, ignore_sfx: bool = True) -> List:
        """Run direct inference through the active ONNX Runtime session with NMS and coordinate scaling."""
        from ..core.project import TextBubble
        import cv2

        orig_h, orig_w = image.shape[:2]
        
        inputs = self.session.get_inputs()
        input_name = inputs[0].name if inputs else "images"
        input_shape = getattr(inputs[0], 'shape', [1, 3, 640, 640]) if inputs else [1, 3, 640, 640]
        
        target_h = input_shape[2] if len(input_shape) > 2 and isinstance(input_shape[2], int) else 640
        target_w = input_shape[3] if len(input_shape) > 3 and isinstance(input_shape[3], int) else 640

        scale = min(target_w / max(1, orig_w), target_h / max(1, orig_h))
        nw, nh = int(round(orig_w * scale)), int(round(orig_h * scale))
        resized = cv2.resize(image, (nw, nh), interpolation=cv2.INTER_LINEAR)

        top = (target_h - nh) // 2
        bottom = target_h - nh - top
        left = (target_w - nw) // 2
        right = target_w - nw - left
        padded = cv2.copyMakeBorder(resized, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(114, 114, 114))

        rgb = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB)
        chw = np.transpose(rgb, (2, 0, 1)).astype(np.float32) / 255.0
        blob = np.expand_dims(chw, axis=0)

        outputs = self.session.run(None, {input_name: blob})
        raw_output = np.asarray(outputs[0])

        if len(raw_output.shape) == 3:
            # Check if format is (batch, features, num_anchors) e.g. (1, 5, 8400) or (1, 5, 2)
            # The features axis must have at least 4 elements (cx, cy, w, h).
            if raw_output.shape[1] >= 4 and (raw_output.shape[2] < 4 or (raw_output.shape[1] <= 32 and raw_output.shape[1] < raw_output.shape[2])):
                preds = np.transpose(raw_output[0], (1, 0))
            else:
                preds = raw_output[0]
        else:
            preds = raw_output

        boxes = []
        confidences = []

        for pred in preds:
            if len(pred) < 4:
                continue
            cx, cy, w, h = pred[0:4]
            scores = pred[4:] if len(pred) > 4 else [1.0]
            conf = float(np.max(scores))

            if conf >= self.confidence_threshold:
                x_p = cx - w / 2.0
                y_p = cy - h / 2.0
                
                x1 = int(round((x_p - left) / scale))
                y1 = int(round((y_p - top) / scale))
                w_orig = int(round(w / scale))
                h_orig = int(round(h / scale))
                
                x1 = max(0, min(orig_w - 1, x1))
                y1 = max(0, min(orig_h - 1, y1))
                x2 = max(0, min(orig_w, x1 + w_orig))
                y2 = max(0, min(orig_h, y1 + h_orig))

                if x2 > x1 and y2 > y1:
                    boxes.append([x1, y1, x2 - x1, y2 - y1])
                    confidences.append(conf)

        bubbles = []
        if boxes:
            indices = cv2.dnn.NMSBoxes(boxes, confidences, score_threshold=self.confidence_threshold, nms_threshold=0.45)
            if len(indices) > 0:
                indices = indices.flatten() if hasattr(indices, 'flatten') else [i[0] if isinstance(i, (list, tuple, np.ndarray)) else i for i in indices]
                for idx in indices:
                    x, y, w, h = boxes[idx]
                    area = w * h
                    if ignore_sfx and area < 400:
                        continue
                    bubbles.append(TextBubble(
                        bbox=[x, y, x + w, y + h],
                        confidence=confidences[idx]
                    ))

        bubbles.sort(key=lambda b: (b.bbox[1], b.bbox[0]))
        return bubbles


# Convenience alias
YOLOONNXDetector = ONNXTextDetector
