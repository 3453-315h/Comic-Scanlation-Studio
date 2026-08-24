## 2024-05-24 - Qt Accessibility vs HTML ARIA
**Learning:** PySide6 uses `setAccessibleName()` and `setToolTip()` instead of HTML `aria-label` attributes. It also uses `setCursor(Qt.CursorShape.PointingHandCursor)` instead of CSS hover classes to indicate interactivity.
**Action:** When adding micro-UX to a PySide6 app, always use native Qt methods instead of web standards.
