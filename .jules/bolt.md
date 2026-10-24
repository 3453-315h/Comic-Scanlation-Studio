## 2023-10-24 - Initial Journal
**Learning:** Initializing journal.
**Action:** Always measure impact.

## 2023-10-24 - Network Requests Optimization
**Learning:** `Translator._deepl_translate` and `Translator._openai_translate` are currently creating new connection sessions/clients for every translation request. `requests.post()` and `OpenAI()` instantiation per call do not utilize connection pooling, leading to overhead during TLS handshakes.
**Action:** Use a single, reusable `requests.Session` instance for DeepL and a single `OpenAI` client instance per `Translator` to optimize network calls via connection pooling.
