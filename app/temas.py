"""Operações sobre temas no banco."""

import csv
import io
import json
import sqlite3
from dataclasses import dataclass

from app.config import CONFIG_PADRAO, PRIORIDADES, STATUS_TEMA
from app.db import transacao

ORDEM = """
    ORDER BY CASE status WHEN 'descartado' THEN 1 ELSE 0 END,
             CASE prioridade WHEN 'alta' THEN 0 WHEN 'media' THEN 1 ELSE 2 END,
             id
"""


@dataclass
class Filtros:
    q: str = ""
    categoria: str = ""
    prioridade: str = ""
    status: str = ""


def listar(con: sqlite3.Connection, f: Filtros) -> list[sqlite3.Row]:
    sql, args = "SELECT * FROM tema WHERE 1=1", []
    if f.q.strip():
        sql += " AND (titulo LIKE ? OR gancho LIKE ? OR notas LIKE ?)"
        args += [f"%{f.q.strip()}%"] * 3
    for campo in ("categoria", "prioridade", "status"):
        valor = getattr(f, campo)
        if valor:
            sql += f" AND {campo} = ?"
            args.append(valor)
    return con.execute(sql + ORDEM, args).fetchall()


def contar_por_status(con: sqlite3.Connection) -> dict[str, int]:
    return dict(con.execute("SELECT status, count(*) FROM tema GROUP BY status").fetchall())


def categorias(con: sqlite3.Connection) -> list[str]:
    return [r[0] for r in con.execute(
        "SELECT DISTINCT categoria FROM tema WHERE categoria != '' ORDER BY categoria")]


def obter(con: sqlite3.Connection, tema_id: int) -> sqlite3.Row | None:
    return con.execute("SELECT * FROM tema WHERE id = ?", (tema_id,)).fetchone()


def config_do_tema(tema: sqlite3.Row) -> dict:
    return json.loads(tema["config_json"] or "{}")


def _normalizar(dados: dict) -> dict:
    prioridade = (dados.get("prioridade") or "media").strip().lower().replace("é", "e")
    status = (dados.get("status") or "ideia").strip().lower()
    return {
        "titulo": (dados.get("titulo") or "").strip(),
        "categoria": (dados.get("categoria") or "").strip(),
        "gancho": (dados.get("gancho") or "").strip(),
        "notas": (dados.get("notas") or "").strip(),
        "prioridade": prioridade if prioridade in PRIORIDADES else "media",
        "status": status if status in STATUS_TEMA else "ideia",
    }


def criar(con: sqlite3.Connection, dados: dict) -> int:
    d = _normalizar(dados)
    if not d["titulo"]:
        raise ValueError("O título é obrigatório.")
    try:
        cur = con.execute(
            "INSERT INTO tema (titulo, categoria, gancho, notas, prioridade, status)"
            " VALUES (:titulo, :categoria, :gancho, :notas, :prioridade, :status)", d)
    except sqlite3.IntegrityError:
        raise ValueError(f"Já existe um tema com o título “{d['titulo']}”.") from None
    return cur.lastrowid


def atualizar(con: sqlite3.Connection, tema_id: int, dados: dict, config: dict) -> None:
    d = _normalizar(dados)
    if not d["titulo"]:
        raise ValueError("O título é obrigatório.")
    # Guarda só o que difere do padrão: mudar o padrão depois afeta quem não personalizou.
    so_diferente = {k: v for k, v in config.items()
                    if v not in (None, "") and v != CONFIG_PADRAO.get(k)}
    try:
        con.execute(
            "UPDATE tema SET titulo=:titulo, categoria=:categoria, gancho=:gancho, notas=:notas,"
            " prioridade=:prioridade, status=:status, config_json=:config,"
            " atualizado_em=datetime('now') WHERE id=:id",
            {**d, "config": json.dumps(so_diferente, ensure_ascii=False), "id": tema_id})
    except sqlite3.IntegrityError:
        raise ValueError(f"Já existe um tema com o título “{d['titulo']}”.") from None


def mudar_status(con: sqlite3.Connection, ids: list[int], status: str) -> int:
    if status not in STATUS_TEMA or not ids:
        return 0
    marcas = ",".join("?" * len(ids))
    cur = con.execute(
        f"UPDATE tema SET status=?, atualizado_em=datetime('now') WHERE id IN ({marcas})",
        [status, *ids])
    return cur.rowcount


def enviar_para_producao(con: sqlite3.Connection, ids: list[int]) -> tuple[int, int]:
    """Cria um trabalho de roteiro para cada tema em 'ideia'. Devolve (enviados, ignorados)."""
    enviados = 0
    with transacao(con):
        for tema_id in ids:
            cur = con.execute(
                "UPDATE tema SET status='em_roteiro', atualizado_em=datetime('now')"
                " WHERE id=? AND status='ideia'", (tema_id,))
            if cur.rowcount:
                con.execute("INSERT INTO trabalho (tipo, referencia_id) VALUES ('roteiro', ?)",
                            (tema_id,))
                enviados += 1
    return enviados, len(ids) - enviados


def importar_csv(con: sqlite3.Connection, conteudo: str) -> tuple[int, int]:
    """Importa linhas com colunas titulo,categoria,gancho,prioridade,status.

    Títulos repetidos (já no banco) são ignorados. Devolve (importados, ignorados).
    """
    leitor = csv.DictReader(io.StringIO(conteudo.lstrip("﻿")))
    if not leitor.fieldnames or "titulo" not in leitor.fieldnames:
        raise ValueError("O CSV precisa ter uma coluna “titulo”.")
    importados = ignorados = 0
    with transacao(con):
        for linha in leitor:
            d = _normalizar(linha)
            if not d["titulo"]:
                ignorados += 1
                continue
            cur = con.execute(
                "INSERT OR IGNORE INTO tema (titulo, categoria, gancho, notas, prioridade, status)"
                " VALUES (:titulo, :categoria, :gancho, :notas, :prioridade, :status)", d)
            importados += cur.rowcount
            ignorados += 1 - cur.rowcount
    return importados, ignorados
