## 2024-11-04 - Translator HTTP Connection Pooling
**Learning:** The DeepL translation backend creates a new `requests.post()` call for every translation request. Creating a new HTTP connection for each API call to the same domain (e.g., api-free.deepl.com) can be a significant bottleneck due to TCP handshake and TLS negotiation overhead, especially during batch processing of multiple text bubbles.
**Action:** Use a `requests.Session()` object, initialized safely to avoid multiprocessing pickling issues, to pool HTTP connections for DeepL translations.
