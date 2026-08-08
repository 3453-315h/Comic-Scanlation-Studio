## 2024-05-24 - API Client Reuse for Translation
**Learning:** Making external API calls (like DeepL or OpenAI) in a loop for each text bubble without reusing the client/connection pool causes repeated TLS handshakes, which can severely slow down processing of comics with many text bubbles.
**Action:** Always instantiate `requests.Session()` or external API clients (like `OpenAI`) once per class instance or thread and reuse them for subsequent requests to utilize connection pooling.
