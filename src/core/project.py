from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional
import json
from datetime import datetime
import uuid

import shutil

@dataclass
class TextBubble:
    """Represents a detected text bubble"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    bbox: List[int] = field(default_factory=list)  # [x1, y1, x2, y2]
    text_original: str = ""
    text_translated: str = ""
    confidence: float = 0.0
    inpainting_mask: Optional[Path] = None
    font_size: int = 12
    font_family: str = "Arial"
    status: str = "pending"  # pending, translated, approved, failed
    text_offset: Optional[tuple] = None  # (x, y) offset for text rendering
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "bbox": self.bbox,
            "text_original": self.text_original,
            "text_translated": self.text_translated,
            "confidence": self.confidence,
            "font_size": self.font_size,
            "font_family": self.font_family,
            "status": self.status,
            "text_offset": self.text_offset
        }

@dataclass
class Page:
    """Represents a comic page"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    file_path: Optional[Path] = None
    bubbles: List[TextBubble] = field(default_factory=list)
    processed_image_path: Optional[Path] = None
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "file_path": str(self.file_path) if self.file_path else None,
            "bubbles": [b.to_dict() for b in self.bubbles],
            "processed_image_path": str(self.processed_image_path) if self.processed_image_path else None
        }

class Project:
    """Manages a scanlation project"""
    def __init__(self, name: str, project_id: Optional[str] = None):
        self.id = project_id or str(uuid.uuid4())[:12]
        self.name = name
        self.created_at = datetime.now()
        self.pages: Dict[str, Page] = {}
        self.settings = {
            "source_language": "ja",
            "target_language": "en",
            "detector_model": "comic-text-detector",
            "ocr_model": "manga_ocr",
            "inpainter_model": "lama",
            "translation_api": "deepl",
            "default_font": "Arial",
            "ignore_sfx": True
        }
        self.cloud_synced = False
    
    def add_page(self, image_path: Path) -> Page:
        """Add a new page to the project"""
        page = Page(file_path=Path(image_path))
        self.pages[page.id] = page
        return page
    
    def save(self, projects_dir: Path):
        """Save project to local disk with portable project-relative paths.
        
        Original images outside the project directory are copied into the project's
        'pages' directory so the project is self-contained and portable.
        """
        p_path = Path(projects_dir)
        if p_path.name == self.id:
            project_dir = p_path
        else:
            project_dir = p_path / self.id
        project_dir.mkdir(parents=True, exist_ok=True)
        pages_dir = project_dir / "pages"
        pages_dir.mkdir(exist_ok=True)
        
        pages_dict = {}
        for pid, page in self.pages.items():
            rel_file = None
            if page.file_path:
                fp = Path(page.file_path)
                try:
                    rel_file = str(fp.resolve().relative_to(project_dir.resolve()))
                except ValueError:
                    if fp.exists():
                        dest = pages_dir / f"{pid}_{fp.name}"
                        if fp.resolve() != dest.resolve():
                            shutil.copy2(fp, dest)
                            page.file_path = dest
                        rel_file = str(dest.resolve().relative_to(project_dir.resolve()))
                    else:
                        rel_file = str(page.file_path)
            
            rel_proc = None
            if page.processed_image_path:
                pp = Path(page.processed_image_path)
                try:
                    rel_proc = str(pp.resolve().relative_to(project_dir.resolve()))
                except ValueError:
                    if pp.exists():
                        dest = pages_dir / f"{pid}_proc_{pp.name}"
                        if pp.resolve() != dest.resolve():
                            shutil.copy2(pp, dest)
                            page.processed_image_path = dest
                        rel_proc = str(dest.resolve().relative_to(project_dir.resolve()))
                    else:
                        rel_proc = str(page.processed_image_path)
            
            pdict = page.to_dict()
            pdict["file_path"] = rel_file
            pdict["processed_image_path"] = rel_proc
            pages_dict[pid] = pdict
        
        # Save project metadata
        data = {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "settings": self.settings,
            "pages": pages_dict
        }
        
        with open(project_dir / "project.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load(cls, project_dir: Path) -> "Project":
        """Load project from disk, resolving relative and legacy absolute paths."""
        project_dir = Path(project_dir)
        project_file = project_dir / "project.json"
        with open(project_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        project = cls(name=data["name"], project_id=data["id"])
        project.created_at = datetime.fromisoformat(data["created_at"])
        project.settings = data["settings"]
        
        pages_dir = project_dir / "pages"
        
        for pid, pdata in data["pages"].items():
            raw_path = pdata.get("file_path")
            file_path = None
            if raw_path:
                cand = Path(raw_path)
                if not cand.is_absolute():
                    file_path = (project_dir / cand).resolve()
                elif cand.exists():
                    file_path = cand
                else:
                    # Legacy absolute path resolution if source moved/deleted
                    if (project_dir / cand.name).exists():
                        file_path = (project_dir / cand.name).resolve()
                    elif (pages_dir / cand.name).exists():
                        file_path = (pages_dir / cand.name).resolve()
                    elif pages_dir.exists():
                        matches = list(pages_dir.glob(f"{pid}_*"))
                        if matches:
                            file_path = matches[0].resolve()
                        else:
                            file_path = cand
                    else:
                        file_path = cand
            
            raw_proc = pdata.get("processed_image_path")
            proc_path = None
            if raw_proc:
                cand_proc = Path(raw_proc)
                if not cand_proc.is_absolute():
                    proc_path = (project_dir / cand_proc).resolve()
                elif cand_proc.exists():
                    proc_path = cand_proc
                else:
                    if (project_dir / cand_proc.name).exists():
                        proc_path = (project_dir / cand_proc.name).resolve()
                    elif (pages_dir / cand_proc.name).exists():
                        proc_path = (pages_dir / cand_proc.name).resolve()
                    elif pages_dir.exists():
                        matches = list(pages_dir.glob(f"{pid}_proc_*"))
                        if matches:
                            proc_path = matches[0].resolve()
                        else:
                            proc_path = cand_proc
                    else:
                        proc_path = cand_proc
                        
            page = Page(id=pid, file_path=file_path)
            page.processed_image_path = proc_path
            
            for bdata in pdata["bubbles"]:
                bubble = TextBubble(
                    id=bdata["id"],
                    bbox=bdata["bbox"],
                    text_original=bdata["text_original"],
                    text_translated=bdata["text_translated"],
                    confidence=bdata["confidence"],
                    font_size=bdata["font_size"],
                    font_family=bdata["font_family"],
                    status=bdata["status"],
                    text_offset=bdata.get("text_offset")
                )
                page.bubbles.append(bubble)
            
            project.pages[pid] = page
        
        return project