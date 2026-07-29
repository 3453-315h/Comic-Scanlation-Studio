## 2024-05-24 - HTTP Connection Pooling in Batch Loops
**Learning:** Creating HTTP connection objects (like `requests.post`, `openai.OpenAI`, or `googletrans.Translator`) inside a translation loop for every bubble adds massive overhead (TLS handshake, TCP setup) per request.
**Action:** Always instantiate HTTP session clients/objects at the class level and reuse them across requests when batch processing API calls.
