
import copy
import logging
import os
import sys
import uuid
from pathlib import Path

import cv2

logger = logging.getLogger(__name__)

# PySide6 import with error handling
try:
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QAction, QImage
    from PySide6.QtWidgets import (
        QApplication,
        QFileDialog,
        QFrame,
        QHBoxLayout,
        QLabel,
        QMainWindow,
        QMenuBar,
        QMessageBox,
        QPushButton,
        QSplitter,
        QStatusBar,
        QVBoxLayout,
        QWidget,
    )
except ImportError as e:
    print("=" * 60)
    print("ERROR: PySide6 is not installed or corrupted!")
    print("Run: pip install PySide6")
    print("=" * 60)
    raise ImportError(f"PySide6 installation required: {e}")

# Local imports
from ..core.config import Config
from ..core.pipeline import ScanlationPipeline
from ..core.project import Page, Project, TextBubble
from ..utils.image_utils import create_cbz, create_pdf, extract_archive, load_image
from .dialogs.batch_dialog import BatchProcessDialog
from .dialogs.download_models_dialog import DownloadModelsDialog
from .dialogs.settings_dialog import SettingsDialog
from .dialogs.text_editor import TextEditorDialog
from .theme import apply_theme, is_dark_mode_preferred
from .widgets.editor_panel import EditorPanel
from .widgets.image_viewer import ImageViewer
from .widgets.log_console import LogConsole
from .widgets.page_carousel import PageCarousel
from .widgets.top_bar import TopBar
from .workers import WorkerThread


