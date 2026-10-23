## 2024-05-14 - PySide6 Widget Accessibility with Emojis
**Learning:** When building cross-platform Python desktop apps with Qt/PySide6, embedding emojis in QPushButton text visually breaks screen reader auditory readouts. The native accessibility layer treats the raw emoji characters inconsistently or poorly.
**Action:** Always set an explicit `setAccessibleName()` on Qt widgets to omit the emojis for screen reader clarity, while still providing `setCursor(Qt.CursorShape.PointingHandCursor)` to visually indicate the button's interactivity on hover.
