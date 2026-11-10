## 2024-05-18 - Tooltip Accessibility
**Learning:** Tooltips should provide additional context, and setting the accessible name on buttons is necessary when the visible button content contains only a character or emoji without providing enough context for screen readers. Emojis should be omitted from the accessible name.
**Action:** Use setAccessibleName to provide a clean, descriptive name for screen readers. Add tooltips for visual context where missing. Set cursor for hover states.
