## 2024-05-19 - Connection Pooling for DeepL Translation
**Learning:** The translator module creates a new HTTP connection for every translation request in `_deepl_translate`. Since translations are likely done in a loop (e.g., iterating through multiple speech bubbles), establishing a new TLS handshake for each short snippet creates a significant bottleneck.
**Action:** Use a `requests.Session` instance for external API calls, especially in methods like `_deepl_translate` that are called repeatedly during batch processing, to reuse connections and reduce latency.
