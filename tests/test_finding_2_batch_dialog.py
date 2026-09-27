import pytest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import Qt

from src.core.project import Project, Page
from src.gui.dialogs.batch_dialog import BatchProcessDialog

def test_batch_dialog_loads_pages_from_dict(qapp):
    """Test dialog construction with project.pages as a dict of Page objects."""
    project = Project("BatchTest")
    p1 = project.add_page(Path("/dummy/path/page1.png"))
    p2 = project.add_page(Path("/dummy/path/page2.png"))
    p3 = project.add_page(Path("/dummy/path/page3.png"))
    
    assert isinstance(project.pages, dict)
    
    dialog = BatchProcessDialog(project)
    assert dialog.page_list.count() == 3
    
    # By default, all are selected
    selected = dialog.page_list.selectedItems()
    assert len(selected) == 3
    
    config = dialog.get_config()
    assert len(config["pages"]) == 3
    assert all(isinstance(p, Page) for p in config["pages"])
    assert [p.id for p in config["pages"]] == [p1.id, p2.id, p3.id]

def test_batch_dialog_selection_modes(qapp):
    """Test select all, select none, and partial selection."""
    project = Project("BatchTest")
    p1 = project.add_page(Path("/dummy/path/page1.png"))
    p2 = project.add_page(Path("/dummy/path/page2.png"))
    
    dialog = BatchProcessDialog(project)
    
    # Select none
    dialog.select_none()
    assert len(dialog.page_list.selectedItems()) == 0
    
    # Select all
    dialog.select_all()
    assert len(dialog.page_list.selectedItems()) == 2
    
    # Select only page 2
    dialog.select_none()
    dialog.page_list.item(1).setSelected(True)
    
    # Trigger run_process
    with patch.object(dialog, 'accept'):
        dialog.run_process()
        assert hasattr(dialog, 'pages_to_process')
        assert len(dialog.pages_to_process) == 1
        assert dialog.pages_to_process[0].id == p2.id
        assert isinstance(dialog.pages_to_process[0], Page)

def test_batch_dialog_no_selection_warning(qapp):
    """Test warning dialog when run_process is called with no pages selected."""
    project = Project("BatchTest")
    project.add_page(Path("/dummy/path/page1.png"))
    
    dialog = BatchProcessDialog(project)
    dialog.select_none()
    
    with patch("PySide6.QtWidgets.QMessageBox.warning") as mock_warn:
        dialog.run_process()
        mock_warn.assert_called_once()
        assert not hasattr(dialog, 'pages_to_process') or not dialog.pages_to_process
