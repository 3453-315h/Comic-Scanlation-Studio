## 2024-05-18 - Translator API calls connection pooling
**Learning:** The `Translator` module performs network requests using `requests.post()` directly for the DeepL backend, which creates a new HTTP connection and performs TLS handshake on every translation request. This is a common performance issue for batch operations in loops. OpenAI client also could be pooled instead of being reinstantiated on every call.
**Action:** Use a `requests.Session()` to reuse connections across requests, reducing overhead per API call. For OpenAI, instantiate the client once and reuse it (the SDK uses `httpx` internally which pools connections). Keep event loop safety in mind and initialize them lazily in `__init__` if thread locks are involved (e.g. `requests.Session`).

## 2024-05-18 - Translator API calls connection pooling (update)
**Action:** Implemented connection pooling using `requests.Session()` for DeepL API requests and instantiated a single `openai.OpenAI()` client instance to be reused across requests in the `Translator` module.
