## 2024-05-18 - Optimized Firestore sync with batched writes
**Learning:** Performing multiple independent write operations inside a loop (like syncing multiple pages) creates an N+1 query bottleneck with Firestore, causing high latency due to individual network roundtrips for each page.
**Action:** Always use `db.batch()` for updating multiple related documents. Preserve encapsulation by passing the `batch` instance down into data access methods (`save_project`, `save_page`) rather than repeating extraction logic. Chunk writes into sizes under 500 to respect Firestore batch limits.
