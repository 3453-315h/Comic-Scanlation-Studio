## 2024-11-20 - PySide6 Explicit UX Requirements
**Learning:** In Qt/PySide6 applications, web paradigms like automatic pointer cursors on buttons or implicit ARIA from HTML semantics do not apply automatically.
**Action:** Always explicitly set `setCursor(Qt.CursorShape.PointingHandCursor)` on interactive widgets (buttons, checkboxes) and use `setAccessibleName` / `setToolTip` for accessibility, particularly on icon-only elements.
