## 2024-05-24 - Accessible Names for Emoji Buttons
**Learning:** In PySide6 applications, screen readers read out visual emojis by default, which can be verbose or confusing. Emojis should be removed from auditory readouts while preserved visually for sighted users.
**Action:** Use `setAccessibleName()` on interactive elements to provide a clean, text-only auditory label stripped of visual emojis.
