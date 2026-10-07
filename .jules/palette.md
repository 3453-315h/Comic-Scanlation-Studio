## 2024-05-24 - PySide6 Accessible Names and Emojis
**Learning:** PySide6 default accessibility features include reading the full text of buttons for screen readers, which includes emojis often used for visual styling. This can create confusing auditory readouts like "Heavy plus sign New Project".
**Action:** When adding emojis to visual button text in PySide6 applications, always explicitly set `setAccessibleName()` without the emoji to ensure clear and concise screen reader behavior.
