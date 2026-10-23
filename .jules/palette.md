## 2024-08-17 - PySide6 Accessibility Patterns
**Learning:** PySide6 uses `setAccessibleName()` and `setToolTip()` for accessibility rather than HTML ARIA attributes. Also, `setCursor(Qt.CursorShape.PointingHandCursor)` improves micro-UX by visually indicating clickability on hover for interactive elements like buttons.
**Action:** Use these methods when adding accessibility and micro-UX polish to Qt/PySide6 widgets instead of trying to write HTML attributes.
