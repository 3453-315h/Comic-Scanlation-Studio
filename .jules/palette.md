## 2024-06-12 - Accessibility improvement for Qt widgets

**Learning:** Qt widgets in this application require `setAccessibleName()` and `setToolTip()` instead of HTML ARIA attributes. Also, when setting `setAccessibleName()`, omit any emojis that are present in the visual button text to ensure clear auditory readouts.
**Action:** Always set accessible names without emojis and tooltips for all interactive widgets.
