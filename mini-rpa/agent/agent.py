# agent.py
import os
import subprocess
import json
import base64
import tempfile
import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from cryptography.fernet import Fernet

app = FastAPI()

FERNET = Fernet(os.environ["AGENT_FERNET_KEY"])


class JobPayload(BaseModel):
    task_name: str               # Nome da Scheduled Task (ex: "DemoBot_Run")
    username: str                # DOMINIO\usuario ou maquina\usuario
    cred_ciphertext: str         # senha criptografada em base64 (Fernet)
    script_b64: str              # automação (conteúdo .py) em base64
    working_dir: str | None = None
    interactive_hint: bool = False  # abre Notepad se houver sessão interativa


def windows_quote(s: str) -> str:
    return f'"{s}"'


def create_python_runner(script_path: str, interactive_hint: bool):
    # Cria um wrapper .cmd para executar o Python de forma confiável
    content = f"""@echo off
setlocal
REM Ajuste o caminho do Python se necessário:
where python >nul 2>nul
IF %ERRORLEVEL% NEQ 0 (
  echo Python não encontrado no PATH. Ajuste o runner.cmd para apontar para o python.exe.
  exit /b 1
)
python {windows_quote(script_path)} {"--interactive" if interactive_hint else ""}
endlocal
"""
    runner = os.path.join(os.path.dirname(script_path), "runner.cmd")
    with open(runner, "w", encoding="utf-8") as f:
        f.write(content)
    return runner


def ensure_task(task_name: str, username: str, password: str, command: str, start_in: str | None):
    # Cria/atualiza a Scheduled Task para rodar "mesmo sem usuário logado"
    # /RL HIGHEST = privilégios elevados (se suportado)
    args_create = [
        "schtasks", "/Create",
        "/TN", task_name,
        "/TR", command,
        "/SC", "ONCE",
        "/ST", (datetime.datetime.now() +
                datetime.timedelta(minutes=2)).strftime("%H:%M"),
        "/RU", username,
        "/RP", password,
        "/RL", "HIGHEST",
        "/F"
    ]
    if start_in:
        # Agendador não tem /StartIn; usamos workdir via wrapper .cmd
        pass

    result = subprocess.run(
        args_create, capture_output=True, text=True, shell=False)
    if result.returncode != 0:
        # Se já existir, alguns ambientes precisam /Change para ajustar credenciais
        # Tenta alterar
        args_change = [
            "schtasks", "/Change",
            "/TN", task_name,
            "/RU", username,
            "/RP", password
        ]
        ch = subprocess.run(args_change, capture_output=True,
                            text=True, shell=False)
        if ch.returncode != 0:
            raise RuntimeError(
                f"Falha ao criar/alterar tarefa: {result.stderr}\n{ch.stderr}")


def run_task(task_name: str):
    result = subprocess.run(["schtasks", "/Run", "/TN", task_name],
                            capture_output=True, text=True, shell=False)
    if result.returncode != 0:
        raise RuntimeError(f"Falha ao iniciar tarefa: {result.stderr}")


@app.post("/run")
def run_job(payload: JobPayload):
    try:
        password = FERNET.decrypt(payload.cred_ciphertext.encode()).decode()
    except Exception as e:
        raise HTTPException(400, f"Credenciais inválidas/cripto: {e}")

    tmpdir = payload.working_dir or tempfile.mkdtemp(prefix="bot_job_")
    script_path = os.path.join(tmpdir, "automation.py")
    with open(script_path, "wb") as f:
        f.write(base64.b64decode(payload.script_b64))

    runner_cmd = create_python_runner(script_path, payload.interactive_hint)

    # Importante: usar caminho absoluto do wrapper .cmd
    ensure_task(
        task_name=payload.task_name,
        username=payload.username,
        password=password,
        command=windows_quote(runner_cmd),
        start_in=tmpdir
    )
    run_task(payload.task_name)
    return {"status": "started", "task": payload.task_name, "workdir": tmpdir}
