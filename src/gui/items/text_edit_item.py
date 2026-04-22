"""
TextEditItem - Editable Text Item for Comic Translation Studio

An interactive text item that can be:
- Dragged to reposition
- Double-clicked to edit text inline
- Resized via scroll wheel or context menu
"""

from PySide6.QtWidgets import (
    QGraphicsTextItem, QGraphicsSceneMouseEvent, 
    QGraphicsSceneContextMenuEvent, QMenu, QInputDialog
)
from PySide6.QtCore import Qt, QRectF, Signal, QObject
from PySide6.QtGui import QFont, QColor, QTextCursor, QPainter, QPen, QFontMetrics
from typing import Optional, Any


class TextEditItemSignals(QObject):
    """Signals for TextEditItem (QGraphicsTextItem can't emit signals directly)"""
    textChanged = Signal(str)
    positionChanged = Signal(float, float)
    fontSizeChanged = Signal(int)
    interactionStarted = Signal()  # Request to save state before change


class TextEditItem(QGraphicsTextItem):
    """
    Interactive editable text item for speech bubbles.
    
    Features:
    - Drag to move
    - Double-click to edit text
    - Mouse wheel to resize font
    - Context menu for options
    """
    
    def __init__(self, text: str, bubble_ref: Any = None, parent=None):
        super().__init__(text, parent)
        
        self.bubble_ref = bubble_ref  # Reference to TextBubble data
        self.signals = TextEditItemSignals()
        
        # Default styling
        self._font_size = 16
        self._font_family = "Arial"
        self._text_color = QColor(0, 0, 0)
        
        # Setup
        self.setFlags(
            QGraphicsTextItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsTextItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsTextItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        
        # Apply initial font
        self._apply_font()
        self.setDefaultTextColor(self._text_color)
    
    def _apply_font(self):
        """Apply current font settings"""
        font = QFont(self._font_family, self._font_size)
        self.setFont(font)
    
    def set_style(self, font_family: str = None, font_size: int = None, 
                  color: tuple = None):
        """Set text styling"""
        if font_family:
            self._font_family = font_family
        if font_size:
            self._font_size = font_size
        if color:
            # Expect BGR tuple, convert to QColor (RGB)
            self._text_color = QColor(color[2], color[1], color[0])
            self.setDefaultTextColor(self._text_color)
        
        self._apply_font()
    
    def auto_fit_to_bubble(self, bubble_width: int, bubble_height: int,
                           padding: int = None, line_height: float = 1.2) -> float:
        """
        Calculate and apply the largest font size that fits the text inside the bubble.

        Uses QTextDocument for pixel-accurate multi-line measurement.
        Padding defaults to 12% of the smaller dimension (min 8px, max 24px).

        Returns:
            The rendered text block height in pixels (for vertical centering by caller).
        """
        from PySide6.QtWidgets import QGraphicsTextItem
        from PySide6.QtCore import QSizeF

        text = self.toPlainText().strip()
        if not text:
            return 0.0

        # Proportional padding: 12% of the shorter side, clamped
        if padding is None:
            padding = max(8, min(24, int(min(bubble_width, bubble_height) * 0.12)))

        available_width  = max(10, bubble_width  - padding * 2)
        available_height = max(10, bubble_height - padding * 2)

        # Use a QTextDocument for accurate measurement (handles wrapping, line spacing, etc.)
        from PySide6.QtGui import QTextOption
        from PySide6.QtWidgets import QApplication

        doc = self.document().clone()  # Clone current doc so we can mutate freely

        best_size = 8
        lo, hi = 8, 52

        while lo <= hi:
            mid = (lo + hi) // 2
            font = QFont(self._font_family, mid)
            doc.setDefaultFont(font)
            doc.setTextWidth(available_width)

            text_option = doc.defaultTextOption()
            text_option.setWrapMode(QTextOption.WrapMode.WordWrap)
            text_option.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            doc.setDefaultTextOption(text_option)

            doc.setPlainText(text)

            doc_height = doc.size().height()
            if doc_height <= available_height:
                best_size = mid
                lo = mid + 1
            else:
                hi = mid - 1

        # Apply the winning font size
        self._font_size = best_size
        font = QFont(self._font_family, best_size)
        self.setFont(font)

        # Set alignment to centre
        text_option = self.document().defaultTextOption()
        text_option.setWrapMode(QTextOption.WrapMode.WordWrap)
        text_option.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.document().setDefaultTextOption(text_option)

        self.setTextWidth(available_width)
        self._sync_to_bubble()

        # Return actual rendered height so caller can vertically centre
        return self.document().size().height()
    
    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent):
        """Enable text editing on double-click"""
        self.signals.interactionStarted.emit()
        self.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextEditorInteraction
        )
        self.setFocus()
        # Place cursor at click position
        cursor = self.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        self.setTextCursor(cursor)
        super().mouseDoubleClickEvent(event)
    
        """Handle mouse press - save state for potential move"""
        self.signals.interactionStarted.emit()
        super().mousePressEvent(event)
        
    def mouseReleaseEvent(self, event):
        """Sync position on release"""
        super().mouseReleaseEvent(event)
        self._sync_to_bubble()
    
    def focusOutEvent(self, event):
        """Disable editing when focus is lost"""
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        cursor = self.textCursor()
        cursor.clearSelection()
        self.setTextCursor(cursor)
        
        # Sync text back to bubble
        self._sync_to_bubble()
        super().focusOutEvent(event)
    
    def wheelEvent(self, event):
        """Resize font with mouse wheel"""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.signals.interactionStarted.emit()
            delta = event.delta() if hasattr(event, 'delta') else event.angleDelta().y()
            if delta > 0:
                self._font_size = min(72, self._font_size + 2)
            else:
                self._font_size = max(8, self._font_size - 2)
            
            self._apply_font()
            self.signals.fontSizeChanged.emit(self._font_size)
            self._sync_to_bubble()  # Sync font size change
            event.accept()
        else:
            super().wheelEvent(event)
    
    def contextMenuEvent(self, event: QGraphicsSceneContextMenuEvent):
        """Show context menu for text options"""
        menu = QMenu()
        
        # Font size submenu
        size_menu = menu.addMenu("Font Size")
        for size in [10, 12, 14, 16, 18, 20, 24, 28, 32, 36, 48]:
            action = size_menu.addAction(f"{size}pt")
            action.triggered.connect(lambda checked, s=size: self._set_font_size(s))
        
        menu.addSeparator()
        
        # Edit text
        edit_action = menu.addAction("Edit Text...")
        edit_action.triggered.connect(self._edit_text_dialog)
        
        # Delete
        delete_action = menu.addAction("Delete")
        delete_action.triggered.connect(self._delete_self)
        
        menu.exec_(event.screenPos())
    
    def _set_font_size(self, size: int):
        """Set font size from menu"""
        self._font_size = size
        self._apply_font()
        self.signals.fontSizeChanged.emit(size)
        self._sync_to_bubble()  # Sync font size change
    
    def _edit_text_dialog(self):
        """Open dialog to edit text"""
        current_text = self.toPlainText()
        new_text, ok = QInputDialog.getMultiLineText(
            None, "Edit Text", "Enter translated text:", current_text
        )
        if ok and new_text:
            self.setPlainText(new_text)
            self._sync_to_bubble()
    
    def _delete_self(self):
        """Remove this item from scene"""
        if self.scene():
            self.scene().removeItem(self)
    
    def toggle_bold(self):
        """Toggle bold on current selection"""
        if not self.textInteractionFlags() & Qt.TextInteractionFlag.TextEditorInteraction:
            return
            
        self.signals.interactionStarted.emit()
        cursor = self.textCursor()
        fmt = cursor.charFormat()
        
        # Toggle weight
        if fmt.fontWeight() == QFont.Weight.Bold:
            fmt.setFontWeight(QFont.Weight.Normal)
        else:
            fmt.setFontWeight(QFont.Weight.Bold)
            
        cursor.mergeCharFormat(fmt)
        self.setTextCursor(cursor)
        self._sync_to_bubble()

    def toggle_italic(self):
        """Toggle italic on current selection"""
        if not self.textInteractionFlags() & Qt.TextInteractionFlag.TextEditorInteraction:
            return
            
        self.signals.interactionStarted.emit()
        cursor = self.textCursor()
        fmt = cursor.charFormat()
        
        # Toggle italic
        fmt.setFontItalic(not fmt.fontItalic())
            
        cursor.mergeCharFormat(fmt)
        self.setTextCursor(cursor)
        self._sync_to_bubble()

    def get_font_size(self) -> int:
        return self._font_size
    
    def get_text(self) -> str:
        return self.toHtml()  # Return HTML to preserve formatting
    
    def _sync_to_bubble(self):
        """Sync current text and position back to TextBubble data"""
        if self.bubble_ref:
            # Update translated text (Now as HTML)
            self.bubble_ref.text_translated = self.toHtml()
            
            # Update position (store offset from bbox)
            pos = self.scenePos()
            self.bubble_ref.text_offset = (pos.x(), pos.y())
            
            # Update font settings
            self.bubble_ref.font_size = self._font_size
            self.bubble_ref.font_family = self._font_family
            
            self.signals.textChanged.emit(self.toHtml())
