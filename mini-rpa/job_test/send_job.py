# send_job.py
import requests
import pathlib

ORCH_URL = "http://127.0.0.1:8000"
AGENT_URL = "http://127.0.0.1:5001"

username = r"notedell_diogo\diogo"
password = "020406"

script_text = pathlib.Path("automation_example.py").read_text(encoding="utf-8")

payload = {
    "agent_url": AGENT_URL,
    "task_name": "DemoBot_Run",
    "username": username,
    "password": password,
    "script_text": script_text,
    "interactive_hint": True  # defina False se não quer tentar UI
}

r = requests.post(f"{ORCH_URL}/dispatch", json=payload, timeout=30)
print(r.status_code, r.json())
