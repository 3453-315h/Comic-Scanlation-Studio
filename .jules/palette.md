## 2024-09-09 - [PySide6 Button Accessibility & Hover Feedback]
**Learning:** Screen readers reading out emojis on UI buttons can degrade the user experience in PySide6. Also, buttons lack a pointer cursor out-of-the-box, providing poor visual feedback to users.
**Action:** Explicitly set `setAccessibleName()` on buttons with text containing emojis, and add `setCursor(Qt.CursorShape.PointingHandCursor)` on interactive elements to improve both accessibility and visual UX.
