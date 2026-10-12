## $(date +%Y-%m-%d) - Accessible Names in PySide6
**Learning:** PySide6 screen readers read out visual emojis in button text. To fix this, always use setAccessibleName to provide a clean string without emojis.
**Action:** Set setAccessibleName() explicitly on widgets containing emojis in their text.
