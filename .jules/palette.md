## 2024-05-19 - Pointer Cursor on Hover
**Learning:** PySide6/Qt standard `QPushButton` does not automatically show a pointing hand cursor on hover, unlike web buttons. This lack of visual feedback can make elements feel less interactive in a desktop app context.
**Action:** Always manually add `button.setCursor(Qt.CursorShape.PointingHandCursor)` to new interactive button elements to ensure consistent micro-UX feedback.
