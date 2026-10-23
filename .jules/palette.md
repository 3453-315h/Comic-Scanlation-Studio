## 2026-07-25 - Accessible Names for PySide6 Controls
**Learning:** PySide6 UI components like `QPushButton` with single characters (e.g. "B" or "I") or custom controls lacking text labels require explicit `setAccessibleName()` and `setToolTip()` for proper accessibility support for screen readers.
**Action:** When creating icon-only or single-letter UI controls in PySide6, always ensure they are paired with `setAccessibleName()` and `setToolTip()` so users relying on screen readers can navigate and understand their purpose.
