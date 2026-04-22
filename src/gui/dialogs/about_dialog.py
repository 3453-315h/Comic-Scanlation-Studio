"""
About Dialog - Comic Scanlation Studio
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QWidget, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QDesktopServices
from PySide6.QtCore import Qt, QUrl
from pathlib import Path
from ...core.config import Config

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = Config()
        self.setWindowTitle("About Comic Scanlation Studio")
        self.setMinimumWidth(500)
        self.setFixedWidth(500)
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 20)
        layout.setSpacing(0)
        
        # 1. Splash Image Header
        header_container = QWidget()
        header_container.setStyleSheet("background-color: #282c34;")
        header_layout = QVBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        splash_path = Path(__file__).parent.parent.parent.parent / "assets" / "splash.png"
        if splash_path.exists():
            pixmap = QPixmap(str(splash_path))
            # Scale to fit width, keep aspect ratio
            scaled = pixmap.scaledToWidth(500, Qt.TransformationMode.SmoothTransformation)
            
            splash_label = QLabel()
            splash_label.setPixmap(scaled)
            splash_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            header_layout.addWidget(splash_label)
        
        layout.addWidget(header_container)
        
        # 2. Content
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(30, 20, 30, 20)
        content_layout.setSpacing(10)
        
        # Title
        title = QLabel("Comic Scanlation Studio")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #ffffff;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(title)
        
        # Version
        version = QLabel(f"Version {self.config.APP_VERSION}")
        version.setStyleSheet("font-size: 14px; color: #abb2bf;")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(version)
        
        # GitHub Link
        github_url = "https://github.com/3453-315h/Comic-Scanlation-Studio"
        github_link = QLabel(f"<a href='{github_url}' style='color: #61afef; text-decoration: none;'>View on GitHub</a>")
        github_link.setTextFormat(Qt.TextFormat.RichText)
        github_link.setOpenExternalLinks(True)
        github_link.setAlignment(Qt.AlignmentFlag.AlignCenter)
        github_link.setCursor(Qt.CursorShape.PointingHandCursor)
        content_layout.addWidget(github_link)
        
        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("background-color: #3e4451; margin: 10px 0;")
        content_layout.addWidget(line)
        
        # Description
        desc_text = """
        <p style='color: #dcdfe4; font-size: 13px; line-height: 1.4;'>
        A modern tool for translating comics and manga with AI-powered features:
        </p>
        <ul style='color: #dcdfe4; margin-left: -20px;'>
        <li><b>Detection</b> - YOLO-based text detection</li>
        <li><b>OCR</b> - MangaOCR (JP) & EasyOCR (Multi)</li>
        <li><b>Translation</b> - NLLB, OPUS, DeepL, OpenAI</li>
        <li><b>Inpainting</b> - LaMa AI text removal</li>
        </ul>
        <p style='color: #98c379; text-align: center; margin-top: 15px;'>
        Built with PySide6, PyTorch, and ❤️
        </p>
        """
        
        description = QLabel(desc_text)
        description.setTextFormat(Qt.TextFormat.RichText)
        description.setWordWrap(True)
        content_layout.addWidget(description)
        
        layout.addLayout(content_layout)
        
        # 3. Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(30, 0, 30, 0)
        
        close_btn = QPushButton("Close")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #61afef;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #528bff;
            }
        """)
        close_btn.clicked.connect(self.accept)
        
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
