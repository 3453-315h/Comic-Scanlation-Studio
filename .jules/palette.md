## 2024-03-XX - [Init Journal]
**Learning:** Initializing palette journal
**Action:** Ready to log critical UX/a11y insights

## 2024-03-XX - [Hidden Tooltips Break Accessibility]
**Learning:** Developers often remove visual tooltips (e.g., `# self.remove_btn.setToolTip("Delete Page") # Remove tooltip to avoid "popup" confusion`) to reduce visual clutter, inadvertently breaking screen reader accessibility for icon-only buttons.
**Action:** When a visual tooltip is undesirable, always ensure `setAccessibleName` is explicitly set to provide an invisible label for screen readers.
