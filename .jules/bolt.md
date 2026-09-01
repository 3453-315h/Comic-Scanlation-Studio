## 2024-05-17 - Connection Pooling for External APIs
**Learning:** Instantiating new HTTP client sessions (`requests.post()`, `OpenAI()`) for every translation text chunk causes repeated TLS handshakes, which can be a significant bottleneck in synchronous loop processing.
**Action:** Always use connection pooling (like `requests.Session()`) or reuse synchronous client instances for external API calls, but avoid caching asyncio-dependent clients across event loops.
