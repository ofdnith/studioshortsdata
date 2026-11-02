"""Site da versão simples (porta 8100).

- /c/{código}: página do amigo (digita o tema, acompanha e baixa os vídeos). Só com convite.
- /admin: convites, teto de gasto e link público. Só abre direto no seu Mac (nunca pelo túnel).
"""

import ipaddress
import os
from pathlib import Path
from urllib.parse import urlencode

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.ambiente import carregar_env
from app.config import VOZES
from lite import db

AQUI = Path(__file__).parent
carregar_env()
db.migrar()

app = FastAPI(title="Estúdio · versão de teste", docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory=AQUI.parent / "app" / "static"), name="static")
app.mount("/lite-static", StaticFiles(directory=AQUI / "static"), name="lite-static")
templates = Jinja2Templates(directory=AQUI / "templates")
templates.env.globals.update(vozes=VOZES)

MAX_TEMA = 160
CABECALHOS_TUNEL = ("cf-connecting-ip", "cf-ray", "x-forwarded-for", "cf-visitor")


def _local(request: Request) -> bool:
    """Verdadeiro só para quem abre direto no Mac. Pelo túnel chegam cabeçalhos do Cloudflare."""
    if any(h in request.headers for h in CABECALHOS_TUNEL):
        return False
    try:
        return ipaddress.ip_address(request.client.host).is_loopback
    except (ValueError, AttributeError):
        return False


def _ir(url: str, **params) -> RedirectResponse:
    params = {k: v for k, v in params.items() if v}
    return RedirectResponse(url + ("?" + urlencode(params) if params else ""), status_code=303)


def _estimativa(con) -> float:
    from app.roteirista import provedores as pv
    m = pv.precos(None, db.ajuste(con, "modelo"))
    return pv.estimativa(m, "medium") if m else 0.3


def _convite(con, codigo: str):
    c = con.execute("SELECT * FROM convite WHERE codigo = ? AND ativo = 1", (codigo,)).fetchone()
    if not c:
        raise HTTPException(404, "Convite não encontrado ou desativado.")
    return c


@app.exception_handler(HTTPException)
def _erro(request: Request, exc: HTTPException):
    return templates.TemplateResponse(request, "inicio.html", {"erro": exc.detail}, status_code=exc.status_code)


@app.get("/", response_class=HTMLResponse)
def inicio(request: Request):
    if _local(request):
        return _ir("/admin")
    return templates.TemplateResponse(request, "inicio.html", {})


# ---------------------------------------------------------------- amigo

def _ctx_amigo(con, c) -> dict:
    videos = con.execute("SELECT * FROM video WHERE convite = ? ORDER BY id DESC", (c["codigo"],)).fetchall()
    fila = {r["id"]: i + 1 for i, r in enumerate(con.execute("SELECT id FROM video WHERE status = 'na_fila' ORDER BY id"))}
    restam = max(0, c["limite"] - db.usados(con, c["codigo"]))
    sem_verba = db.gasto_total(con) + _estimativa(con) > float(db.ajuste(con, "teto_usd"))
    ocupado = any(v["status"] in ("na_fila", "rodando") for v in videos)
    return dict(c=c, videos=videos, fila=fila, restam=restam, sem_verba=sem_verba, ocupado=ocupado,
                rodando=ocupado)


@app.get("/c/{codigo}", response_class=HTMLResponse)
def amigo(request: Request, codigo: str, erro: str = "", msg: str = ""):
    with db.conexao() as con:
        ctx = _ctx_amigo(con, _convite(con, codigo))
    return templates.TemplateResponse(request, "convite.html", {**ctx, "erro": erro, "msg": msg})


@app.get("/c/{codigo}/lista", response_class=HTMLResponse)
def amigo_lista(request: Request, codigo: str):
    with db.conexao() as con:
        ctx = _ctx_amigo(con, _convite(con, codigo))
    return templates.TemplateResponse(request, "_lista.html", ctx)


@app.post("/c/{codigo}/gerar")
def amigo_gerar(codigo: str, tema: str = Form(""), voz: str = Form("pf_dora")):
    tema = " ".join(tema.split())[:MAX_TEMA]
    with db.conexao() as con:
        c = _convite(con, codigo)
        ctx = _ctx_amigo(con, c)
        if len(tema) < 8:
            return _ir(f"/c/{codigo}", erro="Escreva o tema com um pouco mais de detalhe.")
        if ctx["ocupado"]:
            return _ir(f"/c/{codigo}", erro="Espere o seu vídeo atual terminar antes de pedir outro.")
        if ctx["restam"] <= 0:
            return _ir(f"/c/{codigo}", erro="Você já usou todos os vídeos deste convite.")
        if ctx["sem_verba"]:
            return _ir(f"/c/{codigo}", erro="O teste atingiu o limite de gasto. Avise quem te convidou.")
        con.execute("INSERT INTO video (convite, tema, voz) VALUES (?, ?, ?)",
                    (codigo, tema, voz if voz in VOZES else "pf_dora"))
    return _ir(f"/c/{codigo}", msg="Pedido recebido! O vídeo fica pronto em alguns minutos.")


