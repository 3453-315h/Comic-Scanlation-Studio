## 2024-10-24 - Interactive Cursors and Accessible Names in Qt Widgets
**Learning:** PySide6 UI components don't inherently receive hover cursors or accessible names when initialized with emojis, creating poor mouse feedback and screen reader experiences.
**Action:** When working on PySide6 components, always add `setCursor(Qt.CursorShape.PointingHandCursor)` to actionable elements (buttons, checkboxes) and set `setAccessibleName()` without emojis.
