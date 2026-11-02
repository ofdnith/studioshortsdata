"""Fila da versão simples: um vídeo por vez (pesquisa e roteiro → animação → narração e render).

Rode com `python -m lite.worker`. Com LITE_FALSO=1, pula a IA e usa o roteiro de exemplo
(exemplos/livre_sobrevivencia.json): serve para testar sem gastar crédito.
"""

import json
import os
import time
import traceback

from app.ambiente import carregar_env
from lite import db

CONFIG_VIDEO = {"duracao_alvo_s": 60, "tom": "curioso", "instrucoes": "", "velocidade": 1.2}
EXEMPLO = db.RAIZ / "exemplos" / "livre_sobrevivencia.json"


class Video:
    """Atualiza etapa, progresso e log do vídeo no banco."""

    def __init__(self, con, vid: int):
        self.con, self.id = con, vid

    def etapa(self, texto: str, progresso: int):
        self.con.execute("UPDATE video SET etapa = ?, progresso = ?, atualizado_em = datetime('now') WHERE id = ?",
                         (texto, progresso, self.id))
        self.log(f"== {texto}")

    def progresso(self, p: int):
        self.con.execute("UPDATE video SET progresso = ? WHERE id = ?", (p, self.id))

    def log(self, m: str):
        print(f"[vídeo {self.id}] {m}", flush=True)
        self.con.execute("UPDATE video SET log = log || ? WHERE id = ?", (time.strftime("%H:%M:%S ") + m + "\n", self.id))

    def custo(self, valor: float):
        self.con.execute("UPDATE video SET custo = ? WHERE id = ?", (round(valor, 4), self.id))


def escolha(con):
    from app.roteirista import provedores as pv
    modelo = db.ajuste(con, "modelo")
    return pv.Escolha("openai", modelo, "medium", 1, 1, "versão simples", "livre"), pv.precos(None, modelo)


def roteiro_com_ia(con, v: Video, tema: str) -> dict:
    from app.roteirista import openai_gerador
    from app.roteirista.diretor import gerar_codigo
    from app.roteirista.esquema import para_motor
    from app.roteirista.prompt import mensagem_tema
    from motor.layout import LAYOUT_ATUAL

    esc, preco = escolha(con)
    v.etapa("Pesquisando e escrevendo o roteiro", 5)
    msg = mensagem_tema({"titulo": tema, "categoria": "", "gancho": "", "notas": ""}, CONFIG_VIDEO)
    res = openai_gerador.gerar(msg, log=v.log, escolha=esc, preco=preco)
    v.custo(res.uso.custo)
    roteiro, _ = para_motor(res.roteiro)
    roteiro["layout"] = LAYOUT_ATUAL

    v.etapa("Desenhando a animação", 30)
    codigo, uso_d, _ = gerar_codigo(roteiro, esc, preco, log=v.log)
    roteiro["codigo"] = codigo
    v.custo(res.uso.custo + uso_d.custo)
    return roteiro


def roteiro_falso(v: Video) -> dict:
    v.etapa("Modo de teste: usando o roteiro de exemplo (sem IA)", 30)
    return json.loads(EXEMPLO.read_text(encoding="utf-8"))


def produzir(con, linha):
    from app.producao import _rodar_livre_na_caixa

    v = Video(con, linha["id"])
    pasta = db.pasta_video(linha["id"])
    roteiro = roteiro_falso(v) if os.environ.get("LITE_FALSO") == "1" else roteiro_com_ia(con, v, linha["tema"])
    (pasta).mkdir(parents=True, exist_ok=True)
    con.execute("UPDATE video SET titulo = ? WHERE id = ?", (roteiro.get("titulo_capa", "").replace("*", ""), v.id))

    v.etapa("Narrando e renderizando o vídeo", 50)
    _rodar_livre_na_caixa(roteiro, pasta, ["render", "--saida", str(pasta / "video.mp4"), "--voz", linha["voz"],
                                           "--velocidade", str(CONFIG_VIDEO["velocidade"]), "--trilha", "ambiente"],
                          v.log, lambda f: v.progresso(50 + int(f * 49)))
    cron = json.loads((pasta / "video_trabalho" / "cronograma.json").read_text())
    for p in (pasta / "video_trabalho").glob("*"):   # só ficam o MP4 e a capa
        if p.is_file():
            p.unlink()
    con.execute("UPDATE video SET status = 'ok', progresso = 100, etapa = 'Pronto', duracao_s = ?,"
                " atualizado_em = datetime('now') WHERE id = ?", (cron["total"], v.id))
    v.log("pronto")


def proximo(con):
    con.execute("BEGIN IMMEDIATE")
    r = con.execute("SELECT * FROM video WHERE status = 'na_fila' ORDER BY id LIMIT 1").fetchone()
    if r:
        con.execute("UPDATE video SET status = 'rodando', atualizado_em = datetime('now') WHERE id = ?", (r["id"],))
    con.execute("COMMIT")
    return r


def main():
    carregar_env()
    db.migrar()
    with db.conexao() as con:
        # Interrompido no meio: vira erro (não repete sozinho para não cobrar a IA duas vezes).
        con.execute("UPDATE video SET status = 'erro', erro = 'Interrompido: o servidor reiniciou. Tente de novo.'"
                    " WHERE status = 'rodando'")
    print("fila da versão simples rodando" + (" (modo de teste, sem IA)" if os.environ.get("LITE_FALSO") == "1" else ""),
          flush=True)
    while True:
        with db.conexao() as con:
            linha = proximo(con)
            if linha is None:
                time.sleep(2)
                continue
            try:
                produzir(con, linha)
            except Exception as e:
                traceback.print_exc()
                Video(con, linha["id"]).log(f"erro: {e}")
                con.execute("UPDATE video SET status = 'erro', erro = ?, atualizado_em = datetime('now') WHERE id = ?",
                            (str(e)[:500], linha["id"]))


if __name__ == "__main__":
    main()
