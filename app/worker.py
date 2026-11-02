"""Worker de segundo plano.

Fase 2: só informa quantos trabalhos estão na fila. Nas próximas fases vai ler a tabela `trabalho`
do SQLite (roteiro, narração, render, publicação), executar um por vez e, a cada
minuto, verificar publicações vencidas.
"""

import logging
import time

from app.db import conexao, migrar

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("worker")

INTERVALO_S = 60


def main() -> None:
    migrar()
    log.info("worker iniciado")
    while True:
        with conexao() as con:
            n = con.execute("SELECT count(*) FROM trabalho WHERE status = 'na_fila'").fetchone()[0]
        if n:
            log.info("%d trabalho(s) na fila; a execução chega na Fase 4", n)
        else:
            log.info("fila vazia")
        time.sleep(INTERVALO_S)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
