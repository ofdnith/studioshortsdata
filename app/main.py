"""Servidor web do estúdio (FastAPI + Jinja2 + HTMX)."""

import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlencode

from fastapi import FastAPI, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import dados_ficticios as fic
from app import temas as repo
from app.config import CONFIG_PADRAO, PRIORIDADES, STATUS_TEMA, TONS, VOZES, config_efetiva
from app.db import RAIZ as RAIZ_PROJETO
from app.db import conexao, migrar

RAIZ = Path(__file__).parent
STORAGE = RAIZ_PROJETO / "storage"
CSV_INICIAL = RAIZ_PROJETO / "temas_iniciais.csv"
DEV = os.environ.get("ESTUDIO_DEV") == "1"
# Muda a cada reinício do servidor; o navegador recarrega quando percebe a troca.
ID_BOOT = str(time.time_ns())


class _SemPingDev(logging.Filter):
    """Esconde do log as consultas do recarregamento automático."""

    def filter(self, record: logging.LogRecord) -> bool:
        return "/_dev/boot" not in record.getMessage()


logging.getLogger("uvicorn.access").addFilter(_SemPingDev())


@asynccontextmanager
async def ciclo_de_vida(_app: FastAPI):
    migrar()
    yield


STORAGE.mkdir(exist_ok=True)
app = FastAPI(title="Estúdio", lifespan=ciclo_de_vida)
app.mount("/static", StaticFiles(directory=RAIZ / "static"), name="static")
app.mount("/storage", StaticFiles(directory=STORAGE), name="storage")
templates = Jinja2Templates(directory=RAIZ / "templates")
templates.env.globals.update(
    dev=DEV, rotulo_status=STATUS_TEMA, prioridades=PRIORIDADES,
    vozes=VOZES, tons=TONS, padrao=CONFIG_PADRAO,
)


def pagina(request: Request, nome: str, aba: str, **ctx) -> HTMLResponse:
    ctx.setdefault("msg", request.query_params.get("msg", ""))
    ctx.setdefault("erro", request.query_params.get("erro", ""))
    return templates.TemplateResponse(request, nome, {"aba": aba, **ctx})


def redirecionar(url: str, **params) -> RedirectResponse:
    params = {k: v for k, v in params.items() if v}
    return RedirectResponse(url + ("?" + urlencode(params) if params else ""), status_code=303)


@app.get("/")
def inicio():
    return RedirectResponse("/temas")


# ---------------------------------------------------------------- Temas

def _ctx_lista(con, f: repo.Filtros) -> dict:
    lista = repo.listar(con, f)
    return dict(temas=lista, f=f, total=len(lista))


@app.get("/temas")
def temas(request: Request, q: str = "", categoria: str = "", prioridade: str = "",
          status: str = ""):
    f = repo.Filtros(q, categoria, prioridade, status)
    with conexao() as con:
        ctx = _ctx_lista(con, f)
        # Busca/filtro via HTMX: devolve só as linhas da tabela.
        if request.headers.get("HX-Target") == "linhas-temas":
            return templates.TemplateResponse(request, "_linhas_temas.html", ctx)
        ctx.update(categorias=repo.categorias(con), contagem=repo.contar_por_status(con),
                   tem_csv_inicial=CSV_INICIAL.exists())
    return pagina(request, "temas.html", "temas", **ctx)


@app.post("/temas/acao")
async def temas_acao(request: Request):
    form = await request.form()
    acao = form.get("acao", "")
    ids = [int(i) for i in form.getlist("ids")]
    f = repo.Filtros(*(form.get(c, "") for c in ("q", "categoria", "prioridade", "status")))
    with conexao() as con:
        if not ids:
            msg = "Selecione pelo menos um tema."
        elif acao == "descartar":
            msg = f"{repo.mudar_status(con, ids, 'descartado')} tema(s) descartado(s)."
        elif acao == "restaurar":
            msg = f"{repo.mudar_status(con, ids, 'ideia')} tema(s) voltaram para Ideia."
        elif acao == "produzir":
            enviados, ignorados = repo.enviar_para_producao(con, ids)
            msg = f"{enviados} tema(s) enviados para produção."
            if ignorados:
                msg += f" {ignorados} ignorado(s): só temas com status Ideia podem ser enviados."
        else:
            msg = "Ação desconhecida."
        ctx = _ctx_lista(con, f)
    return templates.TemplateResponse(request, "_linhas_temas.html", {**ctx, "msg_oob": msg})


