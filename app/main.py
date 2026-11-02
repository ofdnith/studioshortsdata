"""Servidor web do estúdio (FastAPI + Jinja2 + HTMX)."""

import json
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

from app import custos as cst
from app import producao as prod
from app import temas as repo
from app.ambiente import carregar_env
from app.config import CONFIG_PADRAO, PRIORIDADES, STATUS_TEMA, TONS, VOZES, config_efetiva
from app.db import RAIZ as RAIZ_PROJETO
from app.db import conexao, migrar

RAIZ = Path(__file__).parent
STORAGE = RAIZ_PROJETO / "storage"
CSV_INICIAL = RAIZ_PROJETO / "temas_iniciais.csv"
carregar_env()
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
    vozes=VOZES, tons=TONS, padrao=CONFIG_PADRAO, categorias_custo=cst.CATEGORIAS,
    categorias_manuais=cst.MANUAIS, origens={"claude": "gerado", "correcao": "corrigido", "edicao": "editado",
                                             "importado": "importado"},
)
templates.env.filters["dinheiro"] = cst.moeda_fmt
templates.env.filters["de_json"] = lambda s: json.loads(s or "null")


def pagina(request: Request, nome: str, aba: str, **ctx) -> HTMLResponse:
    ctx.setdefault("msg", request.query_params.get("msg", ""))
    ctx.setdefault("erro", request.query_params.get("erro", ""))
    return templates.TemplateResponse(request, nome, {"aba": aba, **ctx})


def redirecionar(url: str, **params) -> RedirectResponse:
    params = {k: v for k, v in params.items() if v}
    sep = "&" if "?" in url else "?"
    return RedirectResponse(url + (sep + urlencode(params) if params else ""), status_code=303)


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


def _modelos_ctx() -> dict:
    from app.roteirista import provedores as pv
    return {"modelos_ia": pv.MODELOS, "provedores_ia": pv.PROVEDORES}


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
        roteiros = prod.versoes(con, tema_id)
        correcoes = con.execute("SELECT * FROM correcao WHERE tema_id = ? ORDER BY id DESC",
                                (tema_id,)).fetchall()
        pendente = prod.trabalho_pendente(con, "roteiro", tema_id)
        custos = cst.resumo(con, tema_id)
        render = prod.ultimo_render(con, tema_id)
        video = con.execute("SELECT * FROM video WHERE tema_id = ?", (tema_id,)).fetchone()
        esc, chave_ok = _ia(con, repo.config_do_tema(tema))
    config = repo.config_do_tema(tema)
    return pagina(request, "tema.html", "temas", tema=tema, categorias=cats, config=config,
                  efetiva=config_efetiva(config), assets=_listar_assets(tema_id), roteiros=roteiros,
                  correcoes=correcoes, pendente=pendente, custos=custos, render=render, video=video,
                  hoje=time.strftime("%Y-%m-%d"), tem_chave=chave_ok, esc=esc, **_modelos_ctx())


# ---------------------------------------------------------------- custos

@app.post("/temas/{tema_id}/custos")
async def custo_adicionar(request: Request, tema_id: int):
    form = await request.form()
    try:
        valor = float(str(form.get("valor", "")).replace(".", "").replace(",", ".")
                      if "," in str(form.get("valor", "")) else form.get("valor", ""))
    except ValueError:
        return redirecionar(f"/temas/{tema_id}#custos", erro="Valor inválido.")
    with conexao() as con:
        cst.adicionar(con, tema_id, form.get("categoria", "outro"), form.get("descricao", ""), valor,
                      form.get("moeda", "BRL"), form.get("data") or None)
    return redirecionar(f"/temas/{tema_id}", msg="Custo lançado.")


@app.post("/custos/{custo_id}/remover")
def custo_remover(custo_id: int):
    with conexao() as con:
        r = con.execute("SELECT tema_id FROM custo WHERE id = ?", (custo_id,)).fetchone()
        cst.remover(con, custo_id)
    return redirecionar(f"/temas/{r['tema_id']}" if r else "/temas", msg="Custo removido.")


