## 2024-05-19 - TopBar Accessible Names
**Learning:** Found several icon-only buttons in `TopBar` that need explicit accessible names for screen readers, while ensuring we remove the visual emojis from the accessible name itself to prevent confusing auditory output. We should also add visual cues for interaction.
**Action:** Always strip emojis when setting `setAccessibleName` for screen readers and ensure `setCursor(Qt.CursorShape.PointingHandCursor)` is set for interactive icon buttons to improve both auditory and visual accessibility.
