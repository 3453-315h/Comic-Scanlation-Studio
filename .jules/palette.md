## 2024-09-12 - Accessibility improvement for Qt Buttons with Emojis
**Learning:** In PySide6 applications, screen readers announce the exact text of a button, including emojis, which can be verbose (e.g., "Magnifying glass Detect Speech Bubbles").
**Action:** Explicitly set `setAccessibleName()` without the emoji for interactive elements to ensure clear auditory readouts while preserving visual micro-UX.
