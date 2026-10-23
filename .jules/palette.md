## 2024-05-24 - Screen Reader Labels for PySide6 Icon Buttons
**Learning:** In PySide6 desktop applications, icon-only `QPushButton`s lack an implicit accessible name. While `setToolTip` provides visual hints on hover, it does not reliably populate the accessibility tree for screen readers. Using `setAccessibleName()` is required to function as the equivalent of web ARIA labels for icon-only Qt buttons.
**Action:** When creating or modifying icon-only widgets in Qt/PySide6, always ensure `setAccessibleName()` is explicitly set alongside `setToolTip()`.
