## 2024-09-06 - Connection Pooling in Workers
**Learning:** This application uses short-lived WorkerThread instances for background tasks, creating new asyncio event loops. While asyncio-dependent clients cannot be pooled across threads safely, synchronous clients like `requests.Session` and `openai.OpenAI` can and should be pooled at the module/class instance level to avoid repeated TLS handshakes during batch operations (like translation).
**Action:** Always utilize connection pooling for synchronous external API calls, especially when they are invoked iteratively.
