import urllib.request
import json

url = "http://127.0.0.1:8001/api/v1/detect"
payload = {
    "zone_id": "cc0a2353-6648-406d-a8e2-32e792bb5de0",
    "count": 95,
    "metadata": {
        "source": "manual_test",
        "description": "Triggered agent workflow via HTTP API"
    }
}
data = json.dumps(payload).encode('utf-8')
req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'}, method='POST')

try:
    with urllib.request.urlopen(req) as response:
        print(f"Status: {response.status}")
        print(response.read().decode('utf-8'))
except Exception as e:
    print(f"Error: {e}")
