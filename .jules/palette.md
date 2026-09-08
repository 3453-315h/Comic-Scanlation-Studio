## 2024-05-24 - PySide6 Screen Reader & Cursor Interactions
**Learning:** In PySide6, clickable widgets like `QPushButton` and `QCheckBox` need `setCursor(Qt.CursorShape.PointingHandCursor)` explicitly for clear visual affordance. Also, default text with emojis can confuse screen readers, requiring `setAccessibleName()` with pure text.
**Action:** Always strip emojis and apply explicit cursor shapes to interactive desktop elements to ensure universal visual and auditory accessibility.
