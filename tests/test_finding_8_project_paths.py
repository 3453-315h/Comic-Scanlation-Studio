import pytest
import shutil
import json
from pathlib import Path

from src.core.project import Project, Page

def test_project_save_copies_external_images_and_uses_relative_paths(tmp_path):
    """External images should be copied into project_dir/pages and saved as relative paths."""
    external_dir = tmp_path / "external_source"
    external_dir.mkdir()
    ext_img = external_dir / "chapter1_001.png"
    ext_img.write_bytes(b"image data 1")
    
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()
    
    project = Project("PortableTest")
    page = project.add_page(ext_img)
    
    # Save project
    project.save(projects_dir)
    
    project_dir = projects_dir / project.id
    saved_json = project_dir / "project.json"
    assert saved_json.exists()
    
    with open(saved_json, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    pdata = data["pages"][page.id]
    rel_path = pdata["file_path"]
    
    # Must be a relative path!
    assert not Path(rel_path).is_absolute()
    assert "pages/" in rel_path
    
    # Verify the copied image exists in project_dir
    copied_img = project_dir / rel_path
    assert copied_img.exists()
    assert copied_img.read_bytes() == b"image data 1"

def test_source_deletion_resilience(tmp_path):
    """Project must remain intact and loadable even after original imported file is deleted."""
    external_dir = tmp_path / "external"
    external_dir.mkdir()
    ext_img = external_dir / "temp_page.png"
    ext_img.write_bytes(b"temporary external image")
    
    projects_dir = tmp_path / "projects"
    project = Project("DeleteSourceTest")
    page = project.add_page(ext_img)
    project.save(projects_dir)
    
    # Delete original source file
    ext_img.unlink()
    assert not ext_img.exists()
    
    # Load project from disk
    loaded = Project.load(projects_dir / project.id)
    loaded_page = loaded.pages[page.id]
    
    assert loaded_page.file_path.exists()
    assert loaded_page.file_path.read_bytes() == b"temporary external image"

def test_move_project_directory_portability(tmp_path):
    """Moving the entire project directory must not break page file paths."""
    projects_dir = tmp_path / "projects"
    project = Project("MoveTest")
    
    ext_img = tmp_path / "page_to_move.png"
    ext_img.write_bytes(b"content to move")
    page = project.add_page(ext_img)
    project.save(projects_dir)
    
    orig_project_dir = projects_dir / project.id
    new_location = tmp_path / "moved_location" / project.id
    new_location.parent.mkdir(parents=True)
    
    # Move directory
    shutil.move(str(orig_project_dir), str(new_location))
    
    # Load from new location
    loaded = Project.load(new_location)
    loaded_page = loaded.pages[page.id]
    
    assert loaded_page.file_path.exists()
    assert new_location.resolve() in loaded_page.file_path.resolve().parents
    assert loaded_page.file_path.read_bytes() == b"content to move"

def test_legacy_absolute_paths_compatibility(tmp_path):
    """Legacy project.json with absolute paths should resolve via fallback if original file is missing."""
    project_dir = tmp_path / "legacy_project"
    project_dir.mkdir()
    pages_dir = project_dir / "pages"
    pages_dir.mkdir()
    
    pid = "page_leg"
    # Put image in pages directory
    local_img = pages_dir / f"{pid}_legacy.png"
    local_img.write_bytes(b"legacy local image content")
    
    # Create legacy project.json with nonexistent absolute path
    legacy_json = {
        "id": "legacy_project",
        "name": "Legacy Project",
        "created_at": "2025-01-01T00:00:00",
        "settings": {},
        "pages": {
            pid: {
                "id": pid,
                "file_path": "/nonexistent/old/path/on/other/machine/legacy.png",
                "bubbles": [],
                "processed_image_path": None
            }
        }
    }
    
    with open(project_dir / "project.json", "w", encoding="utf-8") as f:
        json.dump(legacy_json, f)
        
    loaded = Project.load(project_dir)
    loaded_page = loaded.pages[pid]
    
    assert loaded_page.file_path.exists()
    assert loaded_page.file_path.resolve() == local_img.resolve()
