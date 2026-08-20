## 2026-08-20 - Connection Pooling for API Backends
**Learning:** In batch processing architectures, repeated external API calls (e.g., DeepL, OpenAI) without connection pooling create massive overhead due to repeated TLS handshakes for each text segment.
**Action:** When implementing classes that make repeated API calls, initialize a persistent client/session (like `requests.Session()` or `OpenAI()`) instead of making one-off connections per request.
