## 2024-09-14 - Use connection pooling for external translation APIs
**Learning:** Making repeated external API calls (e.g., to DeepL or OpenAI) inside batch processing without connection pooling leads to severe performance degradation due to redundant TCP connections and TLS handshakes for each small text chunk.
**Action:** Re-use `requests.Session()` and `OpenAI()` client instances across translation calls. While async event loops shouldn't be shared across thread workers in this app, synchronous HTTP connection pooling is perfectly safe and highly effective.
