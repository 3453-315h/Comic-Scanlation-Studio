"""
TopBar Widget - Navigation and Controls

Matches 8-bit-magic-wand TopBar with Home, Reset, and settings.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QWidget,
)


class TopBar(QWidget):
    """Top navigation bar with project controls"""

    # Signals
    home_clicked = Signal()
    reset_clicked = Signal()
    undo_clicked = Signal()
    redo_clicked = Signal()
    settings_clicked = Signal()
    zoom_in_clicked = Signal()
    zoom_out_clicked = Signal()
    reveal_toggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TopBar")
        self.setFixedHeight(52)
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        # Left section - Navigation
        self.home_btn = QPushButton("➕ New Project")
        self.home_btn.setObjectName("TopBarButton")
        self.home_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.home_btn.setAccessibleName("New Project")
        self.home_btn.setToolTip("Start a new project")
        self.home_btn.clicked.connect(self.home_clicked.emit)
        layout.addWidget(self.home_btn)

        # Separator
        separator1 = QLabel("|")
        separator1.setStyleSheet("color: #37393c; margin: 0 8px;")
        layout.addWidget(separator1)

        self.reset_btn = QPushButton("Reset Session")
        self.reset_btn.setObjectName("TopBarButton")
        self.reset_btn.setStyleSheet("text-decoration: underline;")
        self.reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_btn.setAccessibleName("Reset Session")
        self.reset_btn.setToolTip("Reset the current session")
        self.reset_btn.clicked.connect(self.reset_clicked.emit)
        layout.addWidget(self.reset_btn)

        # Undo/Redo
        self.undo_btn = QPushButton("↩️ Undo")
        self.undo_btn.setObjectName("TopBarButton")
        self.undo_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.undo_btn.setAccessibleName("Undo")
        self.undo_btn.setToolTip("Undo last action")
        self.undo_btn.clicked.connect(self.undo_clicked.emit)
        layout.addWidget(self.undo_btn)

        self.redo_btn = QPushButton("↪️ Redo")
        self.redo_btn.setObjectName("TopBarButton")
        self.redo_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.redo_btn.setAccessibleName("Redo")
        self.redo_btn.setToolTip("Redo last action")
        self.redo_btn.clicked.connect(self.redo_clicked.emit)
        layout.addWidget(self.redo_btn)

        # Center - Project Title
        layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        self.project_label = QLabel("Comic Scanlation Studio")
        self.project_label.setObjectName("ProjectTitle")
        self.project_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.project_label)

        layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        # Right section - Options
        self.zoom_out_btn = QPushButton("➖")
        self.zoom_out_btn.setObjectName("TopBarButton")
        self.zoom_out_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.zoom_out_btn.setAccessibleName("Zoom Out")
        self.zoom_out_btn.setToolTip("Zoom Out")
        self.zoom_out_btn.clicked.connect(self.zoom_out_clicked.emit)
        layout.addWidget(self.zoom_out_btn)

        self.zoom_in_btn = QPushButton("➕")
        self.zoom_in_btn.setObjectName("TopBarButton")
        self.zoom_in_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.zoom_in_btn.setAccessibleName("Zoom In")
        self.zoom_in_btn.setToolTip("Zoom In")
        self.zoom_in_btn.clicked.connect(self.zoom_in_clicked.emit)
        layout.addWidget(self.zoom_in_btn)

        # Separator
        separator3 = QLabel("|")
        separator3.setStyleSheet("color: #37393c; margin: 0 8px;")
        layout.addWidget(separator3)

        self.reveal_checkbox = QCheckBox("Reveal on Hover")
        self.reveal_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reveal_checkbox.setAccessibleName("Reveal on Hover")
        self.reveal_checkbox.setToolTip("Toggle to reveal original text on hover")
        self.reveal_checkbox.toggled.connect(self.reveal_toggled.emit)
        layout.addWidget(self.reveal_checkbox)

        separator2 = QLabel("|")
        separator2.setStyleSheet("color: #37393c; margin: 0 8px;")
        layout.addWidget(separator2)

        self.settings_btn = QPushButton("⚙️")
        self.settings_btn.setObjectName("TopBarButton")
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_btn.setAccessibleName("Settings")
        self.settings_btn.setToolTip("Settings")
        self.settings_btn.clicked.connect(self.settings_clicked.emit)
        layout.addWidget(self.settings_btn)

    def set_project_name(self, name: str):
        """Update the displayed project name"""
        self.project_label.setText(name if name else "Comic Scanlation Studio")
