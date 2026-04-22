
from PySide6.QtWidgets import QGraphicsRectItem, QGraphicsSceneHoverEvent, QGraphicsSceneMouseEvent
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPen, QBrush, QColor, QCursor

class ResizableRectItem(QGraphicsRectItem):
    """
    A GraphicsRectItem with resize handles.
    """
    handle_size = 8.0
    handle_space = -4.0
    
    handle_cursors = {
        0: Qt.SizeFDiagCursor,  # Top-Left
        1: Qt.SizeVerCursor,    # Top
        2: Qt.SizeBDiagCursor,  # Top-Right
        3: Qt.SizeHorCursor,    # Left
        4: Qt.SizeHorCursor,    # Right
        5: Qt.SizeBDiagCursor,  # Bottom-Left
        6: Qt.SizeVerCursor,    # Bottom
        7: Qt.SizeFDiagCursor,  # Bottom-Right
    }

    def __init__(self, rect, bubble_ref=None):
        super().__init__(rect)
        self.bubble_ref = bubble_ref  # Reference to the data object
        self.setFlags(
            QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsRectItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self.handles = {}
        self.current_handle = None
        self.mouse_press_pos = None
        self.mouse_press_rect = None

    def hoverMoveEvent(self, event: QGraphicsSceneHoverEvent):
        """Change cursor when hovering over handles"""
        try:
            if self.isSelected():
                handle, cursor = self.get_handle_at(event.pos())
                if handle is not None:
                    self.setCursor(QCursor(cursor))
                    return
            self.setCursor(QCursor(Qt.ArrowCursor))
            super().hoverMoveEvent(event)
        except Exception as e:
            # Prevent crash on hover
            print(f"Hover error: {e}")

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent):
        """Handle mouse press for resizing"""
        if self.isSelected():
            handle, _ = self.get_handle_at(event.pos())
            if handle is not None:
                self.current_handle = handle
                self.mouse_press_pos = event.pos()
                self.mouse_press_rect = self.rect()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent):
        """Handle resizing logic"""
        if self.current_handle is not None:
            self.interactive_resize(event.pos())
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent):
        """Finish resizing"""
        self.current_handle = None
        self.mouse_press_pos = None
        self.mouse_press_rect = None
        self.update_bubble_ref()
        super().mouseReleaseEvent(event)
        
    def itemChange(self, change, value):
        """Sync movement with data object"""
        if change == QGraphicsRectItem.GraphicsItemChange.ItemPositionChange and self.scene():
            # We delay update to mouse release for perf, but could do here
            pass
        return super().itemChange(change, value)

    def update_bubble_ref(self):
        """Update the underlying TextBubble data"""
        if self.bubble_ref:
            # Get scene coordinates
            # Bbox is [x1, y1, x2, y2]
            r = self.mapRectToScene(self.rect())
            x1, y1, w, h = r.x(), r.y(), r.width(), r.height()
            self.bubble_ref.bbox = [int(x1), int(y1), int(x1+w), int(y1+h)]



    def paint(self, painter, option, widget=None):
        """Draw the rect and handles if selected"""
        super().paint(painter, option, widget)
        
        if self.isSelected():
            painter.setPen(QPen(QColor(0, 0, 0), 1, Qt.SolidLine))
            painter.setBrush(QBrush(QColor(255, 255, 255)))
            
            handles = self.get_handle_rects()
            for handle_rect, _ in handles:
                # Draw handle relative to the item's local coordinate system
                # The rects from get_handle_rects are already in local coords (based on self.rect())
                painter.drawRect(handle_rect)

    def get_handle_rects(self):
        """Get list of (rect, cursor_id) for all handles"""
        r = self.rect()
        x, y, w, h = r.x(), r.y(), r.width(), r.height()
        hs = self.handle_size
        
        # Define handle rects (Top-Left, Top, Top-Right, Left, Right, Bottom-Left, Bottom, Bottom-Right)
        return [
            (QRectF(x, y, hs, hs), 0),      # TL
            (QRectF(x+w/2-hs/2, y, hs, hs), 1), # T
            (QRectF(x+w-hs, y, hs, hs), 2), # TR
            (QRectF(x, y+h/2-hs/2, hs, hs), 3), # L
            (QRectF(x+w-hs, y+h/2-hs/2, hs, hs), 4), # R
            (QRectF(x, y+h-hs, hs, hs), 5), # BL
            (QRectF(x+w/2-hs/2, y+h-hs, hs, hs), 6), # B
            (QRectF(x+w-hs, y+h-hs, hs, hs), 7), # BR
        ]

    def get_handle_at(self, pos: QPointF):
        """Check if position is over a resize handle"""
        handles = self.get_handle_rects()
        
        for rect, idx in handles:
            if rect.contains(pos):
                return idx, self.handle_cursors[idx]
        return None, None

    def interactive_resize(self, mouse_pos):
        """Resize rect based on handle drag"""
        r = self.mouse_press_rect
        # Convert mouse pos to delta from press pos
        diff = mouse_pos - self.mouse_press_pos
        dx, dy = diff.x(), diff.y()
        
        new_rect = QRectF(r)
        
        # 0:TL, 1:T, 2:TR, 3:L, 4:R, 5:BL, 6:B, 7:BR
        
        # X-axis sizing
        if self.current_handle in [0, 3, 5]: # Left
            new_rect.setLeft(min(r.right() - 10, r.left() + dx))
        elif self.current_handle in [2, 4, 7]: # Right
            new_rect.setRight(max(r.left() + 10, r.right() + dx))
            
        # Y-axis sizing
        if self.current_handle in [0, 1, 2]: # Top
            new_rect.setTop(min(r.bottom() - 10, r.top() + dy))
        elif self.current_handle in [5, 6, 7]: # Bottom
            new_rect.setBottom(max(r.top() + 10, r.bottom() + dy))
            
        self.setRect(new_rect)

