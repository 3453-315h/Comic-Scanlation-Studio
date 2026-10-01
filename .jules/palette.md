## 2023-10-24 - PySide6 Hover Cursor Importance
**Learning:** Unlike web development where buttons often get a pointer cursor by default via browser stylesheets, PySide6 generic `QPushButton` instances do not inherently change the mouse cursor on hover. This can make interactive elements feel static and unresponsive.
**Action:** Always explicitly set `setCursor(Qt.CursorShape.PointingHandCursor)` on PySide6 interactive buttons to communicate clickability and improve micro-UX.
