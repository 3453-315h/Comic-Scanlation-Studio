## 2024-05-15 - PySide6 Accessible Names
**Learning:** When setting `setAccessibleName` for Qt widgets to support screen readers, any emojis that are present in the visual button text must be omitted to ensure clear auditory readouts.
**Action:** Always strip emojis when setting accessible names for Qt widgets.
