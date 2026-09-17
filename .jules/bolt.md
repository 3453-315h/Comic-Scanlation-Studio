## 2024-05-18 - Connection Pooling for Translators
**Learning:** External API calls (DeepL, OpenAI) inside loops or batch processing trigger repeated TLS handshakes if clients are recreated each time. However, asyncio-dependent clients (like googletrans) cannot be cached across short-lived WorkerThreads due to event loop thread-safety issues.
**Action:** Use connection pooling (like `requests.Session()` or caching the synchronous `OpenAI` client instance on the `Translator` object) for synchronous backends, while avoiding caching for asyncio-based backends.
