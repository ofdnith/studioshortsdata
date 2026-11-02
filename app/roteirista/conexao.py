"""Chaves de API no .env (nunca no Git) e teste de conexão (lista modelos: não consome crédito)."""

import os
import re
import time
from pathlib import Path

from app.ambiente import ENV
from app.roteirista.provedores import PROVEDORES

EXEMPLO = Path(ENV).with_name(".env.example")
CHAVES = [p["env"] for p in PROVEDORES.values()]


def mascarar(valor: str | None) -> str:
    if not valor:
        return ""
    return valor[:7] + "…" + valor[-4:] if len(valor) > 14 else "…" + valor[-3:]


def salvar_no_env(chave: str, valor: str) -> None:
    """Grava/atualiza CHAVE=valor no .env (cria a partir do .env.example) e no ambiente atual."""
    if not ENV.exists():
        ENV.write_text(EXEMPLO.read_text(encoding="utf-8") if EXEMPLO.exists() else "", encoding="utf-8")
    linhas = ENV.read_text(encoding="utf-8").splitlines()
    padrao = re.compile(rf"^\s*{re.escape(chave)}\s*=")
    feito = False
    for i, l in enumerate(linhas):
        if padrao.match(l):
            linhas[i] = f"{chave}={valor}"
            feito = True
    if not feito:
        linhas.append(f"{chave}={valor}")
    ENV.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    try:
        os.chmod(ENV, 0o600)
    except OSError:
        pass
    if valor:
        os.environ[chave] = valor
    else:
        os.environ.pop(chave, None)


def sincronizar_do_env() -> None:
    """Relê as chaves de IA do .env (o worker chama antes de cada trabalho)."""
    valores = {}
    if ENV.exists():
        for l in ENV.read_text(encoding="utf-8").splitlines():
            if "=" in l and not l.strip().startswith("#"):
                k, v = l.split("=", 1)
                valores[k.strip()] = v.strip().strip('"').strip("'")
    for k in CHAVES:
        if valores.get(k):
            os.environ[k] = valores[k]
        else:
            os.environ.pop(k, None)


def testar(provedor: str) -> dict:
    """{'ok', 'mensagem', 'modelos': [ids], 'ms'} — só lista modelos (gratuito)."""
    env = PROVEDORES[provedor]["env"]
    if not os.environ.get(env):
        return {"ok": False, "mensagem": "Nenhuma chave configurada.", "modelos": [], "ms": 0}
    t0 = time.time()
    try:
        if provedor == "anthropic":
            import anthropic
            c = anthropic.Anthropic(timeout=20, max_retries=0)
            ids = [m.id for m in c.models.list(limit=100)]
        else:
            from openai import OpenAI
            c = OpenAI(timeout=20, max_retries=0)
            ids = sorted(m.id for m in c.models.list())
        return {"ok": True, "mensagem": f"Conectado: {len(ids)} modelos disponíveis na sua conta.",
                "modelos": ids, "ms": int((time.time() - t0) * 1000)}
    except Exception as e:
        nome = type(e).__name__
        texto = str(e)
        if "AuthenticationError" in nome or "401" in texto:
            msg = "Chave inválida ou revogada (401)."
        elif "PermissionDenied" in nome or "403" in texto:
            msg = "A chave não tem permissão (403)."
        elif "RateLimit" in nome or "429" in texto:
            msg = "Limite de uso ou sem crédito (429)."
        elif "Connection" in nome or "Timeout" in nome:
            msg = "Sem conexão com a API (rede)."
        else:
            msg = f"{nome}: {texto[:200]}"
        return {"ok": False, "mensagem": msg, "modelos": [], "ms": int((time.time() - t0) * 1000)}
