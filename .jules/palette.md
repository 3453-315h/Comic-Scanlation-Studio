## 2024-05-24 - Accessibility and micro-UX in PySide6
**Learning:** PySide6 accessibility requires `setAccessibleName()` for icon-only buttons as they lack readable text, and explicit `setCursor(Qt.CursorShape.PointingHandCursor)` is necessary to provide basic visual clickability cues for interactive elements, which is a key micro-UX requirement for this app.
**Action:** When adding or updating interactive elements (especially icon-only ones) in PySide6 applications, always explicitly set `setAccessibleName()` and cursor shapes.
