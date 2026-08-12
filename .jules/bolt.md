## 2024-08-12 - Reusing external API clients to avoid TLS overhead
**Learning:** Recreating `requests.Session()` or external clients like `OpenAI()` inside a loop (like iterating through detected text bubbles) results in substantial performance penalties due to repeated TCP connections and TLS handshakes. Connection pooling must be leveraged.
**Action:** Always declare an instance variable (e.g. `self._requests_session` or `self._openai_client`) in the class constructor and reuse it lazily in the method that calls the API.
