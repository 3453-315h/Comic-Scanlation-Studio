## 2023-11-11 - Firestore N+1 writes optimization
**Learning:** Found N+1 queries in the Firestore `sync_project` method, updated to use batched writes which is up to 500x faster.
**Action:** Use Firestore batched writes when creating/updating multiple documents simultaneously in a loop.
