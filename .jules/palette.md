## 2023-10-24 - Accessibility improvements for PySide6 application
**Learning:** PySide6 uses `setAccessibleName()` and `setToolTip()` instead of HTML ARIA attributes for screen readers. Removing tooltip can degrade accessibility. Use `setToolTip` to convey button purpose (like deleting a page) while using visual design to prevent "popup" confusion instead of completely removing the tooltip. Emoticons/Emojis should be removed from `setAccessibleName` to ensure correct audio readouts.
**Action:** Always check `setAccessibleName` and `setToolTip` on custom icon/small buttons.
