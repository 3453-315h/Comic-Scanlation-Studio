"""
Scanlation Pipeline

Orchestrates the five-stage processing pipeline:
1️⃣ Text detection (TextDetector)
2️⃣ OCR (MangaOCR)
3️⃣ Translation (Translator)
4️⃣ Inpainting (LamaInpainter)
5️⃣ Text Imprinting (TextImprinter)

The implementation uses batch inpainting for efficiency and saves the processed image.
"""

import logging
from pathlib import Path
from typing import Optional, Callable

from .project import Project, Page, TextBubble
from ..utils.image_utils import load_image, save_image

logger = logging.getLogger(__name__)

from ..modules.ocr import MangaOCR, RapidOCR_Module
from ..modules.translator import Translator
from ..modules.inpainter import Inpainter #, LamaInpainter


class ScanlationPipeline:
    """Orchestrates the five-stage pipeline for a single page.
    
    Uses Lazy Loading for models to ensure fast application startup.
    Models are loaded only when first used.
    """

    def __init__(self, config=None):
        if config is None:
            from .config import Config
            config = Config()
        self.config = config
        
        # Lazy loaded components
        self._detector = None
        self._ocr = None
        self._inpainter = None
        self._translator = None
        self._imprinter = None
        
        # Cache configuration values
        self.enable_imprint = getattr(config, 'ENABLE_IMPRINT', True)
        self.box_expansion = getattr(config, 'IMPRINT_BOX_EXPANSION', 0)
        self.shape_wrapping = getattr(config, 'IMPRINT_SHAPE_WRAPPING', False)
        self._font_style = None  # Lazy load this too

    @property
    def detector(self):
        if self._detector is None:
            from ..modules.detector import TextDetector, YOLOTextDetector
            
            detector_type = getattr(self.config, 'DETECTOR_MODEL', 'opencv')
            
            if detector_type == 'yolo':
                model_path = str(getattr(self.config, 'YOLO_MODEL_PATH', 'comic-speech-bubble-detector.pt'))
                confidence = getattr(self.config, 'YOLO_CONFIDENCE', 0.25)
                self._detector = YOLOTextDetector(model_path, confidence)
            
            elif detector_type == 'yolo-onnx':
                from ..modules.detector_onnx import ONNXTextDetector
                model_path = str(getattr(self.config, 'YOLO_MODEL_PATH', 'comic-speech-bubble-detector.pt'))
                confidence = getattr(self.config, 'YOLO_CONFIDENCE', 0.25)
                self._detector = ONNXTextDetector(model_path, confidence)
                
            else:
                self._detector = TextDetector("opencv-robust")
        return self._detector

    @property
    def ocr(self):
        if self._ocr is None:
            # Select OCR Engine based on language
            source_lang = getattr(self.config, 'DEFAULT_SOURCE_LANG', 'ja')
            CJK_LANGS = ['ja', 'zh', 'zh-cn', 'zh-tw', 'ko']
            
            # Map simplified configuration to actual classes
            ocr_model_pref = getattr(self.config, 'OCR_MODEL', 'manga_ocr')
            
            if ocr_model_pref == 'manga_ocr' or (ocr_model_pref == 'auto' and source_lang in CJK_LANGS):
                logger.info("Loading MangaOCR...")
                from ..modules.ocr import MangaOCR
                self._ocr = MangaOCR("manga_ocr")
            else:
                logger.info(f"Loading RapidOCR/EasyOCR for {source_lang}...")
                from ..modules.ocr import EasyOCR
                # Initialize with English + Source Lang
                langs = ['en']
                if source_lang != 'en':
                    langs.append(source_lang)
                self._ocr = EasyOCR(langs, config=self.config)
        return self._ocr

    @property
    def inpainter(self) -> Inpainter:
        if self._inpainter is None:
            from ..modules.inpainter import LamaInpainter
            self._inpainter = LamaInpainter(
                model_name=self.config.INPAINTER_MODEL,
                mask_dilation=getattr(self.config, 'INPAINT_MASK_DILATION', 5),
                protect_borders=getattr(self.config, 'INPAINT_PROTECT_BORDERS', True),
                guided_mode=getattr(self.config, 'INPAINT_GUIDED_MODE', True),
                mask_blur=getattr(self.config, 'INPAINT_MASK_BLUR', 5),
                whiten_mode=getattr(self.config, 'INPAINT_WHITEN_MODE', False)
            )
        return self._inpainter

    @property
    def translator(self):
        if self._translator is None:
            from ..modules.translator import Translator
            self._translator = Translator(
                api=self.config.TRANSLATION_API,
                source_lang=self.config.DEFAULT_SOURCE_LANG,
                target_lang=self.config.DEFAULT_TARGET_LANG,
            )
        return self._translator

    @property
    def imprinter(self):
        if self._imprinter is None:
            from ..modules.imprinter import TextImprinter
            self._imprinter = TextImprinter()
        return self._imprinter

    @detector.setter
    def detector(self, value):
        self._detector = value

    @ocr.setter
    def ocr(self, value):
        self._ocr = value

    @inpainter.setter
    def inpainter(self, value):
        self._inpainter = value

    @translator.setter
    def translator(self, value):
        self._translator = value

    @imprinter.setter
    def imprinter(self, value):
        self._imprinter = value

    @property
    def renderer(self):
        return self.imprinter

    @renderer.setter
    def renderer(self, value):
        self.imprinter = value

    @property
    def font_style(self):
        if self._font_style is None:
            from ..modules.imprinter import FontStyle
            self._font_style = FontStyle(
                font_family=getattr(self.config, 'DEFAULT_FONT', 'Arial'),
                font_size=getattr(self.config, 'DEFAULT_FONT_SIZE', 24),
                color=getattr(self.config, 'DEFAULT_TEXT_COLOR', (0, 0, 0)),
                alignment=getattr(self.config, 'DEFAULT_TEXT_ALIGNMENT', 'center'),
                padding=getattr(self.config, 'IMPRINT_PADDING', 5),
                line_height=getattr(self.config, 'IMPRINT_LINE_SPACING', 1.2),
            )
        return self._font_style
    
    @font_style.setter
    def font_style(self, value):
        self._font_style = value

    def process_page(self, page: Page, project: Project, progress_callback: Optional[Callable] = None) -> Page:
        """Process a single page through detection → OCR → translation → inpainting → imprint."""
        def _emit(msg: str, val: Optional[int] = None):
            if progress_callback:
                try:
                    progress_callback(msg, val)
                except TypeError:
                    try:
                        progress_callback(msg)
                    except Exception:
                        pass
                except Exception:
                    pass

        # ---------------------------------------------------------------------
        # Stage 1 – Detection
        # ---------------------------------------------------------------------
        logger.info(f"[1/5] Detecting text in {page.file_path}")
        _emit(f"[1/5] Detecting text in {getattr(page.file_path, 'name', page.file_path)}", 20)
        image = load_image(page.file_path)
        raw_bubbles = self.detector.detect(image, ignore_sfx=project.settings.get("ignore_sfx", True))
        bubbles = []
        for b in raw_bubbles:
            if isinstance(b, TextBubble):
                bubbles.append(b)
            elif isinstance(b, (list, tuple)) and len(b) == 4:
                bubbles.append(TextBubble(bbox=list(b), status="detected"))
            elif hasattr(b, 'bbox'):
                bubbles.append(b)
        if not bubbles and page.bubbles:
            bubbles = page.bubbles

        # ---------------------------------------------------------------------
        # Stage 2 – OCR
        # ---------------------------------------------------------------------
        logger.info(f"[2/5] Performing OCR on {len(bubbles)} bubbles")
        _emit(f"[2/5] Performing OCR on {len(bubbles)} bubbles", 40)
        stage_errors = []
        for bubble in bubbles:
            try:
                text = self.ocr.recognize(image, bubble.bbox)
                if text and text.strip():
                    bubble.text_original = text.strip()
                    bubble.confidence = self.ocr.confidence
                    bubble.status = "ocr_done"
                else:
                    bubble.text_original = ""
                    bubble.confidence = 0.0
                    bubble.status = "ocr_empty"
            except Exception as e:
                err_msg = f"OCR failed for bubble {bubble.id}: {e}"
                logger.error(err_msg)
                stage_errors.append(err_msg)
                bubble.text_original = ""
                bubble.confidence = 0.0
                bubble.status = "failed"

        # ---------------------------------------------------------------------
        # Stage 3 – Translation
        # ---------------------------------------------------------------------
        ready_bubbles = [b for b in bubbles if b.status == "ocr_done" and b.text_original]
        logger.info(f"[3/5] Translating {len(ready_bubbles)} text blocks")
        _emit(f"[3/5] Translating {len(ready_bubbles)} text blocks", 60)
        for bubble in bubbles:
            if bubble.status == "ocr_done" and bubble.text_original:
                try:
                    bubble.text_translated = self.translator.translate(
                        bubble.text_original,
                        context=f"Comic page from {project.name}",
                    )
                    bubble.status = "translated"
                except Exception as e:
                    err_msg = f"Translation failed for bubble {bubble.id}: {e}"
                    logger.error(err_msg)
                    stage_errors.append(err_msg)
                    bubble.status = "failed"
                    bubble.text_translated = None

        # ---------------------------------------------------------------------
        # Style Analysis (Before Inpainting)
        # ---------------------------------------------------------------------
        if self.enable_imprint and getattr(self.config, 'AUTO_STYLE', False):
            logger.info("Analyzing text style from original image...")
            try:
                self.font_style = self.imprinter.analyze_style(image, bubbles)
            except Exception as e:
                logger.error(f"Style analysis failed: {e}")

        # ---------------------------------------------------------------------
        # Stage 4 – Inpainting (batch)
        # ---------------------------------------------------------------------
        logger.info("[4/5] Inpainting text regions (batch)")
        _emit("[4/5] Inpainting text regions", 80)
        # Gather valid bboxes. When imprinting, only inpaint bubbles that successfully translated
        # so we don't erase text that we can't re-render. Never inpaint failed bubbles.
        if self.enable_imprint:
            bboxes = [b.bbox for b in bubbles if b.status == "translated" and b.bbox and len(b.bbox) == 4]
        else:
            bboxes = [b.bbox for b in bubbles if b.status not in ("failed", "ocr_empty") and b.bbox and len(b.bbox) == 4]
        inpainted_image = image.copy()
        inpainting_failed = False
        if bboxes:
            try:
                inpainted_image = self.inpainter.inpaint_multiple(inpainted_image, bboxes)
            except Exception as e:
                err_msg = f"Inpainting failed: {e}"
                logger.error(err_msg)
                stage_errors.append(err_msg)
                inpainted_image = image.copy()  # Preserve original source artwork
                inpainting_failed = True
        else:
            logger.info("No valid bubbles to inpaint")

        # ---------------------------------------------------------------------
        # Stage 5 – Text Imprinting
        # ---------------------------------------------------------------------
        final_image = inpainted_image
        imprinting_failed = False
        
        if self.enable_imprint:
            if inpainting_failed:
                err_msg = "Imprinting skipped because inpainting failed; preserving original artwork"
                logger.warning(err_msg)
                final_image = image.copy()
            else:
                logger.info("[5/5] Imprinting translated text")
                _emit("[5/5] Imprinting translated text", 95)
                translated_bubbles = [b for b in bubbles if b.status == "translated" and b.text_translated]
                
                if translated_bubbles:
                    try:
                        # Apply box expansion if configured
                        if self.box_expansion != 0:
                            for b in translated_bubbles:
                                x1, y1, x2, y2 = b.bbox
                                b.bbox = [
                                    max(0, x1 - self.box_expansion),
                                    max(0, y1 - self.box_expansion),
                                    min(image.shape[1], x2 + self.box_expansion),
                                    min(image.shape[0], y2 + self.box_expansion)
                                ]
                        
                        final_image = self.imprinter.imprint(
                            inpainted_image, 
                            translated_bubbles, 
                            self.font_style,
                            auto_fit=True,
                            use_elliptical_wrapping=self.shape_wrapping
                        )
                        logger.info(f"Imprinted {len(translated_bubbles)} text bubbles")
                    except Exception as e:
                        err_msg = f"Text imprinting failed: {e}"
                        logger.error(err_msg)
                        stage_errors.append(err_msg)
                        final_image = image.copy()  # Restore original source artwork so erased-but-unlettered page is not exported
                        imprinting_failed = True
                else:
                    logger.info("No translated bubbles to imprint")
        else:
            logger.info("[5/5] Imprinting disabled, skipping")

        # Attach bubbles to the page and update outcome metrics
        page.bubbles = bubbles
        failed_bubbles = [b for b in bubbles if b.status == "failed"]
        translated_bubbles = [b for b in bubbles if b.status == "translated"]
        empty_bubbles = [b for b in bubbles if b.status == "ocr_empty"]

        page.total_bubbles_count = len(bubbles)
        page.translated_bubbles_count = len(translated_bubbles)
        page.failed_bubbles_count = len(failed_bubbles)
        page.empty_bubbles_count = len(empty_bubbles)
        page.error_details = stage_errors

        if inpainting_failed or imprinting_failed:
            page.status = "failed"
            page.error = "; ".join(stage_errors)
            page.processed_image_path = None
        elif len(bubbles) > 0 and len(failed_bubbles) == len(bubbles):
            page.status = "failed"
            page.error = "; ".join(stage_errors) if stage_errors else "All bubbles failed processing"
            page.processed_image_path = None
        elif len(failed_bubbles) > 0:
            page.status = "partial"
            page.error = "; ".join(stage_errors)
            output_suffix = "_translated" if self.enable_imprint else "_inpainted"
            page.processed_image_path = Path(page.file_path).parent / f"{page.id}{output_suffix}.png"
            save_image(final_image, page.processed_image_path)
        else:
            page.status = "success"
            page.error = None
            output_suffix = "_translated" if self.enable_imprint else "_inpainted"
            page.processed_image_path = Path(page.file_path).parent / f"{page.id}{output_suffix}.png"
            save_image(final_image, page.processed_image_path)

        _emit("Processing complete", 100)
        return page

# Backward compatibility alias
TranslationPipeline = ScanlationPipeline
