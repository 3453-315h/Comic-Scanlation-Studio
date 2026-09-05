## 2024-09-05 - Optimize Firestore Data Sync with WriteBatch
**Learning:** Firestore has a 500-operation limit per batch when making writes. N+1 queries when looping over large document collections individually slow down performance.
**Action:** When updating multiple related documents, use `db.batch()` combined with write operations like `batch.set()`, strictly chunking them into blocks of up to 500 limit max before running `batch.commit()`.
