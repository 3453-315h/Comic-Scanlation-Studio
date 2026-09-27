import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.gui.main_window import MainWindow
from src.core.project import Project, Page

def test_batch_complete_with_current_page(qapp):
    """Test batch completion refresh when image_viewer has a current page."""
    window = MainWindow()
    project = Project("BatchCompletionTest")
    p1 = project.add_page(Path("/dummy/path/p1.png"))
    p2 = project.add_page(Path("/dummy/path/p2.png"))
    window.project = project
    
    # Mock current page on image viewer
    window.image_viewer.current_page = p1
    
    # Mock _load_page and save
    window._load_page = MagicMock()
    project.save = MagicMock()
    
    # Simulate batch results with 1 success, 1 failure
    res_p1 = Page(id=p1.id, file_path=p1.file_path)
    res_p2 = Page(id=p2.id, file_path=p2.file_path)
    setattr(res_p2, 'status', 'failed')
    results = [res_p1, res_p2]
    
    with patch("PySide6.QtWidgets.QMessageBox.warning") as mock_warn:
        window._on_batch_complete(results)
        
        # Verify _load_page was called with p1
        window._load_page.assert_called_once()
        assert window._load_page.call_args[0][0].id == p1.id
        
        # Verify status messages show 1 succeeded, 1 failed
        assert "1/2 succeeded" in window.statusbar.currentMessage()
        assert "1 failed" in window.statusbar.currentMessage()
        
        # Verify warning dialog popped up because of 1 failure
        mock_warn.assert_called_once()
    
    window.close()

def test_batch_complete_with_no_current_page(qapp):
    """Test batch completion when no current page is loaded."""
    window = MainWindow()
    project = Project("BatchCompletionTest2")
    p1 = project.add_page(Path("/dummy/path/p1.png"))
    window.project = project
    
    window.image_viewer.current_page = None
    window._load_page = MagicMock()
    project.save = MagicMock()
    
    results = [Page(id=p1.id, file_path=p1.file_path)]
    
    with patch("PySide6.QtWidgets.QMessageBox.information") as mock_info:
        window._on_batch_complete(results)
        
        # _load_page should not be called since current_page is None
        window._load_page.assert_not_called()
        
        # Verify status message shows 1/1 succeeded
        assert "1/1 succeeded" in window.statusbar.currentMessage()
        mock_info.assert_called_once()
        
    window.close()
