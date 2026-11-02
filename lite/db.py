"""Banco próprio da versão simples (data/lite.db): convites, vídeos e ajustes."""

import secrets
import sqlite3
from contextlib import contextmanager
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO = RAIZ / "data" / "lite.db"
STORAGE = RAIZ / "storage" / "lite"

ESQUEMA = """
CREATE TABLE IF NOT EXISTS convite (
    codigo     TEXT PRIMARY KEY,
    nome       TEXT NOT NULL,
    limite     INTEGER NOT NULL DEFAULT 3,
    ativo      INTEGER NOT NULL DEFAULT 1,
    criado_em  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS video (
    id            INTEGER PRIMARY KEY,
    convite       TEXT NOT NULL REFERENCES convite (codigo),
    tema          TEXT NOT NULL,
    voz           TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'na_fila',   -- na_fila, rodando, ok, erro
    etapa         TEXT NOT NULL DEFAULT '',
    progresso     INTEGER NOT NULL DEFAULT 0,
    log           TEXT NOT NULL DEFAULT '',
    erro          TEXT,
    custo         REAL NOT NULL DEFAULT 0,
    titulo        TEXT,
    duracao_s     REAL,
    criado_em     TEXT NOT NULL DEFAULT (datetime('now')),
    atualizado_em TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS ajuste (
    chave TEXT PRIMARY KEY,
    valor TEXT NOT NULL
);
"""

PADROES = {"teto_usd": "5.00", "modelo": "gpt-6.1-sol", "url_publica": ""}


def conectar() -> sqlite3.Connection:
    ARQUIVO.parent.mkdir(exist_ok=True)
    con = sqlite3.connect(ARQUIVO, timeout=30, isolation_level=None)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode = WAL")
    con.execute("PRAGMA foreign_keys = ON")
    return con


@contextmanager
def conexao():
    con = conectar()
    try:
        yield con
    finally:
        con.close()


def migrar():
    with conexao() as con:
        con.executescript(ESQUEMA)
    STORAGE.mkdir(parents=True, exist_ok=True)


def ajuste(con, chave: str) -> str:
    r = con.execute("SELECT valor FROM ajuste WHERE chave = ?", (chave,)).fetchone()
    return r[0] if r else PADROES.get(chave, "")


def definir(con, chave: str, valor: str):
    con.execute("INSERT INTO ajuste (chave, valor) VALUES (?, ?) ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor",
                (chave, valor))


def novo_codigo() -> str:
    return secrets.token_urlsafe(9)


def gasto_total(con) -> float:
    return float(con.execute("SELECT coalesce(sum(custo), 0) FROM video").fetchone()[0])


def usados(con, codigo: str) -> int:
    """Vídeos que contam no limite do convite (os que falharam não contam)."""
    return con.execute("SELECT count(*) FROM video WHERE convite = ? AND status != 'erro'", (codigo,)).fetchone()[0]


def pasta_video(video_id: int) -> Path:
    return STORAGE / f"video_{video_id:04d}"
