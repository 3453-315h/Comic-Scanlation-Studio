## 2024-05-18 - Avoid repeated TLS Handshakes on External API calls

**Learning:** Making repeated API calls within a process without pooling causes repeated TLS handshakes, slowing down network operations, especially for batch operations on deepL or OpenAI APIs. Repeated `requests.post()` calls create a new connection each time.

**Action:** When making external API calls in loops or batch processing (e.g., DeepL, OpenAI), always use connection pooling (like `requests.Session()`) or reuse client instances to prevent repeated TLS handshakes.
