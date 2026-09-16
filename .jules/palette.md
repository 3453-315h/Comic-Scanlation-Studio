## 2024-05-20 - Adding Accessibility Names & Cursors

**Learning:** Qt UI components like toolbars often use emoji for visual flair, which can result in poor screen reader readouts (e.g. "Plus New Project", "Settings Gear"). Setting accessible names that omit the emojis is essential. Additionally, PySide6 interactive elements benefit from setting `Qt.CursorShape.PointingHandCursor` to visually indicate clickability.
**Action:** When working on top bars and editor panels, add clear text-only `setAccessibleName()` attributes and hand cursors for interactive items to improve the UX in desktop apps.
