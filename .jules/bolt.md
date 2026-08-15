## 2024-05-24 - Connection Pooling for External APIs

**Learning:** This codebase's architecture often runs translation tasks in loops across many speech bubbles, making synchronous API clients like `requests` and `OpenAI` vulnerable to repeated TLS handshakes and connection overhead.

**Action:** Always utilize connection pooling (e.g. `requests.Session()` or by caching instantiated clients) when making external API calls in loops or worker threads. Avoid caching asyncio-dependent clients across threads to prevent event loop thread-safety issues, but synchronous clients should be pooled.