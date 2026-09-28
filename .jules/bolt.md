## 2024-05-24 - API Connection Pooling
**Learning:** Instantiating new synchronous clients (like `requests.post` or `OpenAI()`) for every translation task causes significant overhead due to repeated TLS handshakes.
**Action:** Always use connection pooling (like `requests.Session()` or reusing `OpenAI` client instances) for synchronous clients to reduce network latency during batch processing.
