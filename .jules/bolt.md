## 2024-05-18 - Firestore Sync Batching
**Learning:** Firestore operations in loops (like saving multiple pages for a project) can cause N+1 query bottlenecks. Firestore `WriteBatch` resolves this, but batches are strictly limited to 500 operations.
**Action:** When implementing bulk Firestore writes, always use `db.batch()` and explicitly chunk operations in sizes of 500 to respect the limit and maximize throughput.
