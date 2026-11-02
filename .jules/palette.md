## 2024-03-24 - Accessibility improvements for icon-only buttons
**Learning:** Icon-only buttons without explicit labels (e.g., text, tooltips, accessible names) are inaccessible to screen readers. Emojis in visual button text can lead to poor screen reader experiences.
**Action:** Always provide `setToolTip` or `setAccessibleName` for icon-only buttons, avoiding emojis in the accessible names. Add `setCursor(Qt.CursorShape.PointingHandCursor)` to improve visual clickability.
