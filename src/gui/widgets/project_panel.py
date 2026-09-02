
# Add at the top with other imports
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QListWidget, QPushButton, QVBoxLayout, QWidget

from ...core.project import Page, Project


class ProjectPanel(QWidget):
    page_selected = Signal(Page)

    def __init__(self):
        super().__init__()
        self.project: Project | None = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Project info
        self.project_label = QLabel("No Project")
        self.project_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.project_label)

        # Pages list
        self.pages_list = QListWidget()
        self.pages_list.itemClicked.connect(self.on_page_clicked)
        layout.addWidget(self.pages_list)

        # Buttons
        btn_layout = QVBoxLayout()

        self.add_pages_btn = QPushButton("Add Pages")
        self.add_pages_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_pages_btn.clicked.connect(self.on_add_pages)
        btn_layout.addWidget(self.add_pages_btn)

        self.sync_btn = QPushButton("Sync to Cloud")
        self.sync_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sync_btn.clicked.connect(self.on_sync)
        btn_layout.addWidget(self.sync_btn)

        layout.addLayout(btn_layout)

    def set_project(self, project: Project):
        self.project = project
        self.project_label.setText(f"Project: {project.name}")
        self.refresh_pages_list()

    def refresh_pages_list(self):
        self.pages_list.clear()
        if self.project:
            for page in self.project.pages.values():
                item_text = f"Page {page.id} - {Path(page.file_path).name}"
                self.pages_list.addItem(item_text)

    def add_page(self, page: Page):
        self.refresh_pages_list()

    def on_page_clicked(self, item):
        if self.project:
            # Find the page corresponding to the clicked item
            # Simplified: use index for now
            index = self.pages_list.row(item)
            pages = list(self.project.pages.values())
            if 0 <= index < len(pages):
                self.page_selected.emit(pages[index])

    def on_add_pages(self):
        # This would trigger file dialog in main window
        pass

    def on_sync(self):
        if self.project:
            # Placeholder for Firebase sync
            print("Syncing project to Firebase...")
