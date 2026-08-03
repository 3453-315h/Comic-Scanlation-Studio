import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class TextBubble:
    """Represents a detected text bubble"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    bbox: list[int] = field(default_factory=list)  # [x1, y1, x2, y2]
    text_original: str = ""
    text_translated: str = ""
    confidence: float = 0.0
    inpainting_mask: Path | None = None
    font_size: int = 12
    font_family: str = "Arial"
    status: str = "pending"  # pending, translated, approved, failed
    text_offset: tuple | None = None  # (x, y) offset for text rendering

    def to_dict(self) -> dict:
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
    file_path: Path | None = None
    bubbles: list[TextBubble] = field(default_factory=list)
    processed_image_path: Path | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "file_path": str(self.file_path) if self.file_path else None,
            "bubbles": [b.to_dict() for b in self.bubbles],
            "processed_image_path": str(self.processed_image_path) if self.processed_image_path else None
        }

class Project:
    """Manages a scanlation project"""
    def __init__(self, name: str, project_id: str | None = None):
        self.id = project_id or str(uuid.uuid4())[:12]
        self.name = name
        self.created_at = datetime.now()
        self.pages: dict[str, Page] = {}
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
        page = Page(file_path=image_path)
        self.pages[page.id] = page
        return page

    def save(self, projects_dir: Path):
        """Save project to local disk"""
        project_dir = projects_dir / self.id
        project_dir.mkdir(exist_ok=True)

        # Save project metadata
        data = {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "settings": self.settings,
            "pages": {pid: p.to_dict() for pid, p in self.pages.items()}
        }

        with open(project_dir / "project.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, project_dir: Path) -> "Project":
        """Load project from disk"""
        with open(project_dir / "project.json", encoding="utf-8") as f:
            data = json.load(f)

        project = cls(name=data["name"], project_id=data["id"])
        project.created_at = datetime.fromisoformat(data["created_at"])
        project.settings = data["settings"]

        for pid, pdata in data["pages"].items():
            page = Page(id=pid, file_path=Path(pdata["file_path"]))
            page.processed_image_path = Path(pdata["processed_image_path"]) if pdata["processed_image_path"] else None

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
