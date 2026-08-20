## 2025-02-28 - Performance optimization via connection pooling in Translator
 **Learning:** Instantiating new HTTP connection objects like `requests.post` or OpenAI clients for every synchronous API call results in severe latency bottlenecks due to repeated TCP and TLS handshakes.
 **Action:** Always use connection pooling (e.g., `requests.Session()` or reusing API clients) for tasks that may batch process multiple requests, such as iterating through text boxes in translation pipelines.
