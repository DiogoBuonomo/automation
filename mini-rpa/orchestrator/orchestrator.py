# orchestrator.py
import os
import base64
import requests
import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from cryptography.fernet import Fernet

app = FastAPI()
FERNET = Fernet(os.environ["ORCH_FERNET_KEY"])


class DispatchReq(BaseModel):
    agent_url: str                 # ex: "http://AGENTE:5001"
    task_name: str                 # nome da Scheduled Task no agente
    username: str                  # DOMINIO\usuario
    # senha em texto (será criptografada para trânsito)
    password: str
    script_text: str               # conteúdo do automation.py (texto)
    interactive_hint: bool = False  # tenta UI se houver sessão


@app.post("/dispatch")
def dispatch(req: DispatchReq):
    try:
        cipher = FERNET.encrypt(req.password.encode()).decode()
    except Exception as e:
        raise HTTPException(400, f"Erro criptografando senha: {e}")

    payload = {
        "task_name": req.task_name,
        "username": req.username,
        "cred_ciphertext": cipher,
        "script_b64": base64.b64encode(req.script_text.encode()).decode(),
        "working_dir": None,
        "interactive_hint": req.interactive_hint
    }
    try:
        r = requests.post(f"{req.agent_url}/run", json=payload, timeout=30)
        r.raise_for_status()
        return {"dispatched_at": datetime.datetime.utcnow().isoformat()+"Z", "agent_response": r.json()}
    except Exception as e:
        raise HTTPException(502, f"Falha ao contatar agente: {e}")
