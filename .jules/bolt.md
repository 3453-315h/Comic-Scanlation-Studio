## 2024-09-24 - Reuse API Clients
**Learning:** Instantiating new HTTP/API clients (like `requests.post` or `openai.OpenAI()`) for every translation call creates massive overhead due to repeated TCP/TLS handshakes, especially during batch processing.
**Action:** Always use connection pooling (e.g., `requests.Session()` or keeping a single `openai.OpenAI()` instance) for synchronous external API calls to avoid repeated handshake overhead.
