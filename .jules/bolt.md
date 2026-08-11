## 2024-05-18 - Avoid repeated TLS handshakes for translation APIs
**Learning:** During batch translation tasks, making external API calls (e.g., DeepL, OpenAI) repeatedly creates significant overhead due to TLS handshakes for each request.
**Action:** Always use connection pooling (like `requests.Session()`) or reuse client instances for API calls to prevent repeated TLS handshakes.
