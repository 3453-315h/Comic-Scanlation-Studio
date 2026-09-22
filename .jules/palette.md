## 2024-05-18 - PySide6 Accessibility and Hover States
**Learning:** When developing PySide6 applications, interactive elements require `setAccessibleName` (omitting any emojis) and `setCursor(Qt.CursorShape.PointingHandCursor)` to improve both screen reader support and micro-UX clickability indicators.
**Action:** Always add explicit accessible names without emojis to UI components and apply pointing hand cursors to buttons and interactive widgets.
