## 2024-09-16 - Optimizing Firestore sync
**Learning:** The `sync_project` method was saving the project metadata and each page individually, causing an N+1 query bottleneck for projects with many pages.
**Action:** When updating multiple related documents in Firestore, use `db.batch()` to combine writes. Always pass the batch object to existing data access methods to preserve encapsulation, and remember to chunk operations into batches of 500 to respect Firestore limits.
