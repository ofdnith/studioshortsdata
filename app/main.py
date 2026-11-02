"""Servidor web do estúdio (FastAPI + Jinja2 + HTMX)."""

import logging
import os
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import dados_ficticios as fic

RAIZ = Path(__file__).parent
DEV = os.environ.get("ESTUDIO_DEV") == "1"
# Muda a cada reinício do servidor; o navegador recarrega quando percebe a troca.
ID_BOOT = str(time.time_ns())

class _SemPingDev(logging.Filter):
    """Esconde do log as consultas do recarregamento automático."""

    def filter(self, record: logging.LogRecord) -> bool:
        return "/_dev/boot" not in record.getMessage()


logging.getLogger("uvicorn.access").addFilter(_SemPingDev())

app = FastAPI(title="Estúdio")
app.mount("/static", StaticFiles(directory=RAIZ / "static"), name="static")
templates = Jinja2Templates(directory=RAIZ / "templates")
templates.env.globals.update(dev=DEV, rotulo_status=fic.ROTULO_STATUS)


def pagina(request: Request, nome: str, aba: str, **ctx) -> HTMLResponse:
    return templates.TemplateResponse(request, nome, {"aba": aba, **ctx})


@app.get("/")
def inicio():
    return RedirectResponse("/temas")


@app.get("/temas")
def temas(request: Request, q: str = "", categoria: str = "", status: str = ""):
    lista = fic.filtrar_temas(q, categoria, status)
    ctx = dict(
        temas=lista,
        q=q,
        categoria=categoria,
        status=status,
        categorias=fic.categorias(),
        todos_status=list(fic.ROTULO_STATUS),
    )
    # Busca/filtro via HTMX: devolve só as linhas da tabela.
    if request.headers.get("HX-Request") and request.headers.get("HX-Target") == "linhas-temas":
        return templates.TemplateResponse(request, "_linhas_temas.html", ctx)
    return pagina(request, "temas.html", "temas", **ctx)


@app.get("/producao")
def producao(request: Request):
    return pagina(request, "producao.html", "producao", fila=fic.FILA_PRODUCAO)


@app.get("/agenda")
def agenda(request: Request):
    return pagina(
        request,
        "agenda.html",
        "agenda",
        videos=fic.BIBLIOTECA,
        agendados=fic.AGENDADOS,
        contas=fic.CONTAS,
    )


@app.get("/_dev/boot", response_class=PlainTextResponse)
def dev_boot():
    return ID_BOOT
