## 2024-08-17 - Client Pooling for External APIs
**Learning:** Re-instantiating HTTP clients (like `requests.post()` or `OpenAI()`) for every individual piece of text being translated generates massive overhead due to repeated connection setups and TLS handshakes, especially when processing multiple bubbles per page.
**Action:** Always reuse synchronous client instances (`requests.Session`, `OpenAI` client) across loop iterations to maintain a connection pool, while remembering to keep them thread-local (or recreate per worker) to avoid threading issues.
