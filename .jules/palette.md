## 2024-03-24 - Accessibility improvements for icon-only buttons
**Learning:** Icon-only buttons without ARIA labels or tooltips are inaccessible to screen readers and confusing for users. Setting tooltips and accessible names improves the experience for all users.
**Action:** Always provide `setToolTip` and `setAccessibleName` for icon-only `QPushButton` elements. Remove emojis from the accessible name to avoid screen reader clutter. Use `setCursor(Qt.CursorShape.PointingHandCursor)` to indicate clickability.
