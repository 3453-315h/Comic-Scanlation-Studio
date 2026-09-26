## 2024-09-26 - Connection Pooling for Translators
**Learning:** Re-establishing TLS connections for every translated text bubble (DeepL/OpenAI) adds significant overhead per page in batch processing. However, we cannot pool async clients (like googletrans) across the worker threads due to async event loop issues.
**Action:** Always reuse synchronous clients (`requests.Session` and `openai.OpenAI`) across tasks/loops, while keeping async clients scoped or handling thread-safety carefully.
