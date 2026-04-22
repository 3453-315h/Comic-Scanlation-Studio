"""
Page Carousel Widget - Bottom Thumbnail Strip

Horizontal scrolling page thumbnails matching 8-bit-magic-wand's Carousel.
"""

from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QSizePolicy
)
from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtGui import QPixmap, QImage
from typing import Optional, List
import cv2
import numpy as np


class PageThumbnail(QWidget):
    """Individual page thumbnail with selection and remove"""
    
    clicked = Signal(str)  # page_id
    remove_clicked = Signal(str)  # page_id
    
    THUMB_SIZE = 120
    
    def __init__(self, page_id: str, image_path: Path, index: int, parent=None):
        super().__init__(parent)
        self.page_id = page_id
        self.image_path = image_path
        self.index = index
        self._active = False
        
        self.setObjectName("PageThumbnail")
        self.setFixedSize(self.THUMB_SIZE + 4, self.THUMB_SIZE + 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)
        
        # Image container
        self.image_container = QWidget()
        self.image_container.setFixedSize(self.THUMB_SIZE, self.THUMB_SIZE)
        container_layout = QVBoxLayout(self.image_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        # Thumbnail image
        self.image_label = QLabel()
        self.image_label.setFixedSize(self.THUMB_SIZE, self.THUMB_SIZE)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("""
            border-radius: 8px;
            background: #141619;
        """)
        container_layout.addWidget(self.image_label)
        
        layout.addWidget(self.image_container)
        
        # Page number label
        self.number_label = QLabel(f"#{self.index + 1}")
        self.number_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.number_label.setStyleSheet("font-size: 10px; color: #8c8d8e;")
        layout.addWidget(self.number_label)
        
        # Remove button (overlay)
        self.remove_btn = QPushButton("✕", self)
        self.remove_btn.setFixedSize(20, 20)
        self.remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        # self.remove_btn.setToolTip("Delete Page") # Remove tooltip to avoid "popup" confusion
        self.remove_btn.setStyleSheet("""
            QPushButton {
                background: rgba(200, 0, 0, 0.8);
                color: white;
                border-radius: 10px;
                font-size: 10px;
                font-weight: bold;
                border: 1px solid rgba(255,255,255,0.5);
                padding: 0;
                margin: 0;
            }
            QPushButton:hover {
                background: rgba(255, 0, 0, 1.0);
            }
        """)
        self.remove_btn.clicked.connect(lambda: self.remove_clicked.emit(self.page_id))
        self.remove_btn.hide()
        
        # Load thumbnail
        self._load_thumbnail()
        
        # Update style
        self._update_style()
    
    def _load_thumbnail(self):
        """Load and scale the image thumbnail"""
        try:
            # Read image with OpenCV
            image = cv2.imread(str(self.image_path))
            if image is None:
                return
                
            # Scale to fit
            h, w = image.shape[:2]
            scale = self.THUMB_SIZE / max(h, w)
            new_w, new_h = int(w * scale), int(h * scale)
            
            image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Convert to QPixmap
            h, w, ch = image.shape
            bytes_per_line = ch * w
            q_img = QImage(image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(q_img)
            
            self.image_label.setPixmap(pixmap)
            
        except Exception as e:
            self.image_label.setText("?")
    
    def _update_style(self):
        """Update visual style based on active state"""
        if self._active:
            self.setStyleSheet("""
                QWidget#PageThumbnail {
                    border: 3px solid #7FBBFF;
                    border-radius: 10px;
                    background: rgba(127, 187, 255, 0.1);
                }
            """)
            self.remove_btn.move(self.width() - 28, 4)
            self.remove_btn.show() # Show delete on active
            self.remove_btn.raise_()
        else:
            self.setStyleSheet("""
                QWidget#PageThumbnail {
                    border: 2px solid transparent;
                    border-radius: 10px;
                }
                QWidget#PageThumbnail:hover {
                    border-color: #37393c;
                    background: rgba(255, 255, 255, 0.05);
                }
            """)
            if not self.underMouse():
                self.remove_btn.hide()
    
    def resizeEvent(self, event):
        """Update button position on resize"""
        if hasattr(self, 'remove_btn'):
            self.remove_btn.move(self.width() - 28, 4)
        super().resizeEvent(event)
    
    def set_active(self, active: bool):
        """Set whether this thumbnail is the active selection"""
        self._active = active
        self._update_style()
    
    def enterEvent(self, event):
        """Show remove button on hover"""
        self.remove_btn.raise_()
        self.remove_btn.show()
        self.remove_btn.move(self.width() - 28, 4)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Hide remove button when not hovering (unless active)"""
        if not self._active:
            self.remove_btn.hide()
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        """Handle click to select"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.page_id)
        super().mousePressEvent(event)


class PageCarousel(QWidget):
    """Horizontal scrolling page gallery"""
    
    page_selected = Signal(str)  # page_id
    page_removed = Signal(str)  # page_id
    upload_clicked = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PageCarousel")
        self.thumbnails: List[PageThumbnail] = []
        self._active_page_id: Optional[str] = None
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus) # Enable keyboard focus
        self._init_ui()
    
    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        # Upload button (left side)
        upload_container = QWidget()
        upload_layout = QVBoxLayout(upload_container)
        upload_layout.setContentsMargins(0, 0, 0, 0)
        
        self.upload_btn = QPushButton("📁 Upload Images")
        self.upload_btn.setObjectName("PrimaryButton")
        self.upload_btn.setMinimumWidth(140)
        self.upload_btn.setMinimumHeight(48)
        self.upload_btn.clicked.connect(self.upload_clicked.emit)
        upload_layout.addWidget(self.upload_btn, alignment=Qt.AlignmentFlag.AlignTop)
        
        layout.addWidget(upload_container)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setStyleSheet("background: #37393c;")
        separator.setFixedWidth(1)
        layout.addWidget(separator)
        
        # Page gallery container
        gallery_container = QWidget()
        gallery_layout = QVBoxLayout(gallery_container)
        gallery_layout.setContentsMargins(0, 0, 0, 0)
        gallery_layout.setSpacing(4)
        
        # Title
        title = QLabel("PAGE GALLERY")
        title.setStyleSheet("font-size: 11px; font-weight: bold; color: #8c8d8e;")
        gallery_layout.addWidget(title)
        
        # Scroll area for thumbnails
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setFixedHeight(160)
        self.scroll_area.setStyleSheet("background: transparent;")
        
        # Scroll content
        self.scroll_content = QWidget()
        self.scroll_layout = QHBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(4, 4, 4, 4)
        self.scroll_layout.setSpacing(12)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        # Empty state placeholder
        self.empty_label = QLabel("Upload images to get started")
        self.empty_label.setStyleSheet("""
            color: #8c8d8e;
            padding: 40px;
            border: 2px dashed #37393c;
            border-radius: 8px;
        """)
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll_layout.addWidget(self.empty_label)
        
        self.scroll_area.setWidget(self.scroll_content)
        gallery_layout.addWidget(self.scroll_area)
        
        layout.addWidget(gallery_container, stretch=1)
    
    def add_page(self, page_id: str, image_path: Path):
        """Add a page thumbnail to the carousel"""
        # Hide empty state
        self.empty_label.hide()
        
        index = len(self.thumbnails)
        thumb = PageThumbnail(page_id, image_path, index)
        thumb.clicked.connect(self._on_thumbnail_clicked)
        thumb.remove_clicked.connect(self._on_remove_clicked)
        
        self.thumbnails.append(thumb)
        self.scroll_layout.addWidget(thumb)
        
        # Select first page automatically
        if index == 0:
            self.set_active_page(page_id)
    
    def remove_page(self, page_id: str):
        """Remove a page from the carousel"""
        for i, thumb in enumerate(self.thumbnails):
            if thumb.page_id == page_id:
                self.scroll_layout.removeWidget(thumb)
                thumb.deleteLater()
                self.thumbnails.pop(i)
                
                # Update indices
                for j, t in enumerate(self.thumbnails):
                    t.index = j
                    t.number_label.setText(f"#{j + 1}")
                
                # Show empty state if no pages
                if not self.thumbnails:
                    self.empty_label.show()
                
                break
    
    def set_active_page(self, page_id: str):
        """Set the active (selected) page"""
        self._active_page_id = page_id
        
        for thumb in self.thumbnails:
            thumb.set_active(thumb.page_id == page_id)
    
    def clear(self):
        """Remove all pages"""
        for thumb in self.thumbnails:
            self.scroll_layout.removeWidget(thumb)
            thumb.deleteLater()
        
        self.thumbnails.clear()
        self._active_page_id = None
        self.empty_label.show()
    
    def _on_thumbnail_clicked(self, page_id: str):
        """Handle thumbnail click"""
        self.setFocus() # Ensure carousel gets focus for keyboard events
        self.set_active_page(page_id)
        self.page_selected.emit(page_id)
    
    def _on_remove_clicked(self, page_id: str):
        """Handle remove button click"""
        self.page_removed.emit(page_id)

    def keyPressEvent(self, event):
        """Handle keyboard events for deletion"""
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            if self._active_page_id:
                self.page_removed.emit(self._active_page_id)
        super().keyPressEvent(event)
