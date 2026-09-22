## 2024-05-15 - Connection pooling for synchronous external APIs
**Learning:** Repeated TLS handshakes on every translation request using `requests.post()` or re-instantiating `OpenAI()` in `Translator` cause significant latency in processing comics, where many small text pieces need translation.
**Action:** Lazily initialize and reuse `requests.Session()` and `OpenAI` client in `Translator` to leverage connection pooling.
