## 2024-10-24 - Connection Pooling for API Backends

**Learning:** When integrating remote HTTP APIs (e.g., DeepL, OpenAI) where each discrete text processing task (like a comic bubble) triggers a network call, creating a new client/session per text block adds significant connection setup overhead (DNS, TCP, TLS handshake) to every call.
**Action:** Always utilize connection pooling for consecutive network requests (e.g., via `requests.Session()` or persistent instantiated clients like `OpenAI()`) across batches instead of doing sequential ephemeral HTTP connections.
