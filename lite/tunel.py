"""Abre o link público (túnel rápido do Cloudflare) só para a versão simples (porta 8100).

Rode com `python -m lite.tunel`. O endereço muda a cada vez que o túnel abre; ele fica salvo no
banco e aparece na página de administração, já montado nos links dos convites.
"""

import re
import subprocess
import sys

from lite import db

PORTA = 8100


def main():
    db.migrar()
    try:
        proc = subprocess.Popen(["cloudflared", "tunnel", "--no-autoupdate", "--url", f"http://localhost:{PORTA}"],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    except FileNotFoundError:
        print("cloudflared não está instalado (brew install cloudflared)", flush=True)
        sys.exit(1)
    try:
        for linha in proc.stdout:
            m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", linha)
            if m:
                with db.conexao() as con:
                    db.definir(con, "url_publica", m.group(0))
                print(f"link público: {m.group(0)}", flush=True)
            elif "ERR" in linha:
                print(linha.rstrip(), flush=True)
    finally:
        with db.conexao() as con:
            db.definir(con, "url_publica", "")
        proc.terminate()


if __name__ == "__main__":
    main()
