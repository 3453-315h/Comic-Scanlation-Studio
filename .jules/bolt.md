## 2024-05-24 - Batch Firestore writes for project sync
**Learning:** When interacting with Firestore to update multiple related documents (like project pages), iteratively saving each document results in an N+1 query bottleneck.
**Action:** Use `db.batch()` to combine writes and always chunk operations to respect Firestore's 500-operation limit per batch.