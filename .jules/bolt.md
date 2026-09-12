## 2024-05-20 - Connection Pooling for Translation APIs
**Learning:** Making repeated synchronous HTTP requests to external translation APIs (DeepL, OpenAI) during batch processing results in severe overhead due to repeated TLS handshakes for each translation call.
**Action:** Always use connection pooling (e.g. `requests.Session()` or reuse client instances like `openai.OpenAI()`) for external API clients used in loops to prevent this latency.
