"""Roteiros (versões), fila de trabalhos e a tarefa de gerar/corrigir roteiro."""

import json
import sqlite3
from datetime import datetime

from app import temas as repo_temas
from app.config import config_efetiva
from app.db import transacao

# ---------------------------------------------------------------- roteiros


def obter_roteiro(con, roteiro_id: int):
    return con.execute("SELECT * FROM roteiro WHERE id = ?", (roteiro_id,)).fetchone()


def ultimo_roteiro(con, tema_id: int):
    return con.execute("SELECT * FROM roteiro WHERE tema_id = ? ORDER BY versao DESC LIMIT 1",
                       (tema_id,)).fetchone()


def versoes(con, tema_id: int):
    return con.execute("SELECT id, versao, origem, modelo, custo_estimado, criado_em, aprovado_em, instrucao "
                       "FROM roteiro WHERE tema_id = ? ORDER BY versao DESC", (tema_id,)).fetchall()


def salvar_roteiro(con, tema_id: int, roteiro: dict, origem: str, modelo: str = "", uso=None,
                   instrucao: str = "", pesquisa: dict | None = None, validacao: dict | None = None) -> int:
    with transacao(con):
        v = con.execute("SELECT coalesce(max(versao), 0) + 1 FROM roteiro WHERE tema_id = ?",
                        (tema_id,)).fetchone()[0]
        cur = con.execute(
            "INSERT INTO roteiro (tema_id, versao, json, modelo, tokens_entrada, tokens_saida, custo_estimado,"
            " tokens_cache_escrita, tokens_cache_leitura, buscas_web, origem, instrucao, pesquisa_json,"
            " validacao_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (tema_id, v, json.dumps(roteiro, ensure_ascii=False), modelo,
             uso.entrada if uso else 0, uso.saida if uso else 0, uso.custo if uso else 0,
             uso.cache_escrita if uso else 0, uso.cache_leitura if uso else 0, uso.buscas if uso else 0,
             origem, instrucao, json.dumps(pesquisa or {}, ensure_ascii=False),
             json.dumps(validacao or {}, ensure_ascii=False)))
    return cur.lastrowid


def custo_total(con, tema_id: int) -> float:
    return con.execute("SELECT coalesce(sum(custo_estimado), 0) FROM roteiro WHERE tema_id = ?",
                       (tema_id,)).fetchone()[0]


# ---------------------------------------------------------------- trabalhos

def criar_trabalho(con, tipo: str, referencia_id: int, payload: dict | None = None) -> int:
    cur = con.execute("INSERT INTO trabalho (tipo, referencia_id, payload_json) VALUES (?, ?, ?)",
                      (tipo, referencia_id, json.dumps(payload or {}, ensure_ascii=False)))
    return cur.lastrowid


def trabalho_pendente(con, tipo: str, referencia_id: int):
    return con.execute("SELECT * FROM trabalho WHERE tipo = ? AND referencia_id = ? AND status IN "
                       "('na_fila', 'rodando') ORDER BY id DESC LIMIT 1", (tipo, referencia_id)).fetchone()


def pegar_proximo(con):
    """Marca o trabalho mais antigo da fila como 'rodando' e o devolve."""
    with transacao(con):
        t = con.execute("SELECT * FROM trabalho WHERE status = 'na_fila' ORDER BY id LIMIT 1").fetchone()
        if not t:
            return None
        con.execute("UPDATE trabalho SET status = 'rodando', tentativas = tentativas + 1,"
                    " atualizado_em = datetime('now') WHERE id = ?", (t["id"],))
    return con.execute("SELECT * FROM trabalho WHERE id = ?", (t["id"],)).fetchone()


def registrar(con, trabalho_id: int, mensagem: str):
    linha = f"{datetime.now():%H:%M:%S} {mensagem}\n"
    con.execute("UPDATE trabalho SET log = log || ?, atualizado_em = datetime('now') WHERE id = ?",
                (linha, trabalho_id))


def finalizar(con, trabalho_id: int, erro: str | None = None):
    con.execute("UPDATE trabalho SET status = ?, erro = ?, atualizado_em = datetime('now') WHERE id = ?",
                ("erro" if erro else "ok", erro, trabalho_id))


def recuperar_interrompidos(con) -> int:
    """Trabalhos 'rodando' de um worker que caiu voltam para a fila."""
    return con.execute("UPDATE trabalho SET status = 'na_fila' WHERE status = 'rodando'").rowcount


