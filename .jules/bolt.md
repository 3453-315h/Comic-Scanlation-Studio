## 2024-10-21 - Use connection pooling in translator API calls
**Learning:** `translator.py`'s `_deepl_translate` and `_openai_translate` perform API calls in loops (e.g., when a page has many bubbles). They were creating a new HTTP connection or client per call, which triggers a TLS handshake each time, severely impacting translation speed.
**Action:** Use `requests.Session()` for the DeepL backend and initialize the OpenAI client once during the `__init__` method (or inside the method, caching it on `self`) to reuse the connection pool and make batched API calls significantly faster.
