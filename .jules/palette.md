## 2024-05-30 - Added Accessible Names to TopBar Buttons
**Learning:** Found several buttons in `TopBar` without text but with emojis/icons (e.g. ➖ and ➕ for zoom). Screen readers will read the emoji name, but it's better to provide explicit accessible names (e.g., "Zoom Out", "Zoom In") and omit emojis from the read-out for clarity.
**Action:** Use `setAccessibleName()` on icon-only buttons to improve screen reader accessibility. Ensure no emojis are included in the accessible name.
