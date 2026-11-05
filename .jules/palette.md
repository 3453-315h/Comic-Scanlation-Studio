## 2024-05-24 - Accessibility improvements for icon-only buttons
**Learning:** Icon-only buttons without explicit labels (ARIA or otherwise) are invisible to screen readers, which is a major accessibility issue.
**Action:** Add tooltips or explicit accessible names to all icon-only buttons in PySide6 to ensure screen readers can announce their purpose clearly, and optionally omit emojis in accessible names.
