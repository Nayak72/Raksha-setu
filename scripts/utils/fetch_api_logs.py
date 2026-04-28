import urllib.request
import json
import logging
import os

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logging.basicConfig(level=logging.DEBUG)

req = urllib.request.Request("http://127.0.0.1:8001/api/v1/agent-logs")
with urllib.request.urlopen(req) as response:
    body = response.read()
    data = json.loads(body)
    log_path = os.path.join(project_root, "logs", "api_logs.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Status: {response.status}")
    print(f"Returned {len(data)} items")
