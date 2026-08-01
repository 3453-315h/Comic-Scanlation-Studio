## 2024-06-25 - HTTP Connection Pooling for Batch Translation
**Learning:** Re-instantiating HTTP clients (like `googletrans.Translator`, `requests.Session`, or `openai.OpenAI`) per-bubble severely degrades performance due to repeated DNS resolution and TLS handshakes.
**Action:** Always use connection pooling/client reuse by initializing the client once (e.g. lazily on first use) and reusing it for all subsequent translation requests in the batch.
