from dotenv import load_dotenv
import os

load_dotenv()  # carrega as variáveis do .env

FERNET_KEY = os.getenv("ORCH_FERNET_KEY") or os.getenv("AGENT_FERNET_KEY")
