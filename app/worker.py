"""Worker de segundo plano: executa os trabalhos da fila (SQLite), um por vez.

Tipos já implementados: roteiro. Próximas fases: render, publicação, gerar_temas e a
verificação, a cada minuto, das publicações vencidas.
"""

import logging
import time

from app.ambiente import carregar_env
from app.db import conexao, migrar
from app.roteirista.conexao import sincronizar_do_env
from app.producao import TAREFAS, finalizar, pegar_proximo, recuperar_interrompidos, registrar

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("worker")

ESPERA_S = 3            # quando a fila está vazia
AVISO_VAZIA_S = 60      # log "fila vazia" a cada minuto


def executar(con, t) -> None:
    tarefa = TAREFAS.get(t["tipo"])
    if tarefa is None:
        finalizar(con, t["id"], f"tipo de trabalho ainda não implementado: {t['tipo']}")
        return
    sincronizar_do_env()   # chaves salvas pela tela IA valem sem reiniciar
    log.info("trabalho %d (%s, ref %s) começou", t["id"], t["tipo"], t["referencia_id"])
    try:
        tarefa(con, t)
        finalizar(con, t["id"])
        log.info("trabalho %d terminou", t["id"])
    except Exception as e:   # erro legível no painel
        registrar(con, t["id"], f"ERRO: {e}")
        finalizar(con, t["id"], str(e))
        log.exception("trabalho %d falhou", t["id"])


def main() -> None:
    carregar_env()
    migrar()
    with conexao() as con:
        n = recuperar_interrompidos(con)
    log.info("worker iniciado%s", f" ({n} trabalho(s) interrompido(s) voltaram para a fila)" if n else "")
    ultimo_aviso = 0.0
    while True:
        with conexao() as con:
            t = pegar_proximo(con)
            if t:
                executar(con, t)
                continue
        if time.time() - ultimo_aviso > AVISO_VAZIA_S:
            log.info("fila vazia")
            ultimo_aviso = time.time()
        time.sleep(ESPERA_S)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
