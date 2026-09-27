import pytest
import numpy as np
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.core.project import Project, Page, TextBubble
from src.core.pipeline import TranslationPipeline
from src.modules.ocr import OCREngineUnavailableError, OCRError
from src.modules.translator import TranslationBackendError
from src.gui.main_window import MainWindow


def test_pipeline_tracks_bubble_counts_and_preserves_failures(tmp_path):
    """Pipeline tracks failed, empty, and translated bubble counts, setting 'partial' outcome and preserving failed pixels."""
    import cv2
    img_path = tmp_path / "page.png"
    cv2.imwrite(str(img_path), np.zeros((100, 100, 3), dtype=np.uint8))

    project = Project("Item4Test")
    page = project.add_page(img_path)

    # 4 distinct bubble scenarios:
    # 1. Normal success: OCR succeeds, translation succeeds -> 'translated'
    # 2. Genuinely empty: OCR returns empty string -> 'ocr_empty', skipped from translation
    # 3. OCR engine error: OCR raises exception -> 'failed', reason tracked
    # 4. Translation error: OCR succeeds, translation raises exception -> 'failed', reason tracked
    b1 = TextBubble(id="b1", bbox=[10, 10, 20, 20])
    b2 = TextBubble(id="b2", bbox=[30, 30, 40, 40])
    b3 = TextBubble(id="b3", bbox=[50, 50, 60, 60])
    b4 = TextBubble(id="b4", bbox=[70, 70, 80, 80])
    page.bubbles = [b1, b2, b3, b4]

    pipeline = TranslationPipeline()
    pipeline.detector = MagicMock()
    pipeline.detector.detect.return_value = page.bubbles

    def mock_ocr(img, bbox):
        if bbox == [10, 10, 20, 20]:
            return "こんにちは"
        elif bbox == [30, 30, 40, 40]:
            return ""  # Empty OCR
        elif bbox == [50, 50, 60, 60]:
            raise OCREngineUnavailableError("Tesseract engine not found")
        elif bbox == [70, 70, 80, 80]:
            return "さようなら"
        return ""

    pipeline.ocr = MagicMock()
    pipeline.ocr.recognize.side_effect = mock_ocr
    pipeline.ocr.confidence = 0.95

    def mock_translate(text, context=None):
        if text == "こんにちは":
            return "Hello"
        elif text == "さようなら":
            raise TranslationBackendError("DeepL quota exceeded")
        return text

    pipeline.translator = MagicMock()
    pipeline.translator.translate.side_effect = mock_translate

    pipeline.inpainter = MagicMock()
    pipeline.inpainter.inpaint_multiple.return_value = np.zeros((100, 100, 3), dtype=np.uint8)

    pipeline.imprinter = MagicMock()
    pipeline.imprinter.imprint.return_value = np.zeros((100, 100, 3), dtype=np.uint8)

    processed = pipeline.process_page(page, project)

    # Assert bubble statuses
    res1 = next(b for b in processed.bubbles if b.id == "b1")
    res2 = next(b for b in processed.bubbles if b.id == "b2")
    res3 = next(b for b in processed.bubbles if b.id == "b3")
    res4 = next(b for b in processed.bubbles if b.id == "b4")

    assert res1.status == "translated"
    assert res1.text_translated == "Hello"

    assert res2.status == "ocr_empty"
    assert res2.text_translated == ""

    assert res3.status == "failed"
    assert not res3.text_translated

    assert res4.status == "failed"
    assert not res4.text_translated

    # Assert outcome metrics on page
    assert processed.total_bubbles_count == 4
    assert processed.translated_bubbles_count == 1
    assert processed.empty_bubbles_count == 1
    assert processed.failed_bubbles_count == 2
    assert processed.status == "partial"
    assert any("Tesseract engine not found" in err for err in processed.error_details)
    assert any("DeepL quota exceeded" in err for err in processed.error_details)

    # Inpainting and imprinting must ONLY receive b1
    pipeline.inpainter.inpaint_multiple.assert_called_once()
    inpaint_boxes = pipeline.inpainter.inpaint_multiple.call_args[0][1]
    assert len(inpaint_boxes) == 1
    assert inpaint_boxes[0] == [10, 10, 20, 20]

    pipeline.imprinter.imprint.assert_called_once()
    imprinted_bubbles = pipeline.imprinter.imprint.call_args[0][1]
    assert len(imprinted_bubbles) == 1
    assert imprinted_bubbles[0].id == "b1"


def test_all_bubbles_failed_pipeline_status(tmp_path):
    """When all bubbles fail, page status is 'failed' and no inpainting is attempted."""
    import cv2
    img_path = tmp_path / "page_fail.png"
    cv2.imwrite(str(img_path), np.zeros((100, 100, 3), dtype=np.uint8))

    project = Project("FailTest")
    page = project.add_page(img_path)
    page.bubbles = [TextBubble(id="bf", bbox=[10, 10, 20, 20])]

    pipeline = TranslationPipeline()
    pipeline.detector = MagicMock()
    pipeline.detector.detect.return_value = page.bubbles
    pipeline.ocr = MagicMock()
    pipeline.ocr.recognize.side_effect = OCRError("Corrupt region")
    pipeline.inpainter = MagicMock()

    processed = pipeline.process_page(page, project)

    assert processed.status == "failed"
    assert processed.failed_bubbles_count == 1
    assert processed.translated_bubbles_count == 0
    pipeline.inpainter.inpaint_multiple.assert_not_called()


