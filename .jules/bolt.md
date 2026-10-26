## 2023-10-26 - Connection Pooling in Translators
**Learning:** Making repeated API calls (DeepL, OpenAI) for individual text bubbles without connection pooling forces repeated TLS handshakes, severely bottlenecking batch translation performance.
**Action:** Instantiate a single `requests.Session` and `openai.OpenAI` client inside the `Translator` initialization, reusing them for all translations within the worker thread.
