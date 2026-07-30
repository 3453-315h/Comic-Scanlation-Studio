"""
Editor Panel Widget - Right Sidebar

Workflow stage buttons and translation controls matching 8-bit-magic-wand's ComicEditor.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QProgressBar, QSpinBox, QComboBox,
    QTextEdit, QGroupBox, QCheckBox
)
from PySide6.QtCore import Signal, Qt
from typing import Optional


class WorkflowButton(QPushButton):
    """Styled button for workflow stages"""
    
    def __init__(self, emoji: str, title: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        self.setProperty("class", "workflow-button")
        self.setMinimumHeight(56)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self._title = title
        self._subtitle = subtitle
        self._emoji = emoji
        self._update_text()
        
    def _update_text(self):
        text = f"{self._emoji}  {self._title}"
        if self._subtitle:
            text += f"\n     {self._subtitle}"
        self.setText(text)
        
    def set_subtitle(self, text: str):
        self._subtitle = text
        self._update_text()


class EditorPanel(QWidget):
    """Right sidebar with workflow controls and settings"""
    
    # Signals for actions
    detect_clicked = Signal()
    ocr_clicked = Signal()
    edit_text_clicked = Signal()
    translate_clicked = Signal()
    inpaint_clicked = Signal()
    imprint_clicked = Signal()
    export_clicked = Signal()  # Export final image with text
    process_all_clicked = Signal()
    add_bubble_toggled = Signal(bool)
    
    # Font settings changed
    font_changed = Signal(str, int)  # family, size
    font_bold_clicked = Signal()
    font_italic_clicked = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("EditorPanel")
        self.setMinimumWidth(280)
        self.setMaximumWidth(360)
        self._init_ui()
    
    def _init_ui(self):
        # Scroll area for content
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Header
        header = QLabel("WORKFLOW")
        header.setObjectName("SectionHeader")
        header.setStyleSheet("font-size: 11px; font-weight: bold; color: #8c8d8e; text-transform: uppercase;")
        layout.addWidget(header)
        
        # Workflow Buttons
        self.detect_btn = WorkflowButton("🔍", "Detect Speech Bubbles", "Find text regions")
        self.detect_btn.clicked.connect(self.detect_clicked.emit)
        layout.addWidget(self.detect_btn)
        
        # Add Bubble Button (Manual Creation)
        self.add_bubble_btn = QPushButton("➕ Add Bubble")
        self.add_bubble_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_bubble_btn.setCheckable(True)
        self.add_bubble_btn.setObjectName("SecondaryButton")
        self.add_bubble_btn.clicked.connect(self._on_add_bubble_toggled)
        layout.addWidget(self.add_bubble_btn)
        
        self.ocr_btn = WorkflowButton("📝", "OCR Text", "OCR recognition")
        self.ocr_btn.clicked.connect(self.ocr_clicked.emit)
        layout.addWidget(self.ocr_btn)
        
        # Edit Text Button (Small)
        self.edit_text_btn = QPushButton("✏️ Edit Text")
        self.edit_text_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.edit_text_btn.setObjectName("SecondaryButton") 
        self.edit_text_btn.clicked.connect(self.edit_text_clicked.emit)
        layout.addWidget(self.edit_text_btn)
        
        self.translate_btn = WorkflowButton("🌐", "Translate", "Convert to target language")
        self.translate_btn.clicked.connect(self.translate_clicked.emit)
        layout.addWidget(self.translate_btn)
        
        self.inpaint_btn = WorkflowButton("🎨", "Inpaint", "Remove original text")
        self.inpaint_btn.clicked.connect(self.inpaint_clicked.emit)
        layout.addWidget(self.inpaint_btn)
        
        self.imprint_btn = WorkflowButton("✍️", "Imprint", "Render translated text")
        self.imprint_btn.clicked.connect(self.imprint_clicked.emit)
        layout.addWidget(self.imprint_btn)
        
        self.export_btn = WorkflowButton("💾", "Export", "Save final image with text")
        self.export_btn.clicked.connect(self.export_clicked.emit)
        layout.addWidget(self.export_btn)
        
        # Separator
        layout.addSpacing(8)
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #37393c;")
        layout.addWidget(line)
        layout.addSpacing(8)
        
        # Process All Button
        self.process_all_btn = QPushButton("▶️  Process All Stages")
        self.process_all_btn.setObjectName("PrimaryButton")
        self.process_all_btn.setMinimumHeight(48)
        self.process_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.process_all_btn.clicked.connect(self.process_all_clicked.emit)
        layout.addWidget(self.process_all_btn)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p% - %v/%m")
        layout.addWidget(self.progress_bar)
        
        # Font Settings Section
        layout.addSpacing(16)
        font_header = QLabel("FONT SETTINGS")
        font_header.setStyleSheet("font-size: 11px; font-weight: bold; color: #8c8d8e;")
        layout.addWidget(font_header)
        
        font_row = QHBoxLayout()
        
        self.font_family = QComboBox()
        self.font_family.addItems([
            "Arial", "Comic Sans MS", "CC Wild Words", 
            "Anime Ace", "Bangers", "Impact"
        ])
        self.font_family.currentTextChanged.connect(self._on_font_changed)
        font_row.addWidget(self.font_family, stretch=2)
        
        self.font_size = QSpinBox()
        self.font_size.setRange(8, 72)
        self.font_size.setValue(24)
        self.font_size.setSuffix("px")
        self.font_size.valueChanged.connect(self._on_font_changed)
        font_row.addWidget(self.font_size, stretch=1)
        
        layout.addLayout(font_row)
        
        # Style buttons (Bold/Italic)
        style_row = QHBoxLayout()
        
        self.bold_btn = QPushButton("B")
        self.bold_btn.setFixedSize(32, 32)
        self.bold_btn.setCheckable(True)
        self.bold_btn.setStyleSheet("font-weight: bold;")
        self.bold_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bold_btn.setToolTip("Bold")
        self.bold_btn.setAccessibleName("Bold")
        self.bold_btn.clicked.connect(self.font_bold_clicked.emit)
        style_row.addWidget(self.bold_btn)
        
        self.italic_btn = QPushButton("I")
        self.italic_btn.setFixedSize(32, 32)
        self.italic_btn.setCheckable(True)
        self.italic_btn.setStyleSheet("font-style: italic;")
        self.italic_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.italic_btn.setToolTip("Italic")
        self.italic_btn.setAccessibleName("Italic")
        self.italic_btn.clicked.connect(self.font_italic_clicked.emit)
        style_row.addWidget(self.italic_btn)
        
        style_row.addStretch()
        layout.addLayout(style_row)
        
        # Auto-fit checkbox
        self.auto_fit_check = QCheckBox("Auto-fit text to bubble")
        self.auto_fit_check.setChecked(True)
        layout.addWidget(self.auto_fit_check)
        
        # Status Section
        layout.addSpacing(16)
        status_header = QLabel("STATUS")
        status_header.setStyleSheet("font-size: 11px; font-weight: bold; color: #8c8d8e;")
        layout.addWidget(status_header)
        
        self.status_label = QLabel("Ready")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: #8c8d8e; padding: 8px; background: #141619; border-radius: 4px;")
        layout.addWidget(self.status_label)
        
        # Stretch to push content to top
        layout.addStretch()
        
        scroll.setWidget(content)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
    
    def _on_font_changed(self):
        self.font_changed.emit(
            self.font_family.currentText(),
            self.font_size.value()
        )

    def update_font_ui(self, family: str, size: int):
        """Update the UI without triggering font_changed signals"""
        self.font_family.blockSignals(True)
        self.font_size.blockSignals(True)
        
        index = self.font_family.findText(family)
        if index >= 0:
            self.font_family.setCurrentIndex(index)
        self.font_size.setValue(size)
        
        self.font_family.blockSignals(False)
        self.font_size.blockSignals(False)

    def _on_add_bubble_toggled(self, checked: bool):
        """Handle add bubble toggle"""
        self.add_bubble_toggled.emit(checked)
        if checked:
            self.add_bubble_btn.setText("Cancel Adding")
            self.add_bubble_btn.setStyleSheet("background-color: #3d3f42; border: 1px solid #7FBBFF;")
        else:
            self.add_bubble_btn.setText("➕ Add Bubble")
            self.add_bubble_btn.setStyleSheet("")
    
    def set_status(self, message: str):
        """Update status label"""
        self.status_label.setText(message)
    
    def set_progress(self, value: int, maximum: int = 100):
        """Update progress bar"""
        if value < 0:
            self.progress_bar.setVisible(False)
        else:
            self.progress_bar.setVisible(True)
            self.progress_bar.setMaximum(maximum)
            self.progress_bar.setValue(value)
    
    def update_button_status(self, stage: str, count: int):
        """Update workflow button subtitles with counts"""
        button_map = {
            "detect": self.detect_btn,
            "ocr": self.ocr_btn,
            "translate": self.translate_btn,
            "inpaint": self.inpaint_btn,
            "imprint": self.imprint_btn,
        }
        
        if stage in button_map:
            button_map[stage].set_subtitle(f"{count} items")
