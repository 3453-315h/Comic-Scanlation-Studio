## 2024-05-18 - Improved TopBar Accessibility
**Learning:** In PySide6, UI elements containing emojis (like "➕ New Project") require an explicit `setAccessibleName()` without the emoji to ensure screen readers pronounce the label correctly instead of reading out the emoji characters or ignoring them.
**Action:** Always strip emojis and provide clean text when setting `setAccessibleName` on Qt widgets for screen readers.
