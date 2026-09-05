## 2026-09-05 - PySide6 Emoji Accessibility
**Learning:** PySide6 screen readers will read emoji names aloud if they are part of the visible text in buttons. To prevent a noisy auditory experience, buttons with emojis require explicitly setting an emoji-free `setAccessibleName()`.
**Action:** Always provide an explicit, emoji-free accessible name for Qt widgets that use emojis in their visible text.
