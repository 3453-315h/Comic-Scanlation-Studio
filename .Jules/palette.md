## 2024-03-24 - Accessibility improvements for Qt widgets
**Learning:** PySide6/Qt visual elements that contain emojis (like '➕ New Project' or '⚙️') are poorly interpreted by screen readers. Furthermore, interactive but non-standard UI elements (like top bar icon buttons) do not always have an intuitive hover state by default.
**Action:** When working on PySide6 UIs, always explicitly set `setAccessibleName` (stripping emojis for clean auditory readout) and use `setCursor(Qt.CursorShape.PointingHandCursor)` on interactive elements to provide clear visual clickability cues.