@app.post("/ajustes/cotacao")
async def ajuste_cotacao(request: Request):
    form = await request.form()
    volta = form.get("voltar") or "/agenda"
    try:
        valor = float(str(form.get("cotacao", "")).replace(",", "."))
        assert valor > 0
    except (ValueError, AssertionError):
        return redirecionar(volta, erro="Cotação inválida.")
    with conexao() as con:
        cst.definir_cotacao(con, valor)
    return redirecionar(volta, msg=f"Cotação do dólar: R$ {valor:.2f}".replace(".", ","))


# ---------------------------------------------------------------- importar roteiro, render e vídeo

@app.post("/temas/{tema_id}/importar-roteiro")
async def roteiro_importar(tema_id: int, conteudo: str = Form(""), arquivo: UploadFile | None = None):
    from pydantic import ValidationError

    from app.roteirista.validacao import validar
    from motor.roteiro import Roteiro

    if arquivo and arquivo.filename:
        conteudo = (await arquivo.read()).decode("utf-8-sig")
    try:
        dados = json.loads(conteudo)
        Roteiro.model_validate(dados)
    except (json.JSONDecodeError, ValidationError) as e:
        return redirecionar(f"/temas/{tema_id}", erro=f"Roteiro inválido: {str(e)[:300]}")
    with conexao() as con:
        tema = repo.obter(con, tema_id)
        config = config_efetiva(repo.config_do_tema(tema))
        val = validar(dados, config["duracao_alvo_s"])
        rid = prod.salvar_roteiro(con, tema_id, dados, "importado", instrucao="importado (JSON)", validacao=val)
        v = prod.obter_roteiro(con, rid)["versao"]
        if tema["status"] in ("ideia", "em_roteiro", "descartado"):
            con.execute("UPDATE tema SET status = 'roteiro_pronto' WHERE id = ?", (tema_id,))
    return redirecionar(f"/temas/{tema_id}/roteiro?v={v}", msg=f"Roteiro importado como versão {v}.")


@app.post("/roteiros/{roteiro_id}/renderizar")
def roteiro_renderizar(roteiro_id: int):
    with conexao() as con:
        r = prod.obter_roteiro(con, roteiro_id)
        if not r["aprovado_em"]:
            return redirecionar(f"/temas/{r['tema_id']}/roteiro?v={r['versao']}",
                                erro="Aprove o roteiro antes de renderizar.")
        if prod.trabalho_pendente(con, "render", r["tema_id"]):
            return redirecionar(f"/temas/{r['tema_id']}/video", erro="Já existe um render na fila.")
        tema = repo.obter(con, r["tema_id"])
        prod.criar_render(con, roteiro_id, config_efetiva(repo.config_do_tema(tema)))
    return redirecionar(f"/temas/{r['tema_id']}/video", msg="Render na fila.")


def _ctx_video(con, tema_id: int) -> dict:
    tema = repo.obter(con, tema_id)
    lista = prod.renders(con, tema_id)
    aprovado = con.execute("SELECT * FROM roteiro WHERE tema_id = ? AND aprovado_em IS NOT NULL"
                           " ORDER BY versao DESC LIMIT 1", (tema_id,)).fetchone()
    video = con.execute("SELECT * FROM video WHERE tema_id = ?", (tema_id,)).fetchone()
    trab = prod.trabalho_pendente(con, "render", tema_id)
    return dict(tema=tema, renders=lista, atual=lista[0] if lista else None, aprovado=aprovado, video=video,
                pendente=trab, efetiva=config_efetiva(repo.config_do_tema(tema)),
                custos=cst.resumo(con, tema_id))


@app.get("/temas/{tema_id}/video")
def video_pagina(request: Request, tema_id: int):
    with conexao() as con:
        ctx = _ctx_video(con, tema_id)
    if not ctx["tema"]:
        return redirecionar("/producao", erro="Tema não encontrado.")
    return pagina(request, "video.html", "producao", **ctx)


