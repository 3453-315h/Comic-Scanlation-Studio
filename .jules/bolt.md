## 2024-10-03 - Reuse connection pooling for external APIs
**Learning:** Creating a new `requests` session or a new `OpenAI` client per translation bubble initiates a new connection pool and a new TLS handshake every time, which introduces significant latency in batch processing. Synchronous clients should be pooled across short-lived thread instances.
**Action:** Instantiate synchronous clients (like `requests.Session()` or `OpenAI()`) once as class or instance members and reuse them for all API requests to prevent repeated TLS overhead.
