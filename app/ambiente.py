"""Carrega o .env da raiz do projeto (sem sobrescrever variáveis já definidas)."""

import os
from pathlib import Path

ENV = Path(__file__).resolve().parent.parent / ".env"


def carregar_env() -> None:
    if not ENV.exists():
        return
    for linha in ENV.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        valor = valor.strip().strip('"').strip("'")
        if valor:
            os.environ.setdefault(chave.strip(), valor)
