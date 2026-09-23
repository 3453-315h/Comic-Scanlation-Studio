## 2024-07-25 - API Connection Pooling
**Learning:** In batch processing or loops (like translation pipelines), recreating synchronous HTTP clients (like `requests.post` or `OpenAI()` clients) for every call creates massive overhead due to repeated TLS handshakes and connection setup.
**Action:** Always reuse client instances (like `requests.Session()` or a single `OpenAI` client instance) for external API calls, but remember not to cache asyncio-dependent clients across worker threads to avoid event loop thread-safety issues.
