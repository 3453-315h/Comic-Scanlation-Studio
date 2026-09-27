import pytest
from unittest.mock import MagicMock
from pathlib import Path
import numpy as np

from src.core.pipeline import TranslationPipeline
from src.core.project import Project, Page, TextBubble
from src.gui.workers import WorkerThread

def test_pipeline_process_page_progress_callbacks():
    """Verify process_page accepts progress_callback and emits stage progress."""
    pipeline = TranslationPipeline()
    
    # Stub stages so no models are downloaded
    pipeline.detector = MagicMock()
    pipeline.detector.detect.return_value = [[10, 10, 50, 50]]
    
    pipeline.ocr = MagicMock()
    pipeline.ocr.recognize.return_value = "こんにちは"
    pipeline.ocr.confidence = 0.95
    
    pipeline.translator = MagicMock()
    pipeline.translator.translate.return_value = "Hello"
    
    pipeline.inpainter = MagicMock()
    pipeline.inpainter.inpaint_multiple.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
    
    pipeline.imprinter = MagicMock()
    pipeline.imprinter.imprint.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
    
    # Stub load_image
    pipeline_process_page = pipeline.process_page
    
    project = Project("TestProject")
    
    # Create a dummy image
    import tempfile, cv2
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        cv2.imwrite(str(tmp_path), img)
        
    try:
        page = project.add_page(tmp_path)
        
        progress_events = []
        def progress_cb(msg, pct):
            progress_events.append((msg, pct))
            
        processed_page = pipeline.process_page(page, project, progress_callback=progress_cb)
        
        assert processed_page is not None
        assert processed_page.id == page.id
        assert len(progress_events) >= 5
        pcts = [p[1] for p in progress_events]
        assert 20 in pcts
        assert 40 in pcts
        assert 60 in pcts
        assert 80 in pcts
        assert 100 in pcts
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

def test_gui_worker_invocation_with_stub_pipeline(qapp):
    """Test GUI worker invocation with a stub pipeline returns processed page."""
    import tempfile, cv2
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        cv2.imwrite(str(tmp_path), np.zeros((100, 100, 3), dtype=np.uint8))
        
    try:
        project = Project("TestProject")
        page = project.add_page(tmp_path)
        
        pipeline = TranslationPipeline()
        pipeline.detector = MagicMock()
        pipeline.detector.detect.return_value = []
        pipeline.ocr = MagicMock()
        pipeline.translator = MagicMock()
        pipeline.inpainter = MagicMock()
        pipeline.renderer = MagicMock()
        
        # Test calling pipeline.process_page via WorkerThread signature matching
        worker = WorkerThread(pipeline.process_page, page, project)
        results = []
        progress_list = []
        worker.signals.result.connect(lambda r: results.append(r))
        worker.signals.progress.connect(lambda p: progress_list.append(p))
        
        worker.run()
        
        assert len(results) == 1
        assert results[0].id == page.id
    finally:
        if tmp_path.exists():
            tmp_path.unlink()
