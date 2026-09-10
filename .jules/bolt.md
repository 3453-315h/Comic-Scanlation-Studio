## 2025-03-05 - Connection pooling for Translation APIs
**Learning:** When making external API calls in loops or batch processing (like translating multiple text bubbles), failing to use connection pooling results in repeated TLS handshakes which can significantly slow down the overall process.
**Action:** Always reuse client instances (e.g., `requests.Session()`, `OpenAI` client) to prevent repeated TLS handshakes when performing repeated API calls in the same thread.
