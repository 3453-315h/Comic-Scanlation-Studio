import pytest
from unittest.mock import patch

from src.gui.main_window import MainWindow

def test_headless_qt_smoke(qapp):
    """Smoke test creating MainWindow in offscreen headless Qt environment."""
    window = MainWindow()
    assert window is not None
    assert "Comic Scanlation Studio" in window.windowTitle()
    
    # Check main widgets created
    assert window.image_viewer is not None
    assert window.editor_panel is not None
    assert window.page_carousel is not None
    assert window.statusbar is not None
    
    # Clean teardown
    window.close()
