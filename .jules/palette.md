## 2024-05-24 - Qt Accessibility & Micro-UX
**Learning:** Standard Qt widget accessibility names often inherit problematic characters (like emojis) from their text labels, necessitating explicit `setAccessibleName` calls, and pointing hand cursors must be explicitly added to Qt widgets to provide expected web-like micro-UX.
**Action:** Always use `setAccessibleName` without emojis for Qt buttons that have emojis in their labels, and apply `setCursor(Qt.CursorShape.PointingHandCursor)` to all interactive buttons for better hover feedback.
