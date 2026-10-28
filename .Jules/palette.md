## 2024-05-24 - Interactive Cursors for PySide6 Buttons
**Learning:** PySide6 UI elements like `QPushButton` don't automatically show a pointing hand cursor on hover. This leads to a suboptimal user experience as users aren't visually prompted that elements are interactive.
**Action:** Always add `setCursor(Qt.CursorShape.PointingHandCursor)` to clickable components such as buttons and interactive labels in the UI.