class MainWindow(QMainWindow):
    """
    Modern Comic Scanlation Studio - 8-bit-magic-wand style layout
    
    Layout:
    ┌─────────────────────────────────────────────────────────────┐
    │  TopBar: [← Home] [Reset] ─── Project Name ─── [Settings]   │
    ├─────────────────────────────────────────────────┬───────────┤
    │                                                 │           │
    │              Main Image Viewer                  │ Editor    │
    │           (Content area with zoom)              │ Panel     │
    │                                                 │           │
    ├────────────────────┬────────────────────────────┴───────────┤
    │ Upload │ Page Gallery (Carousel) ...                        │
    └────────────────────┴────────────────────────────────────────┘
    """

    def __init__(self):
        super().__init__()
        self.config = Config()
        self.config.initialize_dirs()

        self.project: Project | None = None
        self._language_detected = False

        # Initialize pipeline safely
        try:
            self.pipeline = ScanlationPipeline(self.config)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Models failed: {e}")
            sys.exit(1)

        # Apply theme
        app = QApplication.instance()
        if app:
            apply_theme(app, dark=is_dark_mode_preferred())

        # Undo/Redo Stacks
        self.undo_stack: list[dict] = []
        self.redo_stack: list[dict] = []

        self._init_ui()
        self._setup_connections()
        self.init_dock_widgets()  # Must come before menubar (log_console needed)
        self.init_menubar()
        self.init_statusbar()

    def _init_ui(self):
        """Initialize the modern 3-pane UI layout"""
        self.setWindowTitle(f"Comic Scanlation Studio v{self.config.APP_VERSION}")

        # Set window icon
        icon_path = Path(__file__).parent.parent.parent / "assets" / "icon.png"
        if icon_path.exists():
            from PySide6.QtGui import QIcon
            self.setWindowIcon(QIcon(str(icon_path)))

        self.setMinimumSize(1280, 800)
        self.resize(1400, 900)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ─────────────────────────────────────────────────────────
        # TOP BAR
        # ─────────────────────────────────────────────────────────
        self.top_bar = TopBar()
        main_layout.addWidget(self.top_bar)

        # ─────────────────────────────────────────────────────────
        # MIDDLE: Image Viewer + Editor Panel
        # ─────────────────────────────────────────────────────────
        middle_splitter = QSplitter(Qt.Orientation.Horizontal)
        middle_splitter.setHandleWidth(1)

        # Image Viewer (main content area)
        self.image_viewer = ImageViewer()
        self.image_viewer.setObjectName("ImageViewer")
        middle_splitter.addWidget(self.image_viewer)

        # Editor Panel (right sidebar)
        self.editor_panel = EditorPanel()
        middle_splitter.addWidget(self.editor_panel)

        # Splitter sizing
        middle_splitter.setStretchFactor(0, 4)
        middle_splitter.setStretchFactor(1, 1)
        middle_splitter.setSizes([1000, 300])

        main_layout.addWidget(middle_splitter, stretch=1)

        # ─────────────────────────────────────────────────────────
        # BOTTOM: Page Carousel
        # ─────────────────────────────────────────────────────────
        bottom_bar = QWidget()
        bottom_bar.setObjectName("BottomBar")
        bottom_bar.setFixedHeight(180)
        bottom_layout = QVBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(16, 12, 16, 12)

        self.page_carousel = PageCarousel()
        bottom_layout.addWidget(self.page_carousel)

        main_layout.addWidget(bottom_bar)

    def _setup_connections(self):
        """Connect signals to slots"""
        self.top_bar.home_clicked.connect(self._on_home)
        self.top_bar.reset_clicked.connect(self._on_reset)
        self.top_bar.settings_clicked.connect(self.show_model_settings)
        self.top_bar.reveal_toggled.connect(self._on_reveal_toggle)
        self.top_bar.undo_clicked.connect(self.undo_action)
        self.top_bar.redo_clicked.connect(self.redo_action)
        self.top_bar.zoom_in_clicked.connect(self._on_zoom_in)
        self.top_bar.zoom_out_clicked.connect(self._on_zoom_out)

        self.editor_panel.detect_clicked.connect(self.detect_text)
        self.editor_panel.ocr_clicked.connect(self.perform_ocr)
        self.editor_panel.edit_text_clicked.connect(self.open_text_editor)
        self.editor_panel.translate_clicked.connect(self.translate_all)
        self.editor_panel.inpaint_clicked.connect(self.perform_inpainting)
        self.editor_panel.imprint_clicked.connect(self.perform_imprinting)
        self.editor_panel.export_clicked.connect(self.export_final_image)
        self.editor_panel.process_all_clicked.connect(self.process_all_stages)

        # Manual Bubble Creation
        self.editor_panel.add_bubble_toggled.connect(self.image_viewer.set_draw_mode)
        self.image_viewer.bubble_created.connect(self._on_bubble_created)

        # Font settings
        self.editor_panel.font_changed.connect(self._on_font_changed)
        self.editor_panel.font_bold_clicked.connect(self.image_viewer.toggle_bold_selection)
        self.editor_panel.font_italic_clicked.connect(self.image_viewer.toggle_italic_selection)

        self.page_carousel.page_selected.connect(self._on_carousel_page_selected)
        self.page_carousel.page_removed.connect(self._on_carousel_page_removed)
        self.page_carousel.upload_clicked.connect(self.import_pages)

        # Selection
        self.image_viewer.scene.selectionChanged.connect(self._on_selection_changed)

        # Generic save state request from viewer (e.g. before move/resize)
        self.image_viewer.request_save_state.connect(lambda: self.save_state("Interaction"))

    def init_dock_widgets(self):
        """Initialize dock widgets"""
        self.log_console = LogConsole(self)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.log_console)
        self.log_console.hide()

    def init_menubar(self):
        """Initialize menu bar (kept for power users)"""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        new_action = QAction("&New Project", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_project)
        file_menu.addAction(new_action)

        open_action = QAction("&Open Project", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_project)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        import_action = QAction("&Import Pages", self)
        import_action.setShortcut("Ctrl+I")
        import_action.triggered.connect(self.import_pages)
        file_menu.addAction(import_action)

        file_menu.addSeparator()

        exit_action = QAction("&Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu (for undo/redo)
        edit_menu = menubar.addMenu("&Edit")

        undo_action = QAction("&Undo", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.triggered.connect(self.undo_action)
        edit_menu.addAction(undo_action)

        redo_action = QAction("&Redo", self)
        redo_action.setShortcut("Ctrl+Y")
        redo_action.triggered.connect(self.redo_action)
        edit_menu.addAction(redo_action)

        # View menu
        view_menu = menubar.addMenu("&View")

        log_action = QAction("Show &Log Console", self)
        log_action.setCheckable(True)
        log_action.triggered.connect(lambda checked: self.log_console.setVisible(checked))
        self.log_console.visibilityChanged.connect(log_action.setChecked)
        view_menu.addAction(log_action)

        # Process menu
        process_menu = menubar.addMenu("&Process")

        detect_action = QAction("&Detect Speech Bubbles", self)
        detect_action.triggered.connect(self.detect_text)
        process_menu.addAction(detect_action)

        batch_action = QAction("&Batch Process Pages...", self)
        batch_action.triggered.connect(self.open_batch_dialog)
        process_menu.addAction(batch_action)

        ocr_action = QAction("&OCR Text", self)
        ocr_action.triggered.connect(self.perform_ocr)
        process_menu.addAction(ocr_action)

        translate_action = QAction("&Translate All", self)
        translate_action.triggered.connect(self.translate_all)
        process_menu.addAction(translate_action)

        inpaint_action = QAction("&Inpaint", self)
        inpaint_action.triggered.connect(self.perform_inpainting)
        process_menu.addAction(inpaint_action)

        imprint_action = QAction("I&mprint", self)
        imprint_action.triggered.connect(self.perform_imprinting)
        process_menu.addAction(imprint_action)

        process_menu.addSeparator()

        process_all_action = QAction("Process &All", self)
        process_all_action.triggered.connect(self.process_all_stages)
        process_menu.addAction(process_all_action)

        # Settings menu
        settings_menu = menubar.addMenu("&Settings")

        settings_action = QAction("&Settings", self)
        settings_action.triggered.connect(self.show_model_settings)
        settings_menu.addAction(settings_action)

        download_action = QAction("&Download Models", self)
        download_action.triggered.connect(self.show_download_models)
        settings_menu.addAction(download_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def init_statusbar(self):
        """Initialize status bar"""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("Ready")
        self._update_undo_buttons() # Initialize undo/redo button states

    # ─────────────────────────────────────────────────────────────
    # TopBar Actions
    # ─────────────────────────────────────────────────────────────

    def _on_home(self):
        """Handle home button click"""
        # For now, just prompt to create/open project
        self.new_project()

    def _on_reset(self):
        """Reset current session"""
        if self.project and self.image_viewer.current_page:
            page = self.image_viewer.current_page
            self.save_state("Reset Bubbles")
            page.bubbles.clear()
            page.processed_image_path = None
            if page.file_path.exists():
                self.image_viewer.load_image(page.file_path)
            self.image_viewer.display_bubbles([])
            self.editor_panel.set_status("Session reset")
            self.statusbar.showMessage("Session reset")
            for stage in ["detect", "ocr", "translate", "inpaint", "imprint"]:
                self.editor_panel.update_button_status(stage, 0)

    def _on_reveal_toggle(self, enabled: bool):
        """Toggle reveal-on-hover mode"""
        self.image_viewer.set_reveal_mode(enabled)

    def _on_zoom_in(self):
        """Handle zoom in"""
        self.image_viewer.zoom_in()

    def _on_zoom_out(self):
        """Handle zoom out"""
        self.image_viewer.zoom_out()

    def _on_selection_changed(self):
        """Handle selection changes to update font UI"""
        items = self.image_viewer.scene.selectedItems()
        if len(items) == 1:
            item = items[0]
            from src.gui.items.text_edit_item import TextEditItem
            if isinstance(item, TextEditItem):
                self.editor_panel.update_font_ui(item._font_family, item._font_size)

    def _on_font_changed(self, family: str, size: int):
        """Handle font settings change - update text items in-place so positions are not reset"""
        self.config.DEFAULT_FONT = family
        self.config.DEFAULT_FONT_SIZE = size
        self.pipeline.font_style.font_family = family
        self.pipeline.font_style.font_size = size

        if self.image_viewer.has_text_items():
            import shiboken6

            selected_items = self.image_viewer.scene.selectedItems()
            from src.gui.items.text_edit_item import TextEditItem
            text_selected = [i for i in selected_items if isinstance(i, TextEditItem)]

            # If specific text items are selected, only update them. Otherwise, update all.
            target_items = text_selected if text_selected else self.image_viewer.text_items

            for item in target_items:
                try:
                    if shiboken6.isValid(item):
                        current_pos = item.pos()
                        item.set_style(font_family=family, font_size=size)
                        item.setPos(current_pos)
                        item._sync_to_bubble()
                except Exception:
                    pass

    # ─────────────────────────────────────────────────────────────
    # Carousel Actions
    # ─────────────────────────────────────────────────────────────

    def _on_carousel_page_selected(self, page_id: str):
        """Handle page selection from carousel"""
        if self.project and page_id in self.project.pages:
            page = self.project.pages[page_id]
            self._load_page(page)
            self.undo_stack.clear() # Clear undo/redo history on page change
            self.redo_stack.clear()
            self._update_undo_buttons()


    def _on_carousel_page_removed(self, page_id: str):
        """Handle page removal from carousel"""
        # Immediate deletion as requested (no confirmation popup)
        if self.project and page_id in self.project.pages:
            # Check if deleting current page
            is_current = (self.image_viewer.current_page and
                          self.image_viewer.current_page.id == page_id)

            del self.project.pages[page_id]
            self.page_carousel.remove_page(page_id)
            self.project.save(self.config.PROJECTS_DIR)

            if is_current:
                self.image_viewer.clear_content()
                self.editor_panel.set_status("Page deleted")
                self.undo_stack.clear()
                self.redo_stack.clear()
                self._update_undo_buttons()
                for stage in ["detect", "ocr", "translate", "inpaint", "imprint"]:
                    self.editor_panel.update_button_status(stage, 0)

            self.statusbar.showMessage("Removed page")

    def _load_page(self, page: Page):
        """Load a page into the viewer"""
        if page and page.file_path.exists():
            if page.processed_image_path and page.processed_image_path.exists():
                self.image_viewer.load_image(page.processed_image_path)
            else:
                self.image_viewer.load_image(page.file_path)

            self.image_viewer.display_bubbles(page.bubbles)
            self.image_viewer.current_page = page

            detect_count = len(page.bubbles)
            ocr_count = sum(1 for b in page.bubbles if b.text_original)
            trans_count = sum(1 for b in page.bubbles if b.text_translated)
            inpaint_count = detect_count if page.processed_image_path and page.processed_image_path.exists() else 0

            self.editor_panel.update_button_status("detect", detect_count)
            self.editor_panel.update_button_status("ocr", ocr_count)
            self.editor_panel.update_button_status("translate", trans_count)
            self.editor_panel.update_button_status("inpaint", inpaint_count)
            self.editor_panel.update_button_status("imprint", trans_count if getattr(page, 'imprinted', False) else 0)

    # ─────────────────────────────────────────────────────────────
    # Project Management
    # ─────────────────────────────────────────────────────────────

    def new_project(self):
        """Create a new project"""
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "New Project", "Project name:")

        if ok and name:
            self.project = Project(name)
            self.top_bar.set_project_name(name)
            self.page_carousel.clear()
            self.image_viewer.clear_content()
            self.statusbar.showMessage(f"Created project: {name}")
            self.undo_stack.clear()
            self.redo_stack.clear()
            self._update_undo_buttons()
            for stage in ["detect", "ocr", "translate", "inpaint", "imprint"]:
                self.editor_panel.update_button_status(stage, 0)

    def open_project(self):
        """Open an existing project"""
        project_dir = QFileDialog.getExistingDirectory(
            self, "Open Project", str(self.config.PROJECTS_DIR)
        )

        if project_dir:
            try:
                self.project = Project.load(Path(project_dir))
                self.top_bar.set_project_name(self.project.name)

                # Populate carousel
                self.page_carousel.clear()
                for page in self.project.pages.values():
                    self.page_carousel.add_page(page.id, page.file_path)

                self.statusbar.showMessage(f"Opened project: {self.project.name}")
                self.undo_stack.clear()
                self.redo_stack.clear()
                self._update_undo_buttons()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load project: {e}")

    def import_pages(self):
        """Import image pages"""
        if not self.project:
            # Auto-create a quick project
            self.project = Project("Quick Project")
            self.top_bar.set_project_name("Quick Project")

        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Images or Archives", "",
            "All Supported (*.png *.jpg *.jpeg *.webp *.cbz *.cbr *.zip *.rar);;Images (*.png *.jpg *.jpeg *.webp);;Comic Books (*.cbz *.cbr *.zip *.rar)"
        )

        if files:
            added_count = 0
            for file_path_str in files:
                file_path = Path(file_path_str)

                # Check for archive
                if file_path.suffix.lower() in ['.cbz', '.cbr', '.zip', '.rar']:
                    self.statusbar.showMessage(f"Extracting {file_path.name}...")
                    QApplication.processEvents()

                    # Extract to a dedicated folder in project (stored under config.projects_dir/<id>)
                    extract_dir = (self.config.PROJECTS_DIR / self.project.id / "extracted" / file_path.stem)
                    images = extract_archive(file_path, extract_dir)

                    if not images:
                        QMessageBox.warning(self, "Extraction Failed", f"No images found in {file_path.name}\n(Note: CBR requires WinRAR/7-Zip installed)")
                        continue

                    for img_path in images:
                        page = self.project.add_page(img_path)
                        self.page_carousel.add_page(page.id, page.file_path)
                        added_count += 1
                else:
                    # Regular image
                    page = self.project.add_page(file_path)
                    self.page_carousel.add_page(page.id, page.file_path)
                    added_count += 1

            self.project.save(self.config.PROJECTS_DIR)
            self.statusbar.showMessage(f"Added {added_count} pages")

    # ─────────────────────────────────────────────────────────────
    # Workflow Actions
    # ─────────────────────────────────────────────────────────────

    def export_project(self):
        """Export the current project to CBZ or PDF"""
        if not self.project or not self.project.pages:
            QMessageBox.warning(self, "Export Failed", "No pages to export.")
            return

        # 1. Ask user for destination and format
        file_path, filter_str = QFileDialog.getSaveFileName(
            self, "Export Project",
            f"{self.project.name}",
            "Comic Book Archive (*.cbz);;PDF Document (*.pdf)"
        )

        if not file_path:
            return

        output_path = Path(file_path)

        # 2. Collect pages (prefer processed/translated images, fallback to original)
        export_pages = []
        for page in self.project.pages.values():
            if page.processed_image_path and page.processed_image_path.exists():
                export_pages.append(page.processed_image_path)
            else:
                export_pages.append(page.file_path)

        self.statusbar.showMessage(f"Exporting to {output_path.name}...")
        QApplication.processEvents()

        # 3. Perform Export
        success = False
        if output_path.suffix.lower() == '.cbz':
            success = create_cbz(export_pages, output_path)
        elif output_path.suffix.lower() == '.pdf':
            success = create_pdf(export_pages, output_path)

        if success:
            QMessageBox.information(self, "Export Successful", f"Saved to {output_path}")
            self.statusbar.showMessage(f"Exported {len(export_pages)} pages")
        else:
            QMessageBox.critical(self, "Export Failed", "Check console for errors.")
            self.statusbar.showMessage("Export failed")

    def _create_menu_bar(self):
        menu_bar = self.menuBar()

        # File Menu
        file_menu = menu_bar.addMenu("File")

        open_action = QAction("Open Project", self)
        open_action.triggered.connect(self.open_project_dialog)
        file_menu.addAction(open_action)

        import_action = QAction("Import Pages...", self)
        import_action.triggered.connect(self.import_pages)
        file_menu.addAction(import_action)

        file_menu.addSeparator()

        export_action = QAction("Export Project...", self)
        export_action.triggered.connect(self.export_project)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
    # ─────────────────────────────────────────────────────────────

    def detect_text(self):
        """Run text detection on current page (Background)"""
        if not self.project or not self.image_viewer.current_page:
            QMessageBox.warning(self, "Warning", "No page loaded!")
            return

        page = self.image_viewer.current_page
        self.editor_panel.set_status("Detecting text bubbles...")
        self.statusbar.showMessage("Detecting text... (Background)")

        # Disable UI
        self.editor_panel.setEnabled(False)

        # Prepare args
        image_path = page.file_path
        ignore_sfx = self.project.settings.get("ignore_sfx", True)

        self.current_worker = WorkerThread(self._run_detection_task, image_path, ignore_sfx, self.pipeline)
        self.current_worker.signals.result.connect(self._on_detection_complete)
        self.current_worker.signals.error.connect(self._on_worker_error)
        self.current_worker.signals.finished.connect(self._on_worker_finished)
        self.current_worker.start()

    def _run_detection_task(self, image_path, ignore_sfx, pipeline):
        # Background task
        image = load_image(image_path)
        return pipeline.detector.detect(image, ignore_sfx=ignore_sfx)

    def _on_detection_complete(self, bubbles):
        if not self.project or not self.image_viewer.current_page:
            return

        page = self.image_viewer.current_page
        self.save_state("Before Detection")

        page.bubbles = bubbles
        self.image_viewer.display_bubbles(bubbles)
        self.editor_panel.update_button_status("detect", len(bubbles))
        self.editor_panel.set_status(f"Found {len(bubbles)} text regions")
        self.statusbar.showMessage(f"Detected {len(bubbles)} text bubbles")

        self.project.save(self.config.PROJECTS_DIR)
        self.save_state("Detect Text")

    def _on_worker_finished(self):
        self.editor_panel.setEnabled(True)
        self.current_worker = None

    def _on_worker_error(self, err):
        exctype, value, tb = err
        logger.error(f"Worker Error: {value}")
        self.statusbar.showMessage(f"Error: {value}")
        QMessageBox.critical(self, "Processing Error", f"An error occurred:\n{value}")

    def _on_bubble_created(self, rect):
        """Handle manual bubble creation"""
        if not self.image_viewer.current_page:
            return

        page = self.image_viewer.current_page

        # Create new bubble
        # x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
        # Ensure coordinates are integers for consistency with detection
        x1 = int(rect.x())
        y1 = int(rect.y())
        x2 = int(rect.x() + rect.width())
        y2 = int(rect.y() + rect.height())

        new_bubble = TextBubble(
            id=uuid.uuid4().hex,
            bbox=[x1, y1, x2, y2],
            text_original="", # Empty for manual
            confidence=1.0,
            status="detected"
        )

        # Add to page
        page.bubbles.append(new_bubble)

        # Auto-run OCR on the new bubble
        try:
            self.statusbar.showMessage("Extracting text for new bubble...")
            QApplication.processEvents()

            # Load image
            image = load_image(page.file_path)

            # Run OCR
            text = self.pipeline.ocr.recognize(image, new_bubble.bbox)
            if text:
                new_bubble.text_original = text
                new_bubble.confidence = self.pipeline.ocr.confidence
                new_bubble.status = "ocr_done"
                self.statusbar.showMessage(f"Extracted: {text[:20]}...")
            else:
                self.statusbar.showMessage("No text extracted from new bubble")

        except Exception as e:
            logger.error(f"Auto-OCR failed: {e}")
            self.statusbar.showMessage("Auto-OCR failed for new bubble")

        # Update display (using save_state for undo functionality first)
        self.save_state("Manual Bubble Creation")

        # Refresh viewer
        self.image_viewer.display_bubbles(page.bubbles)
        self.editor_panel.update_button_status("detect", len(page.bubbles))
        # Update ocr count too if we did it
        ocr_count = sum(1 for b in page.bubbles if b.status in ["ocr_done", "translated"])
        self.editor_panel.update_button_status("ocr", ocr_count)

        # Save project
        if self.project:
            self.project.save(self.config.PROJECTS_DIR)

        # Note: We keep draw mode enabled for adding multiple bubbles.
        # User toggles button to stop.

    def perform_ocr(self):
        """Run OCR on detected bubbles using WorkerThread"""
        if not self.project or not self.image_viewer.current_page:
            QMessageBox.warning(self, "Warning", "No page loaded!")
            return

        page = self.image_viewer.current_page
        if not page.bubbles:
            QMessageBox.warning(self, "Warning", "No bubbles detected. Run detection first.")
            return

        self.editor_panel.set_status("Extracting text (OCR)...")
        self.statusbar.showMessage("Performing OCR... (Background)")
        self.editor_panel.setEnabled(False)

        # Prepare data
        image_path = page.file_path
        bubbles_data = []
        for b in page.bubbles:
            if b.status in ["pending", "ocr_done", "detected"]:
                bubbles_data.append((b.id, b.bbox))

        self.current_worker = WorkerThread(self._run_ocr_task, image_path, bubbles_data, self.pipeline)
        self.current_worker.signals.result.connect(self._on_ocr_complete)
        self.current_worker.signals.error.connect(self._on_worker_error)
        self.current_worker.signals.finished.connect(self._on_worker_finished)
        self.current_worker.start()

    def _run_ocr_task(self, image_path, bubbles_data, pipeline):
        image = load_image(image_path)
        results = {}
        for b_id, bbox in bubbles_data:
            text = pipeline.ocr.recognize(image, bbox)
            conf = pipeline.ocr.confidence
            results[b_id] = (text, conf)
        return results

    def _on_ocr_complete(self, results):
        if not self.project or not self.image_viewer.current_page:
            return
        page = self.image_viewer.current_page

        self.save_state("Before OCR")
        ocr_count = 0
        for bubble in page.bubbles:
            if bubble.id in results:
                text, conf = results[bubble.id]
                bubble.text_original = text
                bubble.confidence = conf
                bubble.status = "ocr_done"
                ocr_count += 1

        self.image_viewer.display_bubbles(page.bubbles)
        self.editor_panel.update_button_status("ocr", ocr_count)
        self.editor_panel.set_status(f"OCR complete: {ocr_count} texts extracted")
        self.statusbar.showMessage(f"OCR completed on {ocr_count} bubbles")

        self.project.save(self.config.PROJECTS_DIR)
        self.save_state("Perform OCR")
        self.open_text_editor()

    def open_text_editor(self):
        """Open dialog to edit detected text"""
        if not self.project or not self.image_viewer.current_page:
            QMessageBox.warning(self, "Warning", "No page loaded!")
            return

        page = self.image_viewer.current_page
        if not page.bubbles:
            QMessageBox.info(self, "Info", "No bubbles to edit.")
            return

        def translate_wrapper(text: str, engine: str = None) -> str:
            """Wrapper for translation with correct context"""
            try:
                return self.pipeline.translator.translate(
                    text,
                    context=f"From {self.project.name}",
                    api_override=engine
                )
            except Exception as e:
                QMessageBox.warning(self, "Translation Error", f"Failed: {e}")
                return ""

        self.save_state("Before Text Edit")
        dialog = TextEditorDialog(page.bubbles, self, translator_callback=translate_wrapper)
        if dialog.exec():
            # User saved changes
            dialog.save_changes()
            self.project.save(self.config.PROJECTS_DIR)

            # Refresh view (e.g. if we show text on bubbles, though currently we mostly show boxes)
            self.image_viewer.display_bubbles(page.bubbles)
            self.editor_panel.set_status("Text updates saved")
            self.statusbar.showMessage("Text updates saved")
            self.save_state("Edit Text")

    def translate_all(self):
        """Translate all text using WorkerThread"""
        if not self.project or not self.image_viewer.current_page:
            return

        page = self.image_viewer.current_page
        self.editor_panel.set_status("Translating...")
        self.statusbar.showMessage("Translating... (Background)")
        self.editor_panel.setEnabled(False)

        texts_to_translate = {}
        for b in page.bubbles:
            if b.status != "failed" and b.text_original:
                texts_to_translate[b.id] = b.text_original

        context = f"From {self.project.name}"

        self.current_worker = WorkerThread(self._run_translation_task, texts_to_translate, context, self.pipeline)
        self.current_worker.signals.result.connect(self._on_translation_complete)
        self.current_worker.signals.error.connect(self._on_worker_error)
        self.current_worker.signals.finished.connect(self._on_worker_finished)
        self.current_worker.start()

    def _run_translation_task(self, texts_map, context, pipeline):
        results = {}
        for b_id, text in texts_map.items():
            try:
                translated = pipeline.translator.translate(text, context=context)
                results[b_id] = translated
            except Exception as e:
                logger.error(f"Translation failed for {b_id}: {e}")
        return results

    def _on_translation_complete(self, results):
        if not self.project or not self.image_viewer.current_page:
            return
        page = self.image_viewer.current_page

        self.save_state("Before Translation")
        trans_count = 0
        for bubble in page.bubbles:
            if bubble.id in results:
                bubble.text_translated = results[bubble.id]
                bubble.status = "translated"
                trans_count += 1

        self.image_viewer.display_bubbles(page.bubbles)
        self.editor_panel.update_button_status("translate", trans_count)
        self.editor_panel.set_status(f"Translated {trans_count} texts")
        self.statusbar.showMessage("Translation complete")
        self.project.save(self.config.PROJECTS_DIR)
        self.save_state("Translate All")

    def perform_inpainting(self):
        """Run inpainting on detected text regions using WorkerThread"""
        if not self.project or not self.image_viewer.current_page:
            QMessageBox.warning(self, "Warning", "No page loaded!")
            return

        page = self.image_viewer.current_page
        self.editor_panel.set_status("Inpainting text regions...")
        self.statusbar.showMessage("Inpainting... (Background)")
        self.editor_panel.setEnabled(False)

        image_path = page.file_path
        # Pass ALL valid bounding boxes to inpainter. Even if OCR failed (e.g. blank bubble),
        # the user still wants the drawn bubble erased.
        bboxes = [b.bbox for b in page.bubbles if b.bbox and len(b.bbox) == 4]

        if not bboxes:
             self.editor_panel.set_status("No bubbles to inpaint")
             self.editor_panel.setEnabled(True)
             return

        output_path = Path(page.file_path).parent / f"{page.id}_inpainted.png"

        self.current_worker = WorkerThread(self._run_inpainting_task, image_path, bboxes, output_path, self.pipeline)
        self.current_worker.signals.result.connect(self._on_inpainting_complete)
        self.current_worker.signals.error.connect(self._on_worker_error)
        self.current_worker.signals.finished.connect(self._on_worker_finished)
        self.current_worker.start()

    def _run_inpainting_task(self, image_path, bboxes, output_path, pipeline):
        image = load_image(image_path)
        inpainted = pipeline.inpainter.inpaint_multiple(image, bboxes)
        # Save result
        cv2.imwrite(str(output_path), inpainted)
        return output_path

    def _on_inpainting_complete(self, output_path):
        if not self.project or not self.image_viewer.current_page:
            return
        page = self.image_viewer.current_page

        page.processed_image_path = output_path
        self.image_viewer.load_image(output_path)


        count = sum(1 for b in page.bubbles if b.bbox and len(b.bbox) == 4)
        self.editor_panel.update_button_status("inpaint", count)
        self.editor_panel.set_status(f"Inpainted {count} regions")
        self.statusbar.showMessage(f"Inpainted {count} regions")

        self.project.save(self.config.PROJECTS_DIR)

    def perform_imprinting(self):
        """Show editable text on canvas for adjustment before export"""
        if not self.project or not self.image_viewer.current_page:
            QMessageBox.warning(self, "Warning", "No page loaded!")
            return

        page = self.image_viewer.current_page
        self.editor_panel.set_status("Loading text preview...")
        self.statusbar.showMessage("Imprinting - adjust text then click Export")
        QApplication.processEvents()

        try:
            # Load the inpainted image for display
            if page.processed_image_path and page.processed_image_path.exists():
                print(f"DEBUG: Loading inpainted image: {page.processed_image_path}")
                self.image_viewer.load_image(page.processed_image_path)
            else:
                print(f"DEBUG: Loading original image: {page.file_path}")
                self.image_viewer.load_image(page.file_path)

            # Get bubbles with translated text (regardless of status)
            translated_bubbles = [b for b in page.bubbles if b.text_translated]
            print(f"DEBUG: Found {len(translated_bubbles)} bubbles with translated text")

            if translated_bubbles:
                # Show editable text items on canvas
                print("DEBUG: Calling show_text_items...")
                self.image_viewer.show_text_items(translated_bubbles, self.pipeline.font_style)
                print(f"DEBUG: Text items shown: {len(self.image_viewer.text_items)}")

                self.editor_panel.update_button_status("imprint", len(translated_bubbles))
                self.editor_panel.set_status(f"Imprint: {len(translated_bubbles)} texts (drag to move, double-click to edit)")
                self.statusbar.showMessage("Drag text to adjust position, then Export")
            else:
                print("DEBUG: No translated bubbles found")
                self.editor_panel.set_status("No translated texts - run Translate first")
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Imprint failed: {e}")
            self.editor_panel.set_status(f"Imprint failed: {e}")

    def export_final_image(self):
        """Export the canvas with text as final image"""
        if not self.project or not self.image_viewer.current_page:
            QMessageBox.warning(self, "Warning", "No page loaded!")
            return

        if not self.image_viewer.has_text_items():
            QMessageBox.warning(self, "Warning", "No text to export! Run Preview first.")
            return

        try:
            # Render the scene to image
            final_image = self.image_viewer.export_with_text()
            if final_image is None:
                raise Exception("Failed to render scene")

            page = self.image_viewer.current_page
            default_name = f"{page.file_path.stem}_translated.png"
            default_path = str(page.file_path.parent / default_name)

            # 1. Prompt for save location and format
            file_path, selected_filter = QFileDialog.getSaveFileName(
                self,
                "Export Translated Image",
                default_path,
                "PNG Image (*.png);;JPEG Image (*.jpg *.jpeg);;WebP Image (*.webp)"
            )

            if not file_path:
                return  # User cancelled

            # 2. Check if we need a quality setting
            quality = -1
            lower_path = file_path.lower()
            if lower_path.endswith('.jpg') or lower_path.endswith('.jpeg') or lower_path.endswith('.webp'):
                quality = getattr(self.config, 'EXPORT_IMAGE_QUALITY', 90)

            # 3. Save the image
            # QImage.save uses the file extension to determine format
            success = final_image.save(file_path, quality=quality)
            if not success:
                raise Exception("Failed to write image file")

            output_path = Path(file_path)

            # Print success
            print(f"DEBUG: Saved final image to {output_path}")
            self.editor_panel.set_status(f"Saved to {output_path.name}")
            self.statusbar.showMessage(f"Exported successfully to {output_path}")

            # Open the file
            os.startfile(str(output_path))

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Export failed: {e}")

    # ========== Undo/Redo Logic ==========

    def save_state(self, description: str = "Change"):
        """Save current bubble state to undo stack"""
        if not self.image_viewer.current_page:
            return

        page = self.image_viewer.current_page

        # Deep copy bubbles
        state = {
            "page_id": page.id,
            "bubbles": copy.deepcopy([b.to_dict() for b in page.bubbles]),
            "description": description
        }

        self.undo_stack.append(state)
        self.redo_stack.clear()  # Clear redo on new action

        # Limit stack size
        if len(self.undo_stack) > 50:
            self.undo_stack.pop(0)

        self._update_undo_buttons()
        print(f"DEBUG: Saved state: {description} (Stack: {len(self.undo_stack)})")

    def undo_action(self):
        """Undo last action"""
        if not self.undo_stack:
            return

        # Save current state to redo stack
        page = self.image_viewer.current_page
        if not page:
            return

        current_state = {
            "page_id": page.id,
            "bubbles": copy.deepcopy([b.to_dict() for b in page.bubbles]),
            "description": "Current"
        }
        self.redo_stack.append(current_state)

        # Pop previous state
        state = self.undo_stack.pop()

        # Restore state
        self._restore_state(state)
        self._update_undo_buttons()
        print(f"DEBUG: Undo performed. Stack: {len(self.undo_stack)}")

    def redo_action(self):
        """Redo last undone action"""
        if not self.redo_stack:
            return

        # Save current state to undo stack
        page = self.image_viewer.current_page
        if not page:
            return

        current_state = {
            "page_id": page.id,
            "bubbles": copy.deepcopy([b.to_dict() for b in page.bubbles]),
            "description": "Current"
        }
        self.undo_stack.append(current_state)

        # Pop next state
        state = self.redo_stack.pop()

        # Restore state
        self._restore_state(state)
        self._update_undo_buttons()
        print(f"DEBUG: Redo performed. Stack: {len(self.redo_stack)}")

    def _restore_state(self, state: dict):
        """Restore bubbles from state"""
        if not self.project:
            return

        page_id = state["page_id"]
        # Find page
        page = self.project.pages.get(page_id)
        if not page:
            return

        # Restore bubbles
        page.bubbles = []
        for b_data in state["bubbles"]:
            bubble = TextBubble(
                id=b_data["id"],
                bbox=b_data["bbox"],
                text_original=b_data["text_original"],
                text_translated=b_data["text_translated"],
                confidence=b_data["confidence"],
                font_size=b_data.get("font_size", 12),
                font_family=b_data.get("font_family", "Arial"),
                status=b_data["status"]
            )
            # Restore offset if present (custom field not in standard to_dict sometimes?
            # Wait, TextBubble.to_dict doesn't output _text_offset? Check class.)
            # If text_offset is missing in to_dict, we lose position info!
            # Let's check TextBubble class again.
            if "_text_offset" in b_data:
                bubble._text_offset = b_data["_text_offset"]
            page.bubbles.append(bubble)

        # Refresh view
        if self.image_viewer.current_page == page:
            self.image_viewer.current_page = page # Trigger refresh? No.
            # Re-show text items
            self.image_viewer.display_bubbles(page.bubbles) # This clears and redraws boxes
            translated = [b for b in page.bubbles if b.text_translated]
            if translated:
                self.image_viewer.show_text_items(translated, self.pipeline.font_style)
            else:
                self.image_viewer.clear_text_items()

    def _update_undo_buttons(self):
        """Enable/disable buttons based on stack"""
        self.top_bar.undo_btn.setEnabled(len(self.undo_stack) > 0)
        self.top_bar.redo_btn.setEnabled(len(self.redo_stack) > 0)
        if self.undo_stack:
             self.top_bar.undo_btn.setToolTip(f"Undo {self.undo_stack[-1]['description']}")
        else:
             self.top_bar.undo_btn.setToolTip("Nothing to undo")
        if self.redo_stack:
            self.top_bar.redo_btn.setToolTip(f"Redo {self.redo_stack[-1]['description']}")
        else:
            self.top_bar.redo_btn.setToolTip("Nothing to redo")

    def process_all_stages(self):
        """Run all 5 stages on current page using WorkerThread"""
        if not self.project or not self.image_viewer.current_page:
            QMessageBox.warning(self, "Warning", "No page loaded!")
            return

        page = self.image_viewer.current_page
        self.editor_panel.set_progress(0, 0) # Indeterminate progress
        self.editor_panel.set_status("Processing all stages...")
        self.statusbar.showMessage("Processing all stages... (Background)")
        self.editor_panel.setEnabled(False)

        # We need to pass the project and page.
        # Note: Project is not pickleable sometimes if it has complex objects?
        # But here valid args are passed.
        # Careful: process_page modifies page in place.
        # Worker thread modifies the object, but since it's shared memory (QThread in same process),
        # it is technically concurrently modified.
        # Ideally we should work on a copy or ensure no UI access effectively.
        # However, for this simple tool, passing the object is risky but standard for simple PySide apps.
        # Better: Thread safe approach is to have pipeline return a NEW page or dict, and update UI in main thread.
        # pipeline.process_page returns 'page'.

        self.current_worker = WorkerThread(self._run_process_all_task, page, self.project, self.pipeline)
        self.current_worker.signals.result.connect(self._on_process_all_complete)
        self.current_worker.signals.error.connect(self._on_worker_error)
        self.current_worker.signals.finished.connect(self._on_worker_finished)

        # Connect status/progress signals
        self.current_worker.signals.status.connect(self.statusbar.showMessage)
        self.current_worker.signals.status.connect(self.editor_panel.set_status)
        self.current_worker.signals.progress.connect(lambda val: self.editor_panel.set_progress(val, 100))

        self.current_worker.start()

    def _run_process_all_task(self, page, project, pipeline, progress_callback=None):
        """Worker task for process_all_stages"""
        # We should probably clone the page or reload fresh to avoid race conditions with UI if it was trying to read it.
        # But UI is disabled.
        return pipeline.process_page(page, project, progress_callback=progress_callback)

    def _on_process_all_complete(self, processed_page):
        if not self.project or not self.image_viewer.current_page:
            return

        # Update the live page object if different (process_page returns the same instance usually)
        # But let's be safe.
        page = self.image_viewer.current_page
        if processed_page and processed_page.id == page.id:
             # Merge/Update
             page.bubbles = processed_page.bubbles
             page.processed_image_path = processed_page.processed_image_path

        self.image_viewer.display_bubbles(page.bubbles)

        if page.processed_image_path:
            self.image_viewer.load_image(page.processed_image_path)

        self.editor_panel.set_progress(-1)
        self.editor_panel.set_status("All stages complete!")
        self.statusbar.showMessage("Processing complete")

        self.project.save(self.config.PROJECTS_DIR)

    def show_model_settings(self):
        """Show model settings dialog"""
        dialog = SettingsDialog(self.config, self)
        if dialog.exec():
            self.statusbar.showMessage("Applying new settings...")
            try:
                self.pipeline = ScanlationPipeline(self.config)
                self.statusbar.showMessage("Settings applied", 5000)  # 5 seconds
            except Exception as e:
                self.statusbar.showMessage("Settings failed to apply")
                QMessageBox.warning(
                    self,
                    "Settings Error",
                    f"Failed to apply some settings: {e}\n\nUsing previous configuration."
                )

    def show_download_models(self):
        """Show download models dialog"""
        dialog = DownloadModelsDialog(self)
        dialog.exec()

    def show_about(self):
        """Show about dialog"""
        from src.gui.dialogs.about_dialog import AboutDialog
        dialog = AboutDialog(self)
        dialog.exec()


    def open_batch_dialog(self):
        """Open batch processing dialog"""
        if not self.project:
            QMessageBox.warning(self, "No Project", "Please load a project first.")
            return

        dialog = BatchProcessDialog(self.project, self)
        if dialog.exec():
            # Dialog accepted, get config and start processing
            config = dialog.get_config()
            self._run_batch_process(config)

    def _run_batch_process(self, batch_config):
        """Run batch processing using BatchProcessor"""
        pages = batch_config["pages"]
        parallel = batch_config["parallel"]
        max_workers = batch_config["max_workers"]

        if not pages:
            return

        self.editor_panel.set_status(f"Batch processing {len(pages)} pages...")
        self.statusbar.showMessage("Initializing batch process...")

        # Disable UI
        self.editor_panel.setEnabled(False)
        self.image_viewer.setEnabled(False)

        self.current_worker = WorkerThread(self._execute_batch_task,
                                         self.pipeline,
                                         pages,
                                         self.project,
                                         parallel,
                                         max_workers)

        self.current_worker.signals.result.connect(self._on_batch_complete)
        self.current_worker.signals.error.connect(self._on_worker_error)
        self.current_worker.signals.finished.connect(self._on_worker_finished)
        self.current_worker.signals.progress.connect(self._on_batch_progress)
        self.current_worker.signals.status.connect(self._on_batch_status)

        self.current_worker.start()

    def _execute_batch_task(self, pipeline, pages, project, parallel, max_workers, progress_callback=None):
        """Worker task for batch processing"""
        from ..core.batch_processor import BatchProcessor, BatchProgress

        processor = BatchProcessor(pipeline)

        # Define internal callback to bridge BatchProcessor -> WorkerSignals
        def internal_callback(progress: BatchProgress):
            if progress_callback:
                # Update status message
                msg = f"Page {progress.current_page}/{progress.total_pages}: {progress.current_status.value}"
                progress_callback(msg, int(progress.percent_complete))

        if parallel:
            return processor.process_pages_parallel(pages, project, max_workers, internal_callback)
        else:
            return processor.process_pages(pages, project, internal_callback)

    def _on_batch_progress(self, percent):
        """Update progress bar if we had one, or status bar"""
        pass

    def _on_batch_status(self, msg):
        self.statusbar.showMessage(msg)
        self.editor_panel.set_status(msg)

    def _on_batch_complete(self, results):
        """Batch processing finished"""
        self.statusbar.showMessage(f"Batch processing complete. Processed {len(results)} pages.")
        self.editor_panel.set_status("Batch complete")
        self.editor_panel.setEnabled(True)
        self.image_viewer.setEnabled(True)

        self.project.save(self.config.PROJECTS_DIR)

        # Reload current page to show changes
        if self.image_viewer.current_page:
            self.load_page(self.image_viewer.current_page)

        QMessageBox.information(self, "Batch Complete", f"Successfully processed {len(results)} pages.")
