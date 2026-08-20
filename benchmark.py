import time
import requests

url = "https://httpbin.org/post"
data = {"text": "hello"}

# Without session
start = time.time()
for _ in range(5):
    requests.post(url, data=data)
end_no_session = time.time() - start

# With session
start = time.time()
session = requests.Session()
for _ in range(5):
    session.post(url, data=data)
end_with_session = time.time() - start

print(f"Without session: {end_no_session:.4f}s")
print(f"With session: {end_with_session:.4f}s")
