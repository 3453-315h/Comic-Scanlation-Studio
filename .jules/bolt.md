## 2024-05-18 - Batch processing performance bottleneck
**Learning:** Making external API calls in loops or batch processing (e.g., DeepL, OpenAI) without connection pooling (like `requests.Session()`) or client instance reuse causes repeated TLS handshakes, leading to significant performance bottlenecks.
**Action:** Always use connection pooling (like `requests.Session()`) or reuse client instances when making external API calls in loops or batch processing.
