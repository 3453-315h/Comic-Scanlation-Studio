## 2023-10-29 - Clear Accessibility Names for Emoji Buttons
**Learning:** Adding accessible names (`setAccessibleName`) to buttons containing emojis without including the emoji in the accessible name ensures a cleaner, clearer experience for screen reader users. Screen readers often read emojis redundantly or with long, awkward descriptions if left in the text or name.
**Action:** Always omit emojis from the `setAccessibleName` attribute on buttons to provide clear auditory readouts, focusing purely on the functional text.
