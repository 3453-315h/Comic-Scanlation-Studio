## 2023-10-27 - Batch Firestore writes in sync_project

**Learning:** Syncing a large project with many pages one by one results in N+1 network calls which significantly degrades backend sync performance, making the system sluggish or causing network bottlenecks.
**Action:** When making multiple document modifications in Firestore (e.g., syncing all pages of a project), use `db.batch()` to chunk and execute operations within Firestore's 500 operation limit per batch, reducing network requests to ceil(N/400).
