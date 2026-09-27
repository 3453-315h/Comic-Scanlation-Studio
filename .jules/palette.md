## 2024-09-27 - Setting Accessible Names in PySide6
**Learning:** PySide6 visual components like `QPushButton` with text containing emojis can result in suboptimal screen reader readouts. Screen readers may read the literal unicode emoji names.
**Action:** When creating widgets containing visual emojis, always add a `setAccessibleName` specifically without the emoji content so screen readers provide a clear auditory readout. Additionally, adding `setCursor(Qt.CursorShape.PointingHandCursor)` on all interactive button components enhances visual feedback micro-UX.
