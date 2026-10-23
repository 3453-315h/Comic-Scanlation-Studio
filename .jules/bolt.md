## 2024-03-24 - Network Connection Pooling for Translators
**Learning:** External API calls (like DeepL in Translator) were using `requests.post()` directly, creating a new connection for each translation request. In a pipeline processing many small text snippets, this repeated TLS handshake overhead adds up and acts as a significant bottleneck.
**Action:** When making external API calls in loops or batch processing, always use connection pooling (like `requests.Session()`) or reuse client instances to prevent repeated TLS handshakes.
