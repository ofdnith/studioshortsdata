"""Acesso ao SQLite (data/estudio.db) e migrações simples.

Migrações: arquivos `app/migracoes/NNN_nome.sql`, aplicados em ordem. O número da
última aplicada fica em `PRAGMA user_version`.
"""

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CAMINHO_DB = RAIZ / "data" / "estudio.db"
PASTA_MIGRACOES = Path(__file__).parent / "migracoes"

log = logging.getLogger("db")


def conectar() -> sqlite3.Connection:
    CAMINHO_DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(CAMINHO_DB, timeout=10, isolation_level=None)  # autocommit
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode = WAL")  # servidor e worker ao mesmo tempo
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA busy_timeout = 10000")
    return con


@contextmanager
def conexao():
    con = conectar()
    try:
        yield con
    finally:
        con.close()


@contextmanager
def transacao(con: sqlite3.Connection):
    con.execute("BEGIN IMMEDIATE")
    try:
        yield con
    except BaseException:
        con.execute("ROLLBACK")
        raise
    con.execute("COMMIT")


def migrar() -> None:
    with conexao() as con:
        atual = con.execute("PRAGMA user_version").fetchone()[0]
        for arquivo in sorted(PASTA_MIGRACOES.glob("*.sql")):
            numero = int(arquivo.name.split("_", 1)[0])
            if numero <= atual:
                continue
            log.info("aplicando migração %s", arquivo.name)
            with transacao(con):
                for comando in arquivo.read_text().split(";"):
                    if comando.strip():
                        con.execute(comando)
                con.execute(f"PRAGMA user_version = {numero}")
