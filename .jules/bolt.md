## 2024-03-24 - Reuse HTTP Sessions
**Learning:** Found that `requests.post` and OpenAI client instantiation are being done per-translation in `src/modules/translator.py`.
**Action:** Use connection pooling for `requests` by creating a `requests.Session()` instance in the `Translator` class. For OpenAI, instantiate the client once in `__init__` or lazily cache the client to prevent re-initializing it for each translation.
