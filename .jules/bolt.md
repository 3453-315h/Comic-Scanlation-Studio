## 2024-11-01 - [Pool HTTP connections in Translator]
 **Learning:** [In Python, the `requests` library will create a new TCP connection for every single `requests.post()` call. If many small text snippets are translated via DeepL in loops, this causes massive overhead due to repeated TLS handshakes. Initializing a `requests.Session()` avoids this.]
 **Action:** [When calling external APIs in a batch/loop (like DeepL translations), instantiate and reuse a `requests.Session()` object rather than module-level functions.]
