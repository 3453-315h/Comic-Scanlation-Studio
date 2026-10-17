## 2024-10-17 - Add PointingHandCursor and AccessibleName to TopBar buttons
**Learning:** PySide6 buttons require `setAccessibleName` instead of ARIA attributes, and should have `setCursor(Qt.CursorShape.PointingHandCursor)` to indicate clickability on hover. Emojis in visible text should be stripped from the `setAccessibleName` to prevent screen reader confusion.
**Action:** Always add `PointingHandCursor` and text-only `AccessibleName`s to icon/emoji-heavy buttons in Qt/PySide6 applications.
