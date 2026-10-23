## 2024-05-24 - Qt Accessibility vs HTML ARIA
**Learning:** This app uses PySide6/Qt instead of HTML/React. HTML accessibility properties like `aria-label` do not apply. Instead, we must use Qt-specific methods like `setAccessibleName()` for screen readers and `setToolTip()` for visual tooltips on icon-only buttons.
**Action:** Always verify if the app is web-based or native desktop. When working in PySide6/PyQt apps, use `setAccessibleName()` and `setToolTip()` for button accessibility instead of HTML ARIA attributes.
