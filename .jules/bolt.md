## 2024-03-24 - Reuse clients for external API calls

**Learning:** Repeated synchronous external API calls (such as deepL or OpenAI) in batch processing contexts cause a significant performance bottleneck due to repeated TLS handshakes for each API request.

**Action:** Always use connection pooling (like `requests.Session()`) or reuse external client instances (like `OpenAI()`) instead of repeatedly establishing new connections or instantiating clients when making consecutive external API calls.