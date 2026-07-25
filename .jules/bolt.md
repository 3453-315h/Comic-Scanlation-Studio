## 2025-01-31 - Batch I/O Reduction in Translation Loop
**Learning:** The application was serializing and writing the entire translation cache JSON file to disk after every single successful text bubble translation. During a page processing step, this resulted in O(N) redundant disk writes per page (where N is the number of text bubbles).
**Action:** Always batch or debounce I/O operations (like cache saving) when performing operations in a loop. Added a `save_cache` boolean flag to the translate function to defer saving until the end of the batch.