@app.get("/c/{codigo}/video/{vid}.mp4")
def amigo_video(codigo: str, vid: int, baixar: int = 0):
    with db.conexao() as con:
        _convite(con, codigo)
        v = con.execute("SELECT * FROM video WHERE id = ? AND convite = ? AND status = 'ok'", (vid, codigo)).fetchone()
    return _arquivo(v, "video.mp4", baixar)


@app.get("/c/{codigo}/capa/{vid}.png")
def amigo_capa(codigo: str, vid: int):
    with db.conexao() as con:
        _convite(con, codigo)
        v = con.execute("SELECT * FROM video WHERE id = ? AND convite = ? AND status = 'ok'", (vid, codigo)).fetchone()
    return _arquivo(v, "video_capa.png")


def _arquivo(v, nome: str, baixar: int = 0):
    if not v:
        raise HTTPException(404, "Vídeo não encontrado.")
    caminho = db.pasta_video(v["id"]) / nome
    if not caminho.exists():
        raise HTTPException(404, "Arquivo não encontrado.")
    extra = {"filename": f"video_{v['id']}.mp4"} if baixar else {}
    return FileResponse(caminho, **extra)


# ---------------------------------------------------------------- administração (só no Mac)

def _so_local(request: Request):
    if not _local(request):
        raise HTTPException(404, "Página não encontrada.")


@app.get("/admin", response_class=HTMLResponse)
def admin(request: Request, msg: str = "", erro: str = ""):
    _so_local(request)
    from app.roteirista import provedores as pv
    with db.conexao() as con:
        convites = con.execute(
            "SELECT convite.*, (SELECT count(*) FROM video WHERE video.convite = convite.codigo AND status != 'erro') AS usados,"
            " (SELECT coalesce(sum(custo), 0) FROM video WHERE video.convite = convite.codigo) AS gasto"
            " FROM convite ORDER BY criado_em DESC").fetchall()
        videos = con.execute("SELECT video.*, convite.nome FROM video JOIN convite ON convite.codigo = video.convite"
                             " ORDER BY video.id DESC LIMIT 40").fetchall()
        ctx = dict(convites=convites, videos=videos, gasto=db.gasto_total(con), teto=float(db.ajuste(con, "teto_usd")),
                   modelo=db.ajuste(con, "modelo"), url=db.ajuste(con, "url_publica"), estimativa=_estimativa(con),
                   modelos=pv.MODELOS_ATIVOS, tem_chave=bool(os.environ.get("OPENAI_API_KEY")),
                   teste=os.environ.get("LITE_FALSO") == "1")
    return templates.TemplateResponse(request, "admin.html", {**ctx, "msg": msg, "erro": erro})


@app.post("/admin/convites")
def admin_convite(request: Request, nome: str = Form(""), limite: int = Form(3)):
    _so_local(request)
    nome = nome.strip()[:60]
    if not nome:
        return _ir("/admin", erro="Dê um nome ao convite (ex.: o nome do amigo).")
    with db.conexao() as con:
        con.execute("INSERT INTO convite (codigo, nome, limite) VALUES (?, ?, ?)",
                    (db.novo_codigo(), nome, max(1, min(20, limite))))
    return _ir("/admin", msg=f"Convite criado para {nome}.")


@app.post("/admin/convites/{codigo}")
def admin_convite_mudar(request: Request, codigo: str, acao: str = Form(""), limite: int = Form(0)):
    _so_local(request)
    with db.conexao() as con:
        if acao == "desativar":
            con.execute("UPDATE convite SET ativo = 0 WHERE codigo = ?", (codigo,))
        elif acao == "ativar":
            con.execute("UPDATE convite SET ativo = 1 WHERE codigo = ?", (codigo,))
        elif acao == "limite" and limite > 0:
            con.execute("UPDATE convite SET limite = ? WHERE codigo = ?", (min(20, limite), codigo))
    return _ir("/admin", msg="Convite atualizado.")


@app.post("/admin/ajustes")
def admin_ajustes(request: Request, teto: str = Form(""), modelo: str = Form("")):
    _so_local(request)
    from app.roteirista import provedores as pv
    with db.conexao() as con:
        try:
            db.definir(con, "teto_usd", f"{max(0.0, float(teto.replace(',', '.'))):.2f}")
        except ValueError:
            return _ir("/admin", erro="Teto inválido.")
        if modelo in {m.id for m in pv.MODELOS_ATIVOS}:
            db.definir(con, "modelo", modelo)
    return _ir("/admin", msg="Ajustes salvos.")


@app.post("/admin/videos/{vid}/cancelar")
def admin_cancelar(request: Request, vid: int):
    _so_local(request)
    with db.conexao() as con:
        con.execute("UPDATE video SET status = 'erro', erro = 'Cancelado pelo administrador.'"
                    " WHERE id = ? AND status = 'na_fila'", (vid,))
    return _ir("/admin", msg="Pedido cancelado.")


@app.get("/admin/video/{vid}.mp4")
def admin_video(request: Request, vid: int):
    _so_local(request)
    with db.conexao() as con:
        v = con.execute("SELECT * FROM video WHERE id = ? AND status = 'ok'", (vid,)).fetchone()
    return _arquivo(v, "video.mp4")