@app.get("/temas/{tema_id}/video/estado")
def video_estado(request: Request, tema_id: int):
    with conexao() as con:
        ctx = _ctx_video(con, tema_id)
    return templates.TemplateResponse(request, "_render.html", ctx)


@app.post("/temas/{tema_id}/ajustar-voz")
async def video_ajustar_voz(request: Request, tema_id: int):
    """Muda voz/velocidade do tema e re-renderiza o roteiro aprovado."""
    form = await request.form()
    with conexao() as con:
        tema = repo.obter(con, tema_id)
        config = repo.config_do_tema(tema)
        if form.get("voz") in VOZES:
            config["voz"] = form["voz"]
        try:
            config["velocidade"] = min(1.6, max(0.8, float(form.get("velocidade", "").replace(",", "."))))
        except ValueError:
            pass
        repo.atualizar(con, tema_id, dict(tema), config)
        aprovado = con.execute("SELECT id FROM roteiro WHERE tema_id = ? AND aprovado_em IS NOT NULL"
                               " ORDER BY versao DESC LIMIT 1", (tema_id,)).fetchone()
        if not aprovado:
            return redirecionar(f"/temas/{tema_id}/video", erro="Não há roteiro aprovado.")
        if prod.trabalho_pendente(con, "render", tema_id):
            return redirecionar(f"/temas/{tema_id}/video", erro="Já existe um render na fila.")
        prod.criar_render(con, aprovado["id"], config_efetiva(repo.config_do_tema(repo.obter(con, tema_id))))
    return redirecionar(f"/temas/{tema_id}/video", msg="Voz ajustada; novo render na fila.")


@app.post("/renders/{render_id}/aprovar")
def render_aprovar(render_id: int):
    with conexao() as con:
        rd = con.execute("SELECT render.*, roteiro.tema_id FROM render JOIN roteiro ON roteiro.id = render.roteiro_id"
                         " WHERE render.id = ?", (render_id,)).fetchone()
        if not rd or rd["status"] != "ok":
            return redirecionar("/producao", erro="Esse render não terminou com sucesso.")
        prod.aprovar_video(con, render_id)
    return redirecionar(f"/temas/{rd['tema_id']}/video", msg="Vídeo aprovado e adicionado à biblioteca (aba Agenda).")