def test_unchanged_valid_translation_is_treated_as_successful(tmp_path):
    """An unchanged valid translation (e.g. proper noun 'Tokyo' -> 'Tokyo') is translated, not failed."""
    import cv2
    img_path = tmp_path / "page_unchanged.png"
    cv2.imwrite(str(img_path), np.zeros((100, 100, 3), dtype=np.uint8))

    project = Project("UnchangedTest")
    page = project.add_page(img_path)
    page.bubbles = [TextBubble(id="b_tokyo", bbox=[10, 10, 20, 20])]

    pipeline = TranslationPipeline()
    pipeline.detector = MagicMock()
    pipeline.detector.detect.return_value = page.bubbles
    pipeline.ocr = MagicMock()
    pipeline.ocr.recognize.return_value = "Tokyo"
    pipeline.ocr.confidence = 0.99
    pipeline.translator = MagicMock()
    pipeline.translator.translate.return_value = "Tokyo"
    pipeline.inpainter = MagicMock()
    pipeline.inpainter.inpaint_multiple.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
    pipeline.imprinter = MagicMock()
    pipeline.imprinter.imprint.return_value = np.zeros((100, 100, 3), dtype=np.uint8)

    processed = pipeline.process_page(page, project)

    assert processed.status == "success"
    assert processed.translated_bubbles_count == 1
    assert processed.failed_bubbles_count == 0
    assert processed.bubbles[0].status == "translated"
    assert processed.bubbles[0].text_translated == "Tokyo"
    pipeline.inpainter.inpaint_multiple.assert_called_once()


def test_ui_process_all_surfaces_partial_and_failed_verdicts(qapp, tmp_path):
    """MainWindow._on_process_all_complete shows warning/critical dialog and accurate failure text for partial and failed pages."""
    import cv2
    img_path = tmp_path / "page.png"
    cv2.imwrite(str(img_path), np.zeros((100, 100, 3), dtype=np.uint8))

    window = MainWindow()
    project = Project("UITest")
    page = project.add_page(img_path)
    window.project = project
    window.image_viewer.current_page = page

    # 1. Test Partial page completion
    page.status = "partial"
    page.translated_bubbles_count = 1
    page.failed_bubbles_count = 1
    page.error_details = ["DeepL API 429 Too Many Requests"]

    with patch("PySide6.QtWidgets.QMessageBox.warning") as mock_warn, \
         patch("PySide6.QtWidgets.QMessageBox.critical") as mock_crit:
        window._on_process_all_complete(page)
        
        mock_warn.assert_called_once()
        mock_crit.assert_not_called()
        warn_args = mock_warn.call_args[0]
        assert "Process All Partial" in warn_args[1]
        assert "1 translated, 1 failed (DeepL API 429 Too Many Requests)" in warn_args[2]

        # Verify status text did not claim complete success
        status_text = window.editor_panel.status_label.text()
        assert "partial" in status_text.lower()
        assert "All stages complete!" not in status_text

    # 2. Test Failed page completion
    page.status = "failed"
    page.translated_bubbles_count = 0
    page.failed_bubbles_count = 2
    page.error_details = ["OCR engine unavailable"]

    with patch("PySide6.QtWidgets.QMessageBox.warning") as mock_warn, \
         patch("PySide6.QtWidgets.QMessageBox.critical") as mock_crit:
        window._on_process_all_complete(page)

        mock_crit.assert_called_once()
        mock_warn.assert_not_called()
        crit_args = mock_crit.call_args[0]
        assert "Process All Failed" in crit_args[1]
        assert "OCR engine unavailable" in crit_args[2]

    window.close()


def test_ui_manual_ocr_and_translate_surface_failure_reasons(qapp, tmp_path):
    """Manual OCR and Translation operations surface failure reasons without claiming success."""
    import cv2
    img_path = tmp_path / "page.png"
    cv2.imwrite(str(img_path), np.zeros((100, 100, 3), dtype=np.uint8))

    window = MainWindow()
    project = Project("ManualTest")
    page = project.add_page(img_path)
    b0 = TextBubble(id="b0", bbox=[0, 0, 10, 10])
    b1 = TextBubble(id="b1", bbox=[10, 10, 20, 20])
    page.bubbles = [b0, b1]
    window.project = project
    window.image_viewer.current_page = page

    # 1. OCR with 1 failure and 1 success
    ocr_data = {
        "results": {"b0": ("Extracted text", 0.9)},
        "errors": {"b1": "TesseractNotFound"}
    }

    with patch("PySide6.QtWidgets.QMessageBox.warning") as mock_warn, \
         patch.object(window, "open_text_editor"):
        window._on_ocr_complete(ocr_data)
        mock_warn.assert_called_once()
        warn_args = mock_warn.call_args[0]
        assert "OCR Errors" in warn_args[1]
        assert "TesseractNotFound" in warn_args[2]

        status = window.editor_panel.status_label.text()
        assert "failures: 1 texts extracted, 1 failed (TesseractNotFound)" in status

    # 2. Translation with 1 failure and 1 success
    trans_data = {
        "results": {"b0": "Translated text"},
        "errors": {"b1": "NetworkTimeout"}
    }

    with patch("PySide6.QtWidgets.QMessageBox.warning") as mock_warn:
        window._on_translation_complete(trans_data)
        mock_warn.assert_called_once()
        warn_args = mock_warn.call_args[0]
        assert "Translation Errors" in warn_args[1]
        assert "NetworkTimeout" in warn_args[2]

        status = window.editor_panel.status_label.text()
        assert "failures: 1 translated, 1 failed (NetworkTimeout)" in status

    window.close()
