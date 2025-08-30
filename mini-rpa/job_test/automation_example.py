# automation_example.py (conteúdo que você passará no dispatch)
import os
import sys
import time
import getpass
import pathlib
import subprocess


def ensure_dir(p):
    pathlib.Path(p).mkdir(parents=True, exist_ok=True)


def main():
    base = r"C:\Temp"
    ensure_dir(base)
    proof = os.path.join(base, "automation-proof.txt")
    with open(proof, "a", encoding="utf-8") as f:
        f.write(f"Rodou em {time.ctime()} como {getpass.getuser()}\n")

    # Se houver argumento --interactive E sessão interativa, tenta abrir notepad
    if "--interactive" in sys.argv:
        try:
            subprocess.Popen(["notepad.exe", proof], close_fds=True)
        except Exception as e:
            # Em sessão não interativa, isso vai falhar silenciosamente (ok)
            pass


if __name__ == "__main__":
    main()
