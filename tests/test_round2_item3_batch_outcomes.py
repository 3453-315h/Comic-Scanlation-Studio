import pytest
import numpy as np
import cv2
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.core.project import Project, Page, TextBubble
from src.core.pipeline import ScanlationPipeline
from src.core.batch_processor import BatchProcessor, BatchResult, PageOutcome
from src.gui.main_window import MainWindow


def _setup_test_pages(tmp_path):
    project = Project("BatchOutcomeTest")
    
    # Page 1: All success
    img1 = tmp_path / "page1.png"
    cv2.imwrite(str(img1), np.zeros((100, 100, 3), dtype=np.uint8))
    p1 = project.add_page(img1)
    p1.bubbles = [TextBubble(id="b1", bbox=[10, 10, 30, 30], text_original="Hi", text_translated="Hello", status="translated")]
    p1.status = "success"

    # Page 2: Partial (1 translated, 1 failed)
    img2 = tmp_path / "page2.png"
    cv2.imwrite(str(img2), np.zeros((100, 100, 3), dtype=np.uint8))
    p2 = project.add_page(img2)
    p2.bubbles = [
        TextBubble(id="b2_good", bbox=[10, 10, 30, 30], text_original="Good", text_translated="Bien", status="translated"),
        TextBubble(id="b2_bad", bbox=[40, 40, 60, 60], text_original="Bad", text_translated=None, status="failed")
    ]
    p2.status = "partial"
    p2.failed_bubbles_count = 1
    p2.translated_bubbles_count = 1
    p2.error_details = ["Translation API timeout on b2_bad"]

    # Page 3: Complete bubble failure
    img3 = tmp_path / "page3.png"
    cv2.imwrite(str(img3), np.zeros((100, 100, 3), dtype=np.uint8))
    p3 = project.add_page(img3)
    p3.bubbles = [TextBubble(id="b3", bbox=[10, 10, 30, 30], text_original="Err", text_translated=None, status="failed")]
    p3.status = "failed"
    p3.failed_bubbles_count = 1
    p3.error = "All bubbles failed"

    # Page 4: Unhandled exception during processing
    img4 = tmp_path / "page4.png"
    cv2.imwrite(str(img4), np.zeros((100, 100, 3), dtype=np.uint8))
    p4 = project.add_page(img4)

    return project, [p1, p2, p3, p4]


def test_batch_processor_sequential_mixed_outcomes(tmp_path):
    """Sequential batch processing preserves page outcomes, counting successes, partials, and failures."""
    project, pages = _setup_test_pages(tmp_path)
    p1, p2, p3, p4 = pages

    pipeline = MagicMock(spec=ScanlationPipeline)
    def mock_process_page(page, proj):
        if page.id == p4.id:
            raise RuntimeError("Corrupted image stream on page 4")
        return page

    pipeline.process_page.side_effect = mock_process_page
    processor = BatchProcessor(pipeline)

    results = processor.process_pages([p1, p2, p3, p4], project)
    assert isinstance(results, BatchResult)
    assert results.total_count == 4
    assert results.success_count == 1
    assert results.partial_count == 1
    assert results.failure_count == 2

    # Check page-level outcome preservation
    res_p1 = next(p for p in results if p.id == p1.id)
    res_p2 = next(p for p in results if p.id == p2.id)
    res_p3 = next(p for p in results if p.id == p3.id)
    res_p4 = next(p for p in results if p.id == p4.id)

    assert res_p1.status == "success"
    assert res_p2.status == "partial"
    assert res_p2.bubbles[0].status == "translated"
    assert res_p2.bubbles[1].status == "failed"

    assert res_p3.status == "failed"
    assert res_p4.status == "failed"
    assert "Corrupted image stream" in res_p4.error


def test_batch_processor_parallel_mixed_outcomes(tmp_path):
    """Parallel batch processing carries identical page outcome contract as sequential mode."""
    project, pages = _setup_test_pages(tmp_path)
    p1, p2, p3, p4 = pages

    pipeline = MagicMock(spec=ScanlationPipeline)
    pipeline.config = MagicMock()

    def mock_process_page(page, proj):
        if page.id == p4.id:
            raise RuntimeError("Corrupted image stream on page 4")
        return page

    with patch("src.core.batch_processor.ScanlationPipeline", return_value=pipeline):
        pipeline.process_page.side_effect = mock_process_page
        processor = BatchProcessor(pipeline)
        results = processor.process_pages_parallel([p1, p2, p3, p4], project, max_workers=2)

        assert isinstance(results, BatchResult)
        assert results.total_count == 4
        assert results.success_count == 1
        assert results.partial_count == 1
        assert results.failure_count == 2


def test_batch_dialog_summary_with_mixed_outcomes(qapp, tmp_path):
    """UI _on_batch_complete displays accurate counts for succeeded, partial, and failed pages."""
    project, pages = _setup_test_pages(tmp_path)
    window = MainWindow()
    window.project = project
    window._load_page = MagicMock()
    project.save = MagicMock()

    outcomes = {
        pages[0].id: PageOutcome(page_id=pages[0].id, status="success"),
        pages[1].id: PageOutcome(page_id=pages[1].id, status="partial"),
        pages[2].id: PageOutcome(page_id=pages[2].id, status="failed", error="All bubbles failed"),
        pages[3].id: PageOutcome(page_id=pages[3].id, status="failed", error="Crash"),
    }
    batch_result = BatchResult(pages, outcomes)

    with patch("PySide6.QtWidgets.QMessageBox.warning") as mock_warn:
        window._on_batch_complete(batch_result)
        mock_warn.assert_called_once()
        warning_msg = mock_warn.call_args[0][2]
        assert "1 succeeded" in warning_msg
        assert "1 partial" in warning_msg
        assert "2 failed" in warning_msg
        assert "1/4 succeeded, 1 partial, 2 failed" in window.statusbar.currentMessage()

    window.close()
