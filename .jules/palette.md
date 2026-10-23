## 2024-05-18 - PySide6 Accessibility
**Learning:** PySide6 widgets require `setAccessibleName()` and `setToolTip()` instead of HTML ARIA attributes. Interactive elements should use `setCursor(Qt.CursorShape.PointingHandCursor)` to visually indicate clickability on hover.
**Action:** When adding UX enhancements to buttons, apply these PySide6-specific methods.
