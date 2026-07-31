## 2024-05-24 - Synchronous File I/O in Loop Bottleneck
**Learning:** Saving the entire translation JSON cache to disk synchronously on every successful translation causes severe O(N^2) disk I/O scaling, blocking the processing pipeline, especially when processing multiple comic bubbles or pages in a batch.
**Action:** When implementing caching mechanisms that are updated frequently in a loop, always use batched writes (e.g., saving after N entries) or an asynchronous/background save strategy, and register an `atexit` hook to ensure the final cache state is flushed on shutdown.