@app.post("/temas/{tema_id}")
async def tema_salvar(request: Request, tema_id: int):
    form = await request.form()
    config = {
        "voz": form.get("voz", ""),
        "velocidade": float(form["velocidade"]) if form.get("velocidade") else "",
        "duracao_alvo_s": int(form["duracao_alvo_s"]) if form.get("duracao_alvo_s") else "",
        "tom": form.get("tom", ""),
        "instrucoes": form.get("instrucoes", "").strip(),
        "modelo": form.get("modelo", ""),
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


# ---------------------------------------------------------------- IA (conexão e modelo)

def _ia(con, config_tema: dict | None = None):
    """(escolha, chave_ok) para o modelo que será usado."""
    from app.roteirista import provedores as pv
    esc = pv.escolha(con, config_tema)
    return esc, bool(os.environ.get(pv.PROVEDORES[esc.provedor]["env"]))


@app.get("/ia")
def ia_pagina(request: Request):
    from app.roteirista import provedores as pv
    from app.roteirista.conexao import mascarar

    with conexao() as con:
        esc, _ = _ia(con)
        testes = {p: json.loads(pv.ajuste(con, f"ia_teste_{p}", "null") or "null") for p in pv.PROVEDORES}
        creditos = {p: json.loads(pv.ajuste(con, f"ia_credito_{p}", "null") or "null") for p in pv.PROVEDORES}
        gasto_credito = {p: (pv.gasto_desde(con, p, c["data"]) if c else 0) for p, c in creditos.items()}
        gastos = pv.gasto_por_modelo(con)
        modelos = [pv.precos(con, m.id) for m in pv.MODELOS]
        temas_pers = con.execute("SELECT id, titulo, config_json FROM tema WHERE config_json LIKE '%\"modelo\"%'").fetchall()
        cot = cst.cotacao(con)
    provs = {}
    for p, info in pv.PROVEDORES.items():
        chave = os.environ.get(info["env"])
        c = creditos[p]
        restante = round(c["valor"] - gasto_credito[p], 4) if c else None
        provs[p] = info | {"mascara": mascarar(chave), "tem": bool(chave), "teste": testes[p], "credito": c,
                           "gasto_credito": gasto_credito[p], "restante": restante}
    linhas = []
    for m in modelos:
        est = pv.estimativa(m, esc.esforco)
        rest = provs[m.provedor]["restante"]
        teste = provs[m.provedor]["teste"]
        disponivel = None if not (teste and teste.get("ok")) else (m.id in teste.get("modelos", []))
        linhas.append({"m": m, "est": est, "qtd": int(rest // est) if rest is not None and est > 0 else None,
                       "disp": disponivel, "gasto": gastos.get(m.id)})
    pers = [(t, json.loads(t["config_json"]).get("modelo")) for t in temas_pers]
    return pagina(request, "ia.html", "ia", esc=esc, provs=provs, linhas=linhas, esforcos=pv.ESFORCOS,
                  uso_tipico=pv.USO_TIPICO, preco_busca=pv.PRECO_BUSCA, gastos=gastos, pers=pers, cotacao=cot,
                  outros_modelos=[g for g in gastos if g not in pv.POR_ID])


@app.post("/ia/chave/{provedor}")
async def ia_chave(request: Request, provedor: str):
    from app.roteirista.conexao import salvar_no_env
    from app.roteirista.provedores import PROVEDORES

    form = await request.form()
    if provedor not in PROVEDORES:
        return redirecionar("/ia", erro="Provedor desconhecido.")
    valor = (form.get("chave") or "").strip()
    if form.get("remover"):
        valor = ""
    elif not valor:
        return redirecionar("/ia", erro="Cole a chave antes de salvar.")
    elif any(c.isspace() for c in valor):
        return redirecionar("/ia", erro="A chave não pode ter espaços.")
    salvar_no_env(PROVEDORES[provedor]["env"], valor)
    with conexao() as con:
        con.execute("DELETE FROM ajuste WHERE chave = ?", (f"ia_teste_{provedor}",))
    nome = PROVEDORES[provedor]["nome"]
    return redirecionar("/ia", msg=f"Chave de {nome} {'removida' if not valor else 'salva no .env'}."
                        + ("" if not valor else " Use “Testar conexão”."))


@app.post("/ia/testar/{provedor}")
def ia_testar(provedor: str):
    from app.roteirista import provedores as pv
    from app.roteirista.conexao import testar

    if provedor not in pv.PROVEDORES:
        return redirecionar("/ia", erro="Provedor desconhecido.")
    res = testar(provedor) | {"quando": time.strftime("%d/%m/%Y %H:%M")}
    with conexao() as con:
        pv.definir(con, f"ia_teste_{provedor}", json.dumps(res))
    return redirecionar("/ia", **({"msg": res["mensagem"]} if res["ok"] else {"erro": res["mensagem"]}))


@app.post("/ia/modelo")
async def ia_modelo(request: Request):
    from app.roteirista import provedores as pv

    form = await request.form()
    modelo = form.get("modelo", "")
    if modelo not in pv.POR_ID:
        return redirecionar("/ia", erro="Modelo desconhecido.")
    with conexao() as con:
        pv.definir(con, "ia_modelo", modelo)
        pv.definir(con, "ia_provedor", pv.POR_ID[modelo].provedor)
        if form.get("esforco") in pv.ESFORCOS:
            pv.definir(con, "ia_esforco", form["esforco"])
        for campo, lim in (("ia_max_buscas", 30), ("ia_max_paginas", 30)):
            try:
                pv.definir(con, campo, str(min(lim, max(1, int(form.get(campo, ""))))))
            except ValueError:
                pass
    return redirecionar("/ia", msg=f"Modelo padrão: {pv.POR_ID[modelo].nome}.")


@app.post("/ia/credito/{provedor}")
async def ia_credito(request: Request, provedor: str):
    from app.roteirista import provedores as pv

    form = await request.form()
    with conexao() as con:
        if form.get("remover"):
            con.execute("DELETE FROM ajuste WHERE chave = ?", (f"ia_credito_{provedor}",))
            return redirecionar("/ia", msg="Crédito removido.")
        try:
            valor = float(str(form.get("valor", "")).replace(",", "."))
        except ValueError:
            return redirecionar("/ia", erro="Valor inválido.")
        data = form.get("data") or time.strftime("%Y-%m-%d")
        pv.definir(con, f"ia_credito_{provedor}", json.dumps({"valor": valor, "data": data}))
    return redirecionar("/ia", msg="Crédito registrado.")


# ---------------------------------------------------------------- Produção e Agenda

def _ctx_producao(con) -> dict:
    revisar = con.execute(
        "SELECT tema.*, (SELECT max(versao) FROM roteiro WHERE roteiro.tema_id = tema.id) AS versao"
        " FROM tema WHERE status IN ('roteiro_pronto', 'roteiro_aprovado', 'renderizando', 'pronto_para_revisao') ORDER BY atualizado_em DESC"
    ).fetchall()
    return dict(fila=prod.fila(con), revisar=revisar)


@app.get("/producao")
def producao(request: Request):
    with conexao() as con:
        ctx = _ctx_producao(con)
        esc, ok = _ia(con)
    return pagina(request, "producao.html", "producao", tem_chave=ok, esc=esc, **ctx)


@app.get("/producao/fila")
def producao_fila(request: Request):
    with conexao() as con:
        ctx = _ctx_producao(con)
    return templates.TemplateResponse(request, "_fila.html", ctx)


@app.post("/temas/{tema_id}/gerar")
def tema_gerar(tema_id: int):
    with conexao() as con:
        if prod.trabalho_pendente(con, "roteiro", tema_id):
            return redirecionar(f"/temas/{tema_id}", erro="Já existe uma geração de roteiro na fila.")
        prod.criar_trabalho(con, "roteiro", tema_id)
        con.execute("UPDATE tema SET status = 'em_roteiro', atualizado_em = datetime('now') WHERE id = ?",
                    (tema_id,))
    return redirecionar("/producao", msg="Roteiro na fila de produção.")


@app.post("/trabalhos/{trabalho_id}/repetir")
def trabalho_repetir(trabalho_id: int):
    with conexao() as con:
        con.execute("UPDATE trabalho SET status = 'na_fila', erro = NULL, log = log || '--- nova tentativa\n',"
                    " atualizado_em = datetime('now') WHERE id = ? AND status = 'erro'", (trabalho_id,))
    return redirecionar("/producao", msg="Trabalho de volta na fila.")


@app.post("/trabalhos/{trabalho_id}/cancelar")
def trabalho_cancelar(trabalho_id: int):
    with conexao() as con:
        t = con.execute("SELECT * FROM trabalho WHERE id = ?", (trabalho_id,)).fetchone()
        con.execute("UPDATE trabalho SET status = 'cancelado', atualizado_em = datetime('now')"
                    " WHERE id = ? AND status IN ('na_fila', 'erro')", (trabalho_id,))
        if t and t["tipo"] == "roteiro":
            tem = prod.ultimo_roteiro(con, t["referencia_id"])
            con.execute("UPDATE tema SET status = ? WHERE id = ? AND status = 'em_roteiro'",
                        ("roteiro_pronto" if tem else "ideia", t["referencia_id"]))
    return redirecionar("/producao", msg="Trabalho cancelado.")


# ---------------------------------------------------------------- revisão do roteiro

@app.get("/temas/{tema_id}/roteiro")
def roteiro_revisao(request: Request, tema_id: int, v: int | None = None):
    from app.roteirista.prompt import PALAVRAS_POR_SEGUNDO

    with conexao() as con:
        tema = repo.obter(con, tema_id)
        if not tema:
            return redirecionar("/producao", erro="Tema não encontrado.")
        if v:
            r = con.execute("SELECT * FROM roteiro WHERE tema_id = ? AND versao = ?", (tema_id, v)).fetchone()
        else:
            r = prod.ultimo_roteiro(con, tema_id)
        if not r:
            return redirecionar(f"/temas/{tema_id}", erro="Este tema ainda não tem roteiro.")
        lista = prod.versoes(con, tema_id)
        correcoes = con.execute("SELECT * FROM correcao WHERE tema_id = ? ORDER BY id DESC", (tema_id,)).fetchall()
        pendente = prod.trabalho_pendente(con, "roteiro", tema_id)
    config = config_efetiva(repo.config_do_tema(tema))
    dados = json.loads(r["json"])
    val = json.loads(r["validacao_json"] or "{}")
    por_trecho: dict[int, list] = {}
    gerais = []
    for p in val.get("problemas", []):
        (por_trecho.setdefault(p["trecho"], []) if p.get("trecho") is not None else gerais).append(p)
    fontes = {f["id"]: f for f in dados.get("fontes", [])}
    return pagina(request, "roteiro.html", "producao", tema=tema, r=r, dados=dados, val=val, previa=_previa(r),
                  por_trecho=por_trecho, gerais=gerais, fontes=fontes,
                  pesquisa=json.loads(r["pesquisa_json"] or "{}"), versoes=lista, correcoes=correcoes,
                  pendente=pendente, config=config, pps=PALAVRAS_POR_SEGUNDO * config["velocidade"] / 1.2,
                  ultima=lista[0]["id"] == r["id"],
                  cenas_json=[json.dumps(t["cena"], ensure_ascii=False, indent=1) for t in dados["trechos"]])


def _previa(r) -> dict:
    p = json.loads(r["previa_json"] or "{}")
    p.setdefault("status", "")
    p["por_trecho"] = {t["indice"]: t for t in p.get("trechos", [])}
    p["n_erros"] = sum(1 for t in p.get("trechos", []) for a in t["avisos"] if a["nivel"] == "erro")
    p["n_avisos"] = sum(1 for t in p.get("trechos", []) for a in t["avisos"] if a["nivel"] != "info") + \
        len(p.get("gerais", []))
    return p


@app.get("/roteiros/{roteiro_id}/previa-estado")
def roteiro_previa_estado(request: Request, roteiro_id: int):
    with conexao() as con:
        r = prod.obter_roteiro(con, roteiro_id)
    dados = json.loads(r["json"])
    return templates.TemplateResponse(request, "_previa_oob.html", {"r": r, "previa": _previa(r), "dados": dados})


@app.post("/roteiros/{roteiro_id}/previa")
def roteiro_previa_refazer(roteiro_id: int):
    with conexao() as con:
        r = prod.obter_roteiro(con, roteiro_id)
        prod.enfileirar_previa(con, r["tema_id"], roteiro_id)
    return redirecionar(f"/temas/{r['tema_id']}/roteiro?v={r['versao']}", msg="Prévia na fila.")


@app.post("/roteiros/{roteiro_id}/salvar")
async def roteiro_salvar(request: Request, roteiro_id: int):
    from app.roteirista.validacao import validar

    form = await request.form()
    with conexao() as con:
        base = prod.obter_roteiro(con, roteiro_id)
        tema = repo.obter(con, base["tema_id"])
        dados = json.loads(base["json"])
        try:
            for i, tr in enumerate(dados["trechos"]):
                tr["fala"] = form.get(f"fala_{i}", tr["fala"]).strip()
                tr["titulo_tela"] = [l.strip() for l in form.get(f"titulo_{i}", "").splitlines() if l.strip()][:3]
                if f"cena_{i}" in form:
                    tr["cena"] = json.loads(form[f"cena_{i}"])
                tr["fonte_id"] = form.get(f"fonte_{i}") or None
        except json.JSONDecodeError as e:
            return redirecionar(f"/temas/{tema['id']}/roteiro?v={base['versao']}",
                                erro=f"JSON da cena inválido: {e}")
        config = config_efetiva(repo.config_do_tema(tema))
        pesq = json.loads(base["pesquisa_json"] or "{}")
        val = validar(dados, config["duracao_alvo_s"], pesq.get("urls_abertas"),
                      json.loads(base["validacao_json"] or "{}").get("urls", {}))
        rid = prod.salvar_roteiro(con, tema["id"], dados, "edicao", base["modelo"],
                                  instrucao="edição manual", pesquisa=pesq, validacao=val)
        v = prod.obter_roteiro(con, rid)["versao"]
        if form.get("depois") == "renderizar":
            # ajuste rápido: aprova esta versão e re-renderiza
            con.execute("UPDATE roteiro SET aprovado_em = NULL WHERE tema_id = ?", (tema["id"],))
            con.execute("UPDATE roteiro SET aprovado_em = datetime('now') WHERE id = ?", (rid,))
            if not prod.trabalho_pendente(con, "render", tema["id"]):
                prod.criar_render(con, rid, config)
                return redirecionar(f"/temas/{tema['id']}/video", msg=f"Versão {v} aprovada; render na fila.")
    return redirecionar(f"/temas/{tema['id']}/roteiro?v={v}", msg=f"Edição salva como versão {v}.")


@app.post("/roteiros/{roteiro_id}/aprovar")
def roteiro_aprovar(roteiro_id: int):
    with conexao() as con:
        r = prod.obter_roteiro(con, roteiro_id)
        con.execute("UPDATE roteiro SET aprovado_em = NULL WHERE tema_id = ?", (r["tema_id"],))
        con.execute("UPDATE roteiro SET aprovado_em = datetime('now') WHERE id = ?", (roteiro_id,))
        con.execute("UPDATE tema SET status = 'roteiro_aprovado', atualizado_em = datetime('now') WHERE id = ?",
                    (r["tema_id"],))
    return redirecionar(f"/temas/{r['tema_id']}/roteiro?v={r['versao']}",
                        msg=f"Roteiro v{r['versao']} aprovado. Agora é só renderizar.")


@app.post("/temas/{tema_id}/corrigir")
async def tema_corrigir(request: Request, tema_id: int):
    form = await request.form()
    texto = (form.get("texto") or "").strip()
    alvo = form.get("alvo", "roteiro")
    volta = form.get("voltar") or f"/temas/{tema_id}"
    if not texto:
        return redirecionar(volta, erro="Escreva a correção.")
    with conexao() as con:
        r = prod.ultimo_roteiro(con, tema_id)
        if not r:
            return redirecionar(volta, erro="Ainda não há roteiro para corrigir.")
        if prod.trabalho_pendente(con, "roteiro", tema_id):
            return redirecionar(volta, erro="Já existe um trabalho de roteiro na fila para este tema.")
        trecho = None
        if alvo.startswith("trecho_"):
            trecho = int(alvo.split("_")[1])
            alvo = "trecho"
        if alvo == "render":
            return redirecionar(volta, erro="Correções de render chegam na Fase 5.")
        cur = con.execute("INSERT INTO correcao (tema_id, alvo, trecho_idx, texto) VALUES (?, ?, ?, ?)",
                          (tema_id, alvo, trecho, texto))
        prod.criar_trabalho(con, "roteiro", tema_id, {"correcao_id": cur.lastrowid, "roteiro_id": r["id"]})
    return redirecionar("/producao", msg="Correção enviada para a fila.")


from app.rotas_agenda import registrar_rotas  # noqa: E402

registrar_rotas(app, pagina, templates, redirecionar)


@app.get("/_dev/boot", response_class=PlainTextResponse)
def dev_boot():
    return ID_BOOT
