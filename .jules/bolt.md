## 2024-05-23 - Pool synchronous API clients but beware of asyncio

**Learning:** When making external API calls in background tasks, pooling synchronous clients (like `requests.Session()` or the `OpenAI` client) prevents repeated TLS handshakes, noticeably speeding up tasks like batch translation. However, asyncio-dependent clients (like `googletrans.Translator`) should not be pooled across threads because each background task runs in a new asyncio event loop, leading to thread-safety and attached-loop issues.

**Action:** Always use connection pooling for synchronous external APIs (like DeepL and OpenAI) to improve performance, but carefully avoid caching asyncio-dependent clients across short-lived thread boundaries.
