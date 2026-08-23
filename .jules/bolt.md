## 2026-08-23 - Connection Pooling for API Clients
**Learning:** Recreating synchronous clients (like requests or OpenAI) in loops during page processing forces repeated TLS handshakes, adding hundreds of milliseconds of latency per bubble.
**Action:** Always use connection pooling (e.g. `requests.Session()`) or reuse client instances for synchronous APIs called in loops to significantly reduce latency.
