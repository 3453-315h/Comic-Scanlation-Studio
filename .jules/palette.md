## 2024-03-24 - Accessibility improvements for icon-only buttons
**Learning:** Found several top bar buttons (zoom in/out, settings) that are icon-only but missing tooltips and accessible names.
**Action:** Adding setToolTip and setAccessibleName for better screen reader and general user accessibility.
## 2024-03-24 - Editor panel icon-only buttons
**Learning:** Found that the font style buttons (bold/italic) in the editor panel are missing tooltips and accessible names.
**Action:** Adding setToolTip and setAccessibleName for better screen reader accessibility and general UX for the font style toggles.
## 2024-03-24 - Accessibility improvements for cursor
**Learning:** Found interactive elements (like the zoom/settings buttons in top_bar) that don't have pointing hand cursors like other buttons. Adding this provides users with a clearer visual cue of clickability.
**Action:** Always explicitly set setCursor(Qt.CursorShape.PointingHandCursor) on interactive buttons (especially icon-only ones) for better visual feedback.
