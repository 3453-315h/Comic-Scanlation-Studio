## 2024-11-02 - Reuse OpenAI client in Translator
**Learning:** Instantiating the OpenAI client `OpenAI(api_key=self.api_key)` inside the `_openai_translate` method causes it to reconstruct the connection pool and make a new TLS handshake for every translation call, significantly slowing down batch processing.
**Action:** When integrating OpenAI in classes that process batches or sequences of requests, initialize the client once in `__init__` (or lazily as an instance attribute) and reuse it across requests.
