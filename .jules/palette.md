## 2025-02-23 - Interactive Buttons Pointer
**Learning:** In PySide6 desktop applications, push buttons don't always have a pointer cursor by default on hover, making it unclear which elements are interactive.
**Action:** Always verify if interactive widgets like buttons or clickable labels explicitly set `setCursor(Qt.CursorShape.PointingHandCursor)` to improve affordance and accessibility for mouse users.
