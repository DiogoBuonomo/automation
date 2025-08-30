import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

FERNET_KEY = os.getenv("FERNET_KEY")
fernet = Fernet(FERNET_KEY)


def encrypt_message(message: str) -> str:
    return fernet.encrypt(message.encode()).decode()


def decrypt_message(token: str) -> str:
    return fernet.decrypt(token.encode()).decode()
