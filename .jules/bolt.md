## 2024-05-24 - Reuse API clients for translation connection pooling
**Learning:** Reusing synchronous API clients (like `requests.Session` and OpenAI) prevents repeated TLS handshakes, speeding up translations. However, asyncio-dependent clients (like `googletrans.Translator`) should not be cached across threads due to event loop thread-safety issues.
**Action:** Apply connection pooling for synchronous external API calls, but initialize asyncio-dependent clients per task.
