## 2024-06-03 - Use Connection Pooling for External APIs
**Learning:** Synchronous clients (like `requests.Session` and `OpenAI`) should be pooled across calls to prevent repeated TLS handshakes, which is safe in this architecture despite short-lived worker threads.
**Action:** Always reuse connection clients for `requests` and `OpenAI` in modules handling batch processing or repeated API calls.
