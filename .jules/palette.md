## 2024-10-21 - Pointer Cursors and Clean Accessible Names
**Learning:** Interactive elements in this PySide6 app require manual `setCursor(Qt.CursorShape.PointingHandCursor)` to visually indicate clickability, and `setAccessibleName` should omit visual emojis for cleaner screen reader readouts.
**Action:** Apply `setCursor` to all interactive buttons and set `AccessibleName` explicitly without emojis.
