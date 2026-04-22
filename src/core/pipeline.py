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

from .project import Project, Page
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

    def __init__(self, config):
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

    def process_page(self, page: Page, project: Project) -> Page:
        """Process a single page through detection → OCR → translation → inpainting → imprint."""
        # ---------------------------------------------------------------------
        # Stage 1 – Detection
        # ---------------------------------------------------------------------
        logger.info(f"[1/5] Detecting text in {page.file_path}")
        image = load_image(page.file_path)
        bubbles = self.detector.detect(image, ignore_sfx=project.settings.get("ignore_sfx", True))

        # ---------------------------------------------------------------------
        # Stage 2 – OCR
        # ---------------------------------------------------------------------
        logger.info(f"[2/5] Performing OCR on {len(bubbles)} bubbles")
        for bubble in bubbles:
            try:
                bubble.text_original = self.ocr.recognize(image, bubble.bbox)
                bubble.confidence = self.ocr.confidence
                bubble.status = "ocr_done"
            except Exception as e:
                logger.error(f"OCR failed for bubble {bubble.id}: {e}")
                bubble.status = "failed"

        # ---------------------------------------------------------------------
        # Stage 3 – Translation
        # ---------------------------------------------------------------------
        logger.info(f"[3/5] Translating {len(bubbles)} text blocks")
        for bubble in bubbles:
            if bubble.status == "ocr_done" and bubble.text_original:
                try:
                    bubble.text_translated = self.translator.translate(
                        bubble.text_original,
                        context=f"Comic page from {project.name}",
                    )
                    bubble.status = "translated"
                except Exception as e:
                    logger.error(f"Translation failed for bubble {bubble.id}: {e}")
                    bubble.status = "failed"

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
        # Gather valid bboxes. When imprinting, only inpaint bubbles that successfully translated
        # so we don't erase text that we can't re-render.
        if self.enable_imprint:
            bboxes = [b.bbox for b in bubbles if b.status == "translated" and b.bbox and len(b.bbox) == 4]
        else:
            bboxes = [b.bbox for b in bubbles if b.bbox and len(b.bbox) == 4]
        inpainted_image = image.copy()
        if bboxes:
            try:
                inpainted_image = self.inpainter.inpaint_multiple(inpainted_image, bboxes)
            except Exception as e:
                logger.error(f"Batch inpainting failed: {e}")
        else:
            logger.info("No valid bubbles to inpaint")

        # ---------------------------------------------------------------------
        # Stage 5 – Text Imprinting
        # ---------------------------------------------------------------------
        final_image = inpainted_image
        
        if self.enable_imprint:
            logger.info("[5/5] Imprinting translated text")
            translated_bubbles = [b for b in bubbles if b.status == "translated" and b.text_translated]
            
            if translated_bubbles:
                try:
                    # Optionally analyze style from original image
                    # Moved to before inpainting for safety
                    # if getattr(self.config, 'AUTO_STYLE', False):
                    #    self.font_style = self.imprinter.analyze_style(image, bubbles)
                    
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
                    logger.error(f"Text imprinting failed: {e}")
                    final_image = inpainted_image
            else:
                logger.info("No translated bubbles to imprint")
        else:
            logger.info("[5/5] Imprinting disabled, skipping")

        # Save the final image and update the page metadata
        output_suffix = "_translated" if self.enable_imprint else "_inpainted"
        page.processed_image_path = Path(page.file_path).parent / f"{page.id}{output_suffix}.png"
        save_image(final_image, page.processed_image_path)

        # Attach bubbles to the page and return
        page.bubbles = bubbles
        return page
