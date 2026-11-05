## 2026-11-05 - Lazy Connection Pooling
**Learning:** In this architecture, background tasks are run in short-lived WorkerThread instances (or processes). Eagerly instantiating objects with thread locks (like `requests.Session()`) in `__init__` can cause multiprocessing pickling errors. The `OpenAI` client also handles internal pooling and shouldn't be recreated per request.
**Action:** Use lazy initialization for synchronous clients (`requests.Session`, `OpenAI`) by instantiating them on first use within the class, avoiding eager instantiation in `__init__`.
