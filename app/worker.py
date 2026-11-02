"""Worker de segundo plano.

Fase 1: só mostra que está vivo. Nas próximas fases vai ler a tabela `trabalho`
do SQLite (roteiro, narração, render, publicação), executar um por vez e, a cada
minuto, verificar publicações vencidas.
"""

import logging
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("worker")

INTERVALO_S = 60


def main() -> None:
    log.info("worker iniciado (fase 1: sem trabalhos ainda)")
    while True:
        log.info("verificando trabalhos e publicações vencidas... nada a fazer")
        time.sleep(INTERVALO_S)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
