"""
Image Viewer Widget - Comic Translation Studio

Displays images with text bubble overlays and handles zoom/pan.
"""

from pathlib import Path

import cv2
import shiboken6
from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QGraphicsRectItem, QGraphicsScene, QGraphicsTextItem, QGraphicsView

from ...core.project import TextBubble


class ImageViewer(QGraphicsView):
    # Signals
    request_save_state = Signal()  # Request main window to save state for undo
    bubble_created = Signal(object) # QRectF

    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene()
        self.setScene(self.scene)

        self.current_image: QPixmap | None = None
        self.current_page: object | None = None
        self.bubble_items: list = []

        # Draw mode state
        self._draw_mode = False
        self._draw_start = None
        self._temp_rect_item = None

        # Store image data to prevent garbage collection
        self._image_data = None

        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

    def set_draw_mode(self, enabled: bool):
        """Enable/disable bubble drawing mode"""
        self._draw_mode = enabled
        if enabled:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            # Restore zoom if needed? No, just keep current scale.
            self.setCursor(Qt.CursorShape.ArrowCursor)

            # Clean up if cancelled mid-draw
            if self._temp_rect_item:
                self.scene.removeItem(self._temp_rect_item)
                self._temp_rect_item = None
                self._draw_start = None

    def zoom_in(self):
        """Zoom in by 20%"""
        self.scale(1.2, 1.2)

    def zoom_out(self):
        """Zoom out by 20%"""
        self.scale(1/1.2, 1/1.2)

    def mousePressEvent(self, event):
        """Handle mouse press for drawing or panning"""
        if self._draw_mode and event.button() == Qt.MouseButton.LeftButton:
            self._draw_start = self.mapToScene(event.pos())

            # Create temp rect
            self._temp_rect_item = QGraphicsRectItem()
            self._temp_rect_item.setPen(QPen(QColor(0, 255, 0), 2, Qt.PenStyle.DashLine))
            self._temp_rect_item.setBrush(QColor(0, 255, 0, 50))
            self.scene.addItem(self._temp_rect_item)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse move for drawing"""
        if self._draw_mode and self._draw_start:
            current_pos = self.mapToScene(event.pos())
            rect = QRectF(self._draw_start, current_pos).normalized()
            self._temp_rect_item.setRect(rect)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle mouse release to finalize drawing"""
        if self._draw_mode and self._draw_start and event.button() == Qt.MouseButton.LeftButton:
            current_pos = self.mapToScene(event.pos())
            rect = QRectF(self._draw_start, current_pos).normalized()

            # Cleanup temp item
            if self._temp_rect_item:
                self.scene.removeItem(self._temp_rect_item)
                self._temp_rect_item = None

            self._draw_start = None

            # Emit signal if rect is valid
            if rect.width() > 10 and rect.height() > 10:
                self.bubble_created.emit(rect)
        else:
            super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        """Handle key press events"""
        if event.key() == Qt.Key_Delete:
            self.delete_selected_bubbles()
        else:
            super().keyPressEvent(event)

    def load_image(self, image_path: Path):
        """Load and display an image"""
        img = cv2.imread(str(image_path))
        if img is None:
            return

        # Store a copy to prevent data lifetime issues (prevent GC)
        self._image_data = img.copy()
        height, width, channel = self._image_data.shape
        bytes_per_line = 3 * width

        q_img = QImage(
            self._image_data.data, width, height, bytes_per_line,
            QImage.Format.Format_BGR888
        ).copy()  # Deep copy to ensure data ownership and prevent segfaults

        self.current_image = QPixmap.fromImage(q_img)

        # Clear scene (this also clears bubble_items)
        self._clear_bubbles()
        self.scene.clear()

        self.scene.addPixmap(self.current_image)

        # Set scene rect to image size
        self.scene.setSceneRect(0, 0, width, height)
        self.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def _clear_bubbles(self):
        """Safely clear all bubble overlay items"""
        for item in self.bubble_items:
            try:
                # Check if the C++ object still exists before removing
                if shiboken6.isValid(item):
                    self.scene.removeItem(item)
            except (RuntimeError, Exception):
                # Item already deleted by Qt
                pass
        self.bubble_items.clear()

    def display_bubbles(self, bubbles: list[TextBubble]):
        """Display detected bubbles as overlay rectangles"""
        # Safely clear existing bubble items
        self._clear_bubbles()

        if not self.current_image:
            return

        # Draw each bubble
        for bubble in bubbles:
            x1, y1, x2, y2 = bubble.bbox

            # Create scalable rectangle item
            # from ..items.resizable_rect import ResizableRectItem (Import at top)
            from ..items.resizable_rect import ResizableRectItem

            rect = QRectF(x1, y1, x2-x1, y2-y1)
            rect_item = ResizableRectItem(rect, bubble_ref=bubble)

            # Style based on status
            if bubble.status == "failed":
                pen = QPen(QColor(255, 0, 0), 2)
            elif bubble.status == "translated":
                pen = QPen(QColor(0, 255, 0), 2)
            else:
                pen = QPen(QColor(0, 150, 255), 2)

            pen.setCosmetic(True)
            rect_item.setPen(pen)
            rect_item.setBrush(QColor(0, 150, 255, 30))

            self.scene.addItem(rect_item)
            self.bubble_items.append(rect_item)

            # Add text label if there's text
            label_text = bubble.text_original or ""
            if label_text:
                display_text = label_text[:20] + "..." if len(label_text) > 20 else label_text
                text_item = QGraphicsTextItem(display_text)
                text_item.setPos(x1, y1 - 20)
                text_item.setFont(QFont("Arial", 10))
                text_item.setDefaultTextColor(QColor(255, 255, 255))

                self.scene.addItem(text_item)
                self.bubble_items.append(text_item)

    def delete_selected_bubbles(self):
        """Remove selected bubbles from scene and data"""
        if not self.current_page:
            return

        items_to_remove = self.scene.selectedItems()
        if not items_to_remove:
            return

        # Filter for ResizableRectItems
        from ..items.resizable_rect import ResizableRectItem
        bubbles_to_remove = []

        for item in items_to_remove:
            if isinstance(item, ResizableRectItem) and item.bubble_ref:
                bubbles_to_remove.append(item.bubble_ref)
                self.scene.removeItem(item)
                if item in self.bubble_items:
                    self.bubble_items.remove(item)

        # Update page data
        if bubbles_to_remove:
            self.current_page.bubbles = [b for b in self.current_page.bubbles if b not in bubbles_to_remove]
            return True
        return False

    def update_display(self):
        """Refresh the currently displayed bubbles"""
        if self.current_page and hasattr(self.current_page, 'bubbles'):
            self.display_bubbles(self.current_page.bubbles)

    def set_reveal_mode(self, enabled: bool):
        """Toggle reveal-on-hover mode for bubble overlays"""
        # When enabled, bubbles are hidden until hovered
        for item in self.bubble_items:
            if hasattr(item, 'setOpacity'):
                item.setOpacity(0.3 if enabled else 1.0)

    # ========== Text Editing Features ==========

    def show_text_items(self, bubbles, font_style=None):
        """
        Display editable text items for translated bubbles.
        
        Args:
            bubbles: List of TextBubble objects with text_translated
            font_style: Optional FontStyle for styling
        """
        from ..items.text_edit_item import TextEditItem

        # Clear existing text items
        self.clear_text_items()

        if not hasattr(self, 'text_items'):
            self.text_items = []

        for bubble in bubbles:
            if not bubble.text_translated:
                continue

            # Get bubble dimensions
            x1, y1, x2, y2 = bubble.bbox
            bubble_width = x2 - x1
            bubble_height = y2 - y1

            # Create text item
            text_item = TextEditItem(bubble.text_translated, bubble_ref=bubble)

            # Apply font family / color from style (but NOT size yet — we need to auto-fit first)
            if font_style:
                text_item.set_style(
                    font_family=font_style.font_family,
                    color=font_style.color
                )

            # Determine position and font size
            if bubble.text_offset:
                # --- Bubble has been manually positioned — restore exactly ---
                text_item.setPos(*bubble.text_offset)
                saved_size = bubble.font_size if (bubble.font_size and bubble.font_size > 0) else 14
                text_item.set_style(font_size=saved_size)
                text_item.setTextWidth(bubble_width - 20)
            else:
                # --- Fresh bubble — auto-fit font size and center within bbox ---
                # proportional padding (matches auto_fit_to_bubble's default)
                padding = max(8, min(24, int(min(bubble_width, bubble_height) * 0.12)))
                text_height = text_item.auto_fit_to_bubble(bubble_width, bubble_height)

                # Horizontal: left edge of bubble + padding (text width already constrains right)
                text_x = x1 + padding

                # Vertical: center the text block within the bubble
                inner_height = bubble_height - padding * 2
                v_offset = (inner_height - text_height) / 2.0
                text_y = y1 + padding + max(0.0, v_offset)

                text_item.setPos(text_x, text_y)
                # Persist the auto-computed position so font-change doesn't reset it
                text_item._sync_to_bubble()

            # Connect signals for undo/redo
            text_item.signals.interactionStarted.connect(self.request_save_state.emit)

            self.scene.addItem(text_item)
            self.text_items.append(text_item)

    def clear_text_items(self):
        """Remove all text items from scene"""
        if not hasattr(self, 'text_items'):
            self.text_items = []
            return

        for item in self.text_items:
            try:
                if shiboken6.isValid(item):
                    self.scene.removeItem(item)
            except:
                pass
        self.text_items.clear()

    def _get_selected_text_item(self):
        """Get the single selected text item, if any"""
        selected = self.scene.selectedItems()
        from ..items.text_edit_item import TextEditItem
        for item in selected:
            if isinstance(item, TextEditItem):
                return item
        return None

    def toggle_bold_selection(self):
        """Toggle bold on selected text item"""
        item = self._get_selected_text_item()
        if item:
            item.toggle_bold()

    def toggle_italic_selection(self):
        """Toggle italic on selected text item"""
        item = self._get_selected_text_item()
        if item:
            item.toggle_italic()

    def clear_content(self):
        """Clear image and all overlays"""
        self.current_image = None
        self.current_page = None
        self._clear_bubbles()
        self.clear_text_items()
        self.scene.clear()
        self._image_data = None

    def export_with_text(self):
        """
        Render the scene (image + text items) to a QImage.
        
        Returns:
            QImage with text flattened onto the image
        """
        if not self.current_image:
            return None

        # Get scene rectangle
        rect = self.scene.sceneRect()

        # Create image to render into
        result = QImage(
            int(rect.width()), int(rect.height()),
            QImage.Format.Format_RGB888
        )
        result.fill(QColor(255, 255, 255))

        # Render scene to image
        painter = QPainter(result)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # Hide bubble overlays temporarily for clean export
        for item in self.bubble_items:
            if hasattr(item, 'setVisible'):
                item.setVisible(False)

        self.scene.render(painter)
        painter.end()

        # Restore bubble visibility
        for item in self.bubble_items:
            if hasattr(item, 'setVisible'):
                item.setVisible(True)

        return result

    def has_text_items(self) -> bool:
        """Check if there are text items on the canvas"""
        return hasattr(self, 'text_items') and len(self.text_items) > 0
