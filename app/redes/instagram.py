"""Instagram API with Instagram Login: OAuth, tokens de longa duração e publicação de Reels.

Referência (conferida em 2026-11-02):
- Business Login for Instagram: authorize em www.instagram.com/oauth/authorize; código vale 1 h;
  troca em POST api.instagram.com/oauth/access_token; token longo (≈60 dias) em
  GET graph.instagram.com/access_token (ig_exchange_token); renovação em
  GET graph.instagram.com/refresh_access_token (token com 24 h+ e ainda válido).
- Publicação: POST /{ig-user-id}/media (media_type=REELS, video_url pública, caption);
  GET /{container}?fields=status_code até FINISHED; POST /{ig-user-id}/media_publish.
  Upload retomável é só para Facebook Login: aqui o vídeo vai por URL pública (túnel).
- Limite: GET /{ig-user-id}/content_publishing_limit.
"""

import os
import secrets
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

VERSAO = "v26.0"
GRAPH = f"https://graph.instagram.com/{VERSAO}"
ESCOPOS = ["instagram_business_basic", "instagram_business_content_publish"]
ENV = {"app_id": "INSTAGRAM_APP_ID", "secret": "INSTAGRAM_APP_SECRET", "redirect": "INSTAGRAM_REDIRECT_URI"}
REDIRECT_PADRAO = "https://localhost:8443/contas/instagram/retorno"


class ErroInstagram(Exception):
    pass


def credenciais() -> dict:
    return {k: os.environ.get(v, "") for k, v in ENV.items()} | \
        {"redirect": os.environ.get(ENV["redirect"]) or REDIRECT_PADRAO}


def configurado() -> bool:
    c = credenciais()
    return bool(c["app_id"] and c["secret"])


def _erro(r: httpx.Response) -> ErroInstagram:
    try:
        e = r.json().get("error", {})
        msg = e.get("error_user_msg") or e.get("message") or r.text[:300]
    except ValueError:
        msg = r.text[:300]
    return ErroInstagram(f"Instagram {r.status_code}: {msg}")


# ---------------------------------------------------------------- OAuth

def url_autorizacao(state: str) -> str:
    c = credenciais()
    return "https://www.instagram.com/oauth/authorize?" + urlencode({
        "client_id": c["app_id"], "redirect_uri": c["redirect"], "response_type": "code",
        "scope": ",".join(ESCOPOS), "state": state, "force_reauth": "true"})


def novo_state() -> str:
    return secrets.token_urlsafe(16)


def extrair_codigo(url_ou_codigo: str) -> tuple[str, str | None]:
    """Aceita a URL completa do retorno (copiada do navegador) ou só o código."""
    texto = url_ou_codigo.strip()
    if texto.endswith("#_"):
        texto = texto[:-2]
    if texto.startswith("http"):
        q = parse_qs(urlparse(texto).query)
        if "error" in q:
            raise ErroInstagram(f"Autorização negada: {q.get('error_description', q['error'])[0]}")
        codigo = (q.get("code") or [""])[0]
        state = (q.get("state") or [None])[0]
    else:
        codigo, state = texto, None
    codigo = codigo.split("#")[0].strip()
    if not codigo:
        raise ErroInstagram("Não encontrei o parâmetro 'code' na URL colada.")
    return codigo, state


