## 2024-03-24 - API Client Connection Pooling
**Learning:** The OpenAI and DeepL translation backends in `Translator` recreate their respective HTTP clients (`OpenAI()` and `requests.post()`) for every translation request. This discards the underlying connection pool and requires a new TLS handshake for each API call, which is highly inefficient for batch text block processing.
**Action:** Instantiate a single `requests.Session()` and single `OpenAI` client during initialization (or lazy-loaded and cached) and reuse them across translation calls to preserve connection pools.
