## 2024-05-18 - Improve Top Bar Accessibility and UX
**Learning:** PySide6 accessibility requires `setAccessibleName()` for buttons with emojis to ensure proper screen reader pronunciation without saying the emoji names. Also, `setCursor(Qt.CursorShape.PointingHandCursor)` is needed for better visual hover feedback on custom UI buttons.
**Action:** Always strip emojis when setting `setAccessibleName` on buttons containing them, and apply the pointing hand cursor to all interactive elements for better UX.
