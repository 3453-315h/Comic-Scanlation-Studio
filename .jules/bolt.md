## 2026-09-02 - Firestore Batching for Project Sync
**Learning:** When writing multiple documents to Firestore, using individual `set()` calls is inefficient and leads to N+1 query bottlenecks. Combining them using `db.batch()` avoids this, but we must chunk operations to respect Firestore's 500-operation limit per batch.
**Action:** Use batching and pass an optional `batch` object to existing data access methods to preserve encapsulation when performing multiple writes.
