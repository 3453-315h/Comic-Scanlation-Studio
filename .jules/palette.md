## 2024-05-15 - Missing Hover Cursors on PySide6 Widgets
**Learning:** In PySide6 applications, interactive elements like buttons and checkboxes don't default to a pointing hand cursor, making them feel less clickable and violating standard web/desktop micro-UX expectations.
**Action:** Always explicitly set `setCursor(Qt.CursorShape.PointingHandCursor)` on all interactive buttons, checkboxes, and clickable labels to ensure clear affordance.
