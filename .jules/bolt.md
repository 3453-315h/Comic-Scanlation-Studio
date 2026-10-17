## 2024-10-17 - Connection Pooling for API Backends
**Learning:** Making external API calls (e.g. DeepL) inside loops for batch processing without connection pooling results in a significant performance bottleneck due to repeated TLS handshakes for every request.
**Action:** Always instantiate and reuse a `requests.Session()` object across multiple requests instead of using module-level functions like `requests.post()` when interacting with external APIs in translation loops.
