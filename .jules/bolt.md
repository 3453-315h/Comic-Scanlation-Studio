## 2024-05-24 - API Client Connection Pooling in Translators
**Learning:** In a batch-processing application (like comic translation), reinstantiating HTTP clients (like `requests` for DeepL or `OpenAI` client) for every individual request causes repeated TLS handshakes, introducing significant overhead.
**Action:** Always maintain a single connection pool or cached client instance (e.g., `requests.Session()` or `OpenAI()`) for external API calls inside loop-based or batch-processing workers to minimize overhead.
