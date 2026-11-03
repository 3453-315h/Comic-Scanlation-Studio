## 2023-11-03 - Added Hand Cursors to Buttons
**Learning:** The default QPushButton in PySide6 does not change the mouse cursor to a hand on hover, which can lead to reduced discoverability for interactive elements like top bar navigation buttons or main primary action buttons.
**Action:** Explicitly use `setCursor(Qt.CursorShape.PointingHandCursor)` on interactive PySide6 UI elements like buttons to provide users with a clear visual cue of clickability on hover.