def fila(con):
    return con.execute(
        "SELECT trabalho.*, tema.titulo, tema.status AS status_tema FROM trabalho"
        " LEFT JOIN tema ON tema.id = trabalho.referencia_id"
        " WHERE trabalho.status IN ('na_fila', 'rodando', 'erro')"
        "    OR trabalho.atualizado_em > datetime('now', '-10 minutes')"
        " ORDER BY trabalho.id DESC LIMIT 30").fetchall()


# ---------------------------------------------------------------- tarefa: roteiro

def _mesclar_trecho(base: dict, novo: dict, idx: int) -> dict:
    """Pega só o trecho idx do roteiro novo (mais fontes e pessoas novas)."""
    res = json.loads(json.dumps(base))
    if idx < len(novo["trechos"]) and idx < len(res["trechos"]):
        res["trechos"][idx] = novo["trechos"][idx]
    ids = {f["id"] for f in res["fontes"]}
    res["fontes"] += [f for f in novo["fontes"] if f["id"] not in ids]
    nomes = {p["nome"].lower() for p in res["pessoas"]}
    res["pessoas"] += [p for p in novo["pessoas"] if p["nome"].lower() not in nomes]
    return res


def tarefa_roteiro(con, trabalho, gerar=None):
    """Gera (ou corrige) o roteiro de um tema. `gerar` permite injetar um gerador falso em testes."""
    from app.roteirista import claude
    from app.roteirista.esquema import para_motor
    from app.roteirista.prompt import mensagem_correcao, mensagem_tema
    from app.roteirista.validacao import validar

    gerar = gerar or claude.gerar
    tema_id = trabalho["referencia_id"]
    payload = json.loads(trabalho["payload_json"] or "{}")
    tema = repo_temas.obter(con, tema_id)
    config = config_efetiva(repo_temas.config_do_tema(tema))

    def log(m):
        registrar(con, trabalho["id"], m)

    correcao = None
    base = None
    if payload.get("correcao_id"):
        correcao = con.execute("SELECT * FROM correcao WHERE id = ?", (payload["correcao_id"],)).fetchone()
        base = obter_roteiro(con, payload["roteiro_id"])
        trecho = correcao["trecho_idx"] if correcao["alvo"] == "trecho" else None
        msg = mensagem_correcao(tema, config, json.loads(base["json"]), correcao["texto"], trecho)
        log(f"correção: {correcao['texto'][:120]}")
    else:
        msg = mensagem_tema(tema, config)
        log(f"gerando roteiro com {claude.modelo()}")

    status_antes = tema["status"] if tema["status"] != "em_roteiro" else None
    con.execute("UPDATE tema SET status = 'em_roteiro', atualizado_em = datetime('now') WHERE id = ?", (tema_id,))
    try:
        res = gerar(msg, log=log)
        roteiro, notas = para_motor(res.roteiro)
        if correcao is not None and correcao["alvo"] == "trecho":
            roteiro = _mesclar_trecho(json.loads(base["json"]), roteiro, correcao["trecho_idx"])
        log("validando (formato, fontes, palavras, URLs)…")
        cache = json.loads(base["validacao_json"]).get("urls", {}) if base else {}
        val = validar(roteiro, config["duracao_alvo_s"], res.urls_abertas, cache)
        pesquisa = {"buscas": res.buscas, "urls_abertas": res.urls_abertas, "notas": notas,
                    "uso": vars(res.uso) | {"custo": res.uso.custo}}
        rid = salvar_roteiro(con, tema_id, roteiro, "correcao" if correcao else "claude", res.uso.modelo,
                             res.uso, correcao["texto"] if correcao else "", pesquisa, val)
        if correcao is not None:
            con.execute("UPDATE correcao SET status = 'aplicada', aplicada_em = datetime('now'), resultado = ?"
                        " WHERE id = ?", (f"roteiro v{obter_roteiro(con, rid)['versao']}", correcao["id"]))
        con.execute("UPDATE tema SET status = 'roteiro_pronto', atualizado_em = datetime('now') WHERE id = ?",
                    (tema_id,))
        n_erros = sum(1 for p in val["problemas"] if p["nivel"] == "erro")
        log(f"pronto: roteiro v{obter_roteiro(con, rid)['versao']} · {val['palavras']} palavras · "
            f"{n_erros} erro(s) de validação")
    except Exception as e:
        anterior = ultimo_roteiro(con, tema_id)
        volta = status_antes or ("roteiro_pronto" if anterior else "ideia")
        con.execute("UPDATE tema SET status = ?, atualizado_em = datetime('now') WHERE id = ?", (volta, tema_id))
        if correcao is not None:
            con.execute("UPDATE correcao SET status = 'erro', resultado = ? WHERE id = ?", (str(e), correcao["id"]))
        raise


TAREFAS = {"roteiro": tarefa_roteiro}
