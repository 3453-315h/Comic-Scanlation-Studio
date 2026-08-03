## 2024-08-03 - API Connection Pooling in Batch Processing
**Learning:** During batch processing of comic bubbles, making external API calls (like to DeepL or OpenAI) without connection pooling results in a massive performance bottleneck because every single call triggers a new TLS handshake. In our case, a page with 30 bubbles would result in 30 separate TLS handshakes.
**Action:** Always use connection pooling (`requests.Session()` or reusing the initialized API client like `OpenAI()`) for operations performed iteratively in loops to preserve HTTP keep-alive.