def conectar(codigo: str) -> dict:
    """Troca o código por token curto, depois por token longo, e lê o perfil."""
    c = credenciais()
    r = httpx.post("https://api.instagram.com/oauth/access_token", timeout=30, data={
        "client_id": c["app_id"], "client_secret": c["secret"], "grant_type": "authorization_code",
        "redirect_uri": c["redirect"], "code": codigo})
    if r.status_code != 200:
        raise _erro(r)
    dados = r.json()
    dados = dados["data"][0] if "data" in dados else dados
    curto = dados["access_token"]
    escopos = dados.get("permissions", "")
    r = httpx.get("https://graph.instagram.com/access_token", timeout=30, params={
        "grant_type": "ig_exchange_token", "client_secret": c["secret"], "access_token": curto})
    if r.status_code != 200:
        raise _erro(r)
    longo = r.json()
    perfil = ler_perfil(longo["access_token"])
    return {"access_token": longo["access_token"], "expira_em": _expira(longo.get("expires_in", 5184000)),
            "conta_id": str(perfil.get("user_id") or dados.get("user_id")), "usuario": perfil.get("username"),
            "escopos": escopos if isinstance(escopos, str) else ",".join(escopos)}


def renovar(token: str) -> dict:
    r = httpx.get("https://graph.instagram.com/refresh_access_token", timeout=30,
                  params={"grant_type": "ig_refresh_token", "access_token": token})
    if r.status_code != 200:
        raise _erro(r)
    d = r.json()
    return {"access_token": d["access_token"], "expira_em": _expira(d.get("expires_in", 5184000))}


def _expira(segundos: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=int(segundos))).strftime("%Y-%m-%d %H:%M:%S")


def ler_perfil(token: str) -> dict:
    r = httpx.get(f"{GRAPH}/me", timeout=30, params={"fields": "user_id,username,account_type",
                                                     "access_token": token})
    if r.status_code != 200:
        raise _erro(r)
    return r.json()


def limite(conta) -> dict:
    r = httpx.get(f"{GRAPH}/{conta['conta_id']}/content_publishing_limit", timeout=30,
                  params={"fields": "quota_usage,config", "access_token": conta["access_token"]})
    if r.status_code != 200:
        raise _erro(r)
    d = (r.json().get("data") or [{}])[0]
    return {"uso": d.get("quota_usage", 0), "total": (d.get("config") or {}).get("quota_total", 50)}


# ---------------------------------------------------------------- publicação

def publicar_reel(conta, video_url: str, legenda: str, log=print, espera_max_s: int = 900) -> dict:
    """Cria o contêiner, espera o processamento e publica. Devolve {'id', 'link'}."""
    token = conta["access_token"]
    uid = conta["conta_id"]
    lim = limite(conta)
    log(f"limite de publicação: {lim['uso']}/{lim['total']} nas últimas 24 h")
    if lim["uso"] >= lim["total"]:
        raise ErroInstagram("Limite de publicações das últimas 24 h atingido.")
    r = httpx.post(f"{GRAPH}/{uid}/media", timeout=60, data={
        "media_type": "REELS", "video_url": video_url, "caption": legenda, "access_token": token})
    if r.status_code != 200:
        raise _erro(r)
    container = r.json()["id"]
    log(f"contêiner criado ({container}); o Instagram está baixando e processando o vídeo…")
    fim = time.time() + espera_max_s
    status = ""
    while time.time() < fim:
        time.sleep(15)
        r = httpx.get(f"{GRAPH}/{container}", timeout=30, params={"fields": "status_code,status",
                                                                   "access_token": token})
        if r.status_code != 200:
            raise _erro(r)
        status = r.json().get("status_code", "")
        if status == "FINISHED":
            break
        if status in ("ERROR", "EXPIRED"):
            raise ErroInstagram(f"Processamento do vídeo falhou: {r.json().get('status', status)}")
    if status != "FINISHED":
        raise ErroInstagram("O Instagram não terminou de processar o vídeo a tempo.")
    log("vídeo processado; publicando…")
    r = httpx.post(f"{GRAPH}/{uid}/media_publish", timeout=60,
                   data={"creation_id": container, "access_token": token})
    if r.status_code != 200:
        raise _erro(r)
    midia = r.json()["id"]
    link = None
    r = httpx.get(f"{GRAPH}/{midia}", timeout=30, params={"fields": "permalink", "access_token": token})
    if r.status_code == 200:
        link = r.json().get("permalink")
    return {"id": midia, "link": link}
