import pytest
import numpy as np
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.modules.translator import (
    Translator,
    TranslationBackendError,
    MissingCredentialsError,
    UnsupportedBackendError,
    TranslationError
)
from src.core.pipeline import TranslationPipeline
from src.core.project import Project, Page, TextBubble

def test_missing_credentials_raises_loudly():
    """Missing or empty API key must raise MissingCredentialsError loudly."""
    translator = Translator(backend="deepl")
    translator.api_key = ""
    
    with pytest.raises(MissingCredentialsError):
        translator.translate("Hello")

def test_unsupported_backend_raises_loudly():
    """Unsupported backend name must raise UnsupportedBackendError."""
    translator = Translator(backend="imaginary_backend")
    
    with pytest.raises(UnsupportedBackendError):
        translator.translate("Hello")

def test_network_error_raises_backend_error():
    """Network connection failure must raise TranslationBackendError, not return original text."""
    translator = Translator(backend="deepl")
    translator.api_key = "test"
    
    with patch("requests.Session.post", side_effect=Exception("Connection refused")):
        with pytest.raises(TranslationBackendError):
            translator.translate("テスト")

def test_identical_valid_translation_is_preserved_and_cached(tmp_path):
    """An authentic identical translation (e.g. proper noun 'Tokyo' -> 'Tokyo') is valid and marked translated."""
    translator = Translator(backend="offline", cache_file=tmp_path / "trans_cache.json")
    
    # Offline backend mock returning identical text
    with patch.object(translator, '_nllb_translate', return_value="Tokyo"):
        result = translator.translate("Tokyo")
        assert result == "Tokyo"
        
        # Verify it was added to cache
        cache_key = translator._get_cache_key("Tokyo", "ja", "en")
        assert cache_key in translator.cache

def test_pipeline_mixed_good_bad_translation_preserves_failed_source_pixels(tmp_path):
    """When some bubbles fail translation, only successfully translated bubbles are inpainted."""
    import cv2
    img_path = tmp_path / "page_trans.png"
    cv2.imwrite(str(img_path), np.zeros((100, 100, 3), dtype=np.uint8))
    
    project = Project("TransTest")
    page = project.add_page(img_path)
    
    b_good = TextBubble(id="b_good", bbox=[10, 10, 30, 30], text_original="こんにちは")
    b_bad = TextBubble(id="b_bad", bbox=[50, 50, 70, 70], text_original="エラーテキスト")
    page.bubbles = [b_good, b_bad]
    
    pipeline = TranslationPipeline()
    pipeline.detector = MagicMock()
    pipeline.detector.detect.return_value = page.bubbles
    
    # OCR succeeds for both
    pipeline.ocr = MagicMock()
    pipeline.ocr.recognize.side_effect = lambda img, bbox: "こんにちは" if bbox == [10, 10, 30, 30] else "エラーテキスト"
    pipeline.ocr.confidence = 0.9
    
    # Translator fails on b_bad
    def mock_translate(text, context=None):
        if text == "こんにちは":
            return "Hello"
        else:
            raise TranslationBackendError("DeepL quota exceeded")
            
    pipeline.translator = MagicMock()
    pipeline.translator.translate.side_effect = mock_translate
    
    pipeline.inpainter = MagicMock()
    pipeline.inpainter.inpaint_multiple.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
    pipeline.imprinter = MagicMock()
    pipeline.imprinter.imprint.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
    
    processed_page = pipeline.process_page(page, project)
    
    res_good = next(b for b in processed_page.bubbles if b.id == "b_good")
    res_bad = next(b for b in processed_page.bubbles if b.id == "b_bad")
    
    assert res_good.status == "translated"
    assert res_good.text_translated == "Hello"
    
    assert res_bad.status == "failed"
    assert not res_bad.text_translated
    
    # Inpainter must ONLY receive the bbox of b_good, preserving b_bad source pixels!
    pipeline.inpainter.inpaint_multiple.assert_called_once()
    inpainted_boxes = pipeline.inpainter.inpaint_multiple.call_args[0][1]
    assert len(inpainted_boxes) == 1
    assert inpainted_boxes[0] == [10, 10, 30, 30]
