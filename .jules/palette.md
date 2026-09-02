## 2024-09-02 - PySide6 Screen Reader Accessibility and Micro-UX
**Learning:** When using emojis in Qt buttons for visual flair, screen readers will attempt to read the emojis, causing a confusing auditory experience. Additionally, Qt buttons don't have a built-in hover cursor, making them feel less interactive.
**Action:** Always set `setAccessibleName()` without the emoji for clean auditory readouts, and apply `setCursor(Qt.CursorShape.PointingHandCursor)` to visually indicate clickability on hover.
