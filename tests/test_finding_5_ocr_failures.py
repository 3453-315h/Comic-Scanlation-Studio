import pytest
import numpy as np
from pathlib import Path
from unittest.mock import MagicMock

from src.modules.ocr import MangaOCR, EasyOCR, OCREngineUnavailableError, OCRError
from src.core.pipeline import TranslationPipeline
from src.core.project import Project, Page, TextBubble

def test_ocr_reader_none_raises_engine_unavailable():
    """Uninitialized OCR engine must raise OCREngineUnavailableError loudly, not placeholder text."""
    manga_ocr = MangaOCR()
    manga_ocr.reader = None
    
    img = np.zeros((50, 50, 3), dtype=np.uint8)
    with pytest.raises(OCREngineUnavailableError):
        manga_ocr.recognize(img)

    easy_ocr = EasyOCR()
    easy_ocr.reader = None
    with pytest.raises(OCREngineUnavailableError):
        easy_ocr.recognize(img)

def test_ocr_failure_does_not_become_printable_text():
    """OCR failure must not generate 'OCR engine not loaded' as valid text."""
    manga_ocr = MangaOCR()
    manga_ocr.reader = MagicMock()
    manga_ocr.reader.side_effect = RuntimeError("GPU memory exhausted")
    
    img = np.zeros((50, 50, 3), dtype=np.uint8)
    with pytest.raises(OCRError):
        manga_ocr.recognize(img)

def test_pipeline_handles_ocr_failure_and_empty_without_inpainting(tmp_path):
    """Pipeline must mark failed/empty OCR appropriately and NEVER send them to inpainting."""
    import cv2
    img_path = tmp_path / "page.png"
    cv2.imwrite(str(img_path), np.zeros((100, 100, 3), dtype=np.uint8))
    
    project = Project("OCRTest")
    page = project.add_page(img_path)
    
    # 3 bubbles:
    # 1. Successful OCR
    # 2. Empty OCR (no text extracted)
    # 3. Failed OCR (exception raised)
    b1 = TextBubble(id="b1", bbox=[10, 10, 30, 30])
    b2 = TextBubble(id="b2", bbox=[40, 40, 60, 60])
    b3 = TextBubble(id="b3", bbox=[70, 70, 90, 90])
    page.bubbles = [b1, b2, b3]
    
    pipeline = TranslationPipeline()
    # Stub detector to keep page bubbles
    pipeline.detector = MagicMock()
    pipeline.detector.detect.return_value = page.bubbles
    
    # Mock OCR
    def mock_ocr(image, bbox):
        if bbox == [10, 10, 30, 30]:
            return "おはよう"
        elif bbox == [40, 40, 60, 60]:
            return "   "  # Empty whitespace
        else:
            raise OCRError("Corrupt region")
            
    pipeline.ocr = MagicMock()
    pipeline.ocr.recognize.side_effect = mock_ocr
    pipeline.ocr.confidence = 0.9
    
    # Mock translator
    pipeline.translator = MagicMock()
    pipeline.translator.translate.return_value = "Good morning"
    
    # Mock inpainter
    pipeline.inpainter = MagicMock()
    pipeline.inpainter.inpaint_multiple.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
    
    # Mock imprinter
    pipeline.imprinter = MagicMock()
    pipeline.imprinter.imprint.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
    
    processed_page = pipeline.process_page(page, project)
    
    # Verify bubble statuses
    b1_res = next(b for b in processed_page.bubbles if b.id == "b1")
    b2_res = next(b for b in processed_page.bubbles if b.id == "b2")
    b3_res = next(b for b in processed_page.bubbles if b.id == "b3")
    
    assert b1_res.status == "translated"
    assert b1_res.text_translated == "Good morning"
    
    assert b2_res.status == "ocr_empty"
    assert b2_res.text_translated == ""
    
    assert b3_res.status == "failed"
    assert b3_res.text_translated == ""
    
    # Verify inpainting was ONLY called for b1
    pipeline.inpainter.inpaint_multiple.assert_called_once()
    inpainted_bboxes = pipeline.inpainter.inpaint_multiple.call_args[0][1]
    assert len(inpainted_bboxes) == 1
    assert inpainted_bboxes[0] == [10, 10, 30, 30]
