## 2024-03-24 - Repeated TLS Handshakes and Client Instantiation
**Learning:** External API clients (like OpenAI or DeepL using `requests`) are being instantiated per-request in loops/batch processes, which prevents connection pooling and leads to significant TLS handshake overhead.
**Action:** Use connection pooling (e.g., `requests.Session()` or reusing `OpenAI()` client instances) across translation calls to prevent repeated TLS handshakes.
