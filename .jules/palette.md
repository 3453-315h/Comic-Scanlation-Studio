## 2024-05-24 - PySide6 Accessible Names should exclude Emojis
**Learning:** When using screen readers with Qt/PySide6, visual emojis within text buttons (e.g., '➕ New Project') can be read out confusingly by the screen reader.
**Action:** Use `setAccessibleName()` on Qt widgets with a clean, emoji-free string to explicitly provide a better auditory readout while keeping the visual flair.
