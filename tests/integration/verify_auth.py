import requests
url = "http://localhost:8080/chat/completions"
headers = {
    "Authorization": "Bearer sk-1234",
    "Content-Type": "application/json"
}
data = {
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "ping"}]
}
try:
    resp = requests.post(url, json=data, headers=headers)
    print(f"Status: {resp.status_code}")
    print(f"Body: {resp.text}")
except Exception as e:
    print(f"Error: {e}")
