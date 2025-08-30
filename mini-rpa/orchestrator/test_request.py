import requests

url = "http://127.0.0.1:5000/send-task"
data = {"command": "echo Hello World"}

response = requests.post(url, json=data)

print("Status:", response.status_code)
print("Resposta:", response.json())
