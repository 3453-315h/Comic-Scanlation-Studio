## 2024-09-17 - PySide6 Screen Reader & Hover Feedback Insights

**Learning:** When evaluating the TopBar for accessibility and interaction, I found two crucial elements missing for a modern desktop UX:
1. PySide6 buttons with text that includes emojis (e.g., "➕ New Project" or "⚙️") aren't natively read clearly by screen readers. The emoji creates audio clutter.
2. Unlike modern web frameworks, Qt interactive elements (like `QPushButton` and `QCheckBox`) do not show a pointing hand cursor on hover by default, which removes an important visual cue for clickability.

**Action:**
- For screen readers, always explicitly call `setAccessibleName("Plain Text")` on buttons containing emojis to ensure clean auditory readouts.
- For interaction design, manually call `setCursor(Qt.CursorShape.PointingHandCursor)` on all primary buttons, settings toggles, and icon-only interactive elements to provide instant visual feedback that they are clickable.