@app.post("/temas/importar")
async def temas_importar(arquivo: UploadFile | None = None, inicial: str = Form("")):
    try:
        if inicial:
            conteudo, nome = CSV_INICIAL.read_text(encoding="utf-8"), CSV_INICIAL.name
        elif arquivo and arquivo.filename:
            conteudo, nome = (await arquivo.read()).decode("utf-8-sig"), arquivo.filename
        else:
            return redirecionar("/temas", erro="Escolha um arquivo CSV.")
        with conexao() as con:
            importados, ignorados = repo.importar_csv(con, conteudo)
    except (ValueError, UnicodeDecodeError) as e:
        return redirecionar("/temas", erro=f"Não consegui importar: {e}")
    msg = f"{nome}: {importados} tema(s) importado(s)"
    if ignorados:
        msg += f", {ignorados} ignorado(s) (já existiam ou sem título)"
    return redirecionar("/temas", msg=msg + ".")


@app.get("/temas/novo")
def tema_novo(request: Request):
    with conexao() as con:
        cats = repo.categorias(con)
    return pagina(request, "tema.html", "temas", tema=None, categorias=cats,
                  config={}, efetiva=CONFIG_PADRAO, assets=[])


@app.post("/temas/novo")
async def tema_criar(request: Request):
    form = await request.form()
    try:
        with conexao() as con:
            tema_id = repo.criar(con, dict(form))
    except ValueError as e:
        return redirecionar("/temas/novo", erro=str(e))
    return redirecionar(f"/temas/{tema_id}", msg="Tema criado.")


def _listar_assets(tema_id: int) -> list[dict]:
    pasta = STORAGE / "temas" / str(tema_id)
    if not pasta.is_dir():
        return []
    return [
        {"nome": str(p.relative_to(pasta)), "url": f"/storage/{p.relative_to(STORAGE)}",
         "kb": max(1, p.stat().st_size // 1024),
         "tipo": p.suffix.lower().lstrip(".")}
        for p in sorted(pasta.rglob("*")) if p.is_file() and not p.name.startswith(".")
    ]


@app.get("/temas/{tema_id}")
def tema_detalhe(request: Request, tema_id: int):
    with conexao() as con:
        tema = repo.obter(con, tema_id)
        if not tema:
            return redirecionar("/temas", erro="Tema não encontrado.")
        cats = repo.categorias(con)
    config = repo.config_do_tema(tema)
    return pagina(request, "tema.html", "temas", tema=tema, categorias=cats, config=config,
                  efetiva=config_efetiva(config), assets=_listar_assets(tema_id))


@app.post("/temas/{tema_id}")
async def tema_salvar(request: Request, tema_id: int):
    form = await request.form()
    config = {
        "voz": form.get("voz", ""),
        "velocidade": float(form["velocidade"]) if form.get("velocidade") else "",
        "duracao_alvo_s": int(form["duracao_alvo_s"]) if form.get("duracao_alvo_s") else "",
        "tom": form.get("tom", ""),
        "instrucoes": form.get("instrucoes", "").strip(),
    }
    try:
        with conexao() as con:
            repo.atualizar(con, tema_id, dict(form), config)
    except ValueError as e:
        return redirecionar(f"/temas/{tema_id}", erro=str(e))
    return redirecionar(f"/temas/{tema_id}", msg="Alterações salvas.")


@app.get("/amostra-voz", response_class=HTMLResponse)
def amostra_voz(voz: str = "", velocidade: str = ""):
    """Gera (ou reaproveita) um MP3 curto com a voz e a velocidade escolhidas."""
    from motor.narracao import amostra

    voz = voz if voz in VOZES else CONFIG_PADRAO["voz"]
    try:
        vel = min(1.6, max(0.8, float(velocidade))) if velocidade else CONFIG_PADRAO["velocidade"]
    except ValueError:
        vel = CONFIG_PADRAO["velocidade"]
    destino = STORAGE / "amostras" / f"{voz}_{vel:.2f}.mp3"
    try:
        if not destino.exists():
            amostra(voz, vel, destino)
    except Exception as e:  # modelo ausente, ffmpeg etc.
        return HTMLResponse(f'<span class="vermelho pequeno">Não consegui gerar a amostra: {e}</span>')
    return HTMLResponse(
        f'<audio controls autoplay src="/storage/amostras/{destino.name}"></audio>'
        f'<span class="cinza pequeno">{VOZES[voz]} · {vel:g}×</span>')


# ---------------------------------------------------------------- Produção e Agenda

@app.get("/producao")
def producao(request: Request):
    with conexao() as con:
        fila = con.execute(
            "SELECT trabalho.*, tema.titulo FROM trabalho"
            " LEFT JOIN tema ON tema.id = trabalho.referencia_id"
            " WHERE trabalho.status IN ('na_fila', 'rodando', 'erro') ORDER BY trabalho.id"
        ).fetchall()
    return pagina(request, "producao.html", "producao", fila=fila)


@app.get("/agenda")
def agenda(request: Request):
    return pagina(request, "agenda.html", "agenda", ficticio=True,
                  videos=fic.BIBLIOTECA, agendados=fic.AGENDADOS, contas=fic.CONTAS)


@app.get("/_dev/boot", response_class=PlainTextResponse)
def dev_boot():
    return ID_BOOT
