## 2024-06-25 - API Connection Pooling in Batch Processing
**Learning:** The pipeline processes text bubbles in batches per page (e.g., `for bubble in bubbles: ...`). When using external APIs like DeepL or OpenAI without a connection pool or reused client, the application performs a full TLS handshake for *every single text bubble*.
**Action:** Always instantiate synchronous HTTP clients (like `requests.Session` or `openai.OpenAI`) once per instance and reuse them across calls, especially when they are called inside loops, to significantly reduce network overhead.
