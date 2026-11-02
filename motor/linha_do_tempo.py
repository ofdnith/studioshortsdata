"""Linha do tempo: trechos com horários e 'corridas' (trechos seguidos com a mesma cena).

Dentro de uma corrida a cena continua na tela (sem reentrar) e só anima o que muda
de um trecho para o outro (ex.: marcar o vencedor, focar um gráfico, nova coluna).
Um `texto_grande` com estilo 'carimbo' entra na corrida anterior, por cima da cena.
"""

from dataclasses import dataclass, field

from motor.narracao import Cronograma
from motor.roteiro import Roteiro

ADIANTO = 1.5    # a 1ª cena já começa adiantada: o quadro 0 (capa) precisa ter visual
FADE = 0.2


def chave_continuidade(cena) -> tuple:
    t = cena.tipo
    if t == "barras":
        return (t, tuple(d.rotulo for d in cena.dados))
    if t == "barras_pareadas":
        return (t, tuple(g.rotulo for g in cena.grupos))
    if t == "barra_empilhada":
        return (t, tuple(b.rotulo for b in cena.barras))
    if t == "grade_graficos":
        return (t, tuple(g.titulo for g in cena.graficos))
    if t == "tabela":
        return (t, tuple(l.rotulo for l in cena.linhas))
    if t == "linha":
        return (t, tuple(s.nome for s in cena.series), tuple(cena.rotulos_x))
    if t in ("histograma", "ranking", "pizza"):
        itens = cena.barras if t == "histograma" else (cena.itens if t == "ranking" else cena.fatias)
        return (t, tuple(i.rotulo for i in itens))
    if t in ("medidor", "escala"):
        return (t, cena.minimo, cena.maximo, cena.unidade)
    if t in ("bolhas", "funil"):
        return (t, tuple(i.rotulo for i in (cena.itens if t == "bolhas" else cena.etapas)))
    if t == "mapa_calor":
        return (t, tuple(cena.linhas), tuple(cena.colunas))
    if t == "inclinacao":
        return (t, cena.rotulo_antes, tuple(i.rotulo for i in cena.itens))
    if t == "arvore":
        return (t, cena.total, tuple(r.rotulo for r in cena.ramos))
    if t == "distribuicao":
        return (t, cena.forma, cena.media, cena.desvio)
    if t in ("icones", "simulacao"):
        return (t, cena.total if t == "icones" else cena.experimento)
    if t == "linha_do_tempo":
        return (t, tuple(e.ano for e in cena.eventos))
    if t == "passos":
        return (t, cena.itens[0])
    if t == "comparacao":
        return (t, cena.esquerda.titulo, cena.direita.titulo)
    if t in ("numero_grande", "objeto", "citacao"):
        return (t, id(cena))
    if t in ("pessoa", "lugar", "mapa"):
        return (t, cena.lugar if t != "pessoa" else cena.pessoa)
    if t == "texto_grande":
        return (t, id(cena))   # cada frase é uma cena nova
    return (t,)   # dispersao, diagrama_causal, chamada: continuam


def eh_carimbo(cena) -> bool:
    return cena.tipo == "texto_grande" and cena.estilo == "carimbo"


@dataclass
class TrechoTempo:
    indice: int
    cena: object
    titulo: list[str]
    fonte_id: str | None
    inicio: float
    fim: float
    prox: float          # início do próximo trecho (ou fim do vídeo)
    ilustracao: str | None = None
    enfase: bool = False


@dataclass
class Corrida:
    trechos: list[TrechoTempo]
    primeira: bool
    ini: float = 0.0     # limites da seção (onde troca de cena)
    fim: float = 0.0
    entrada: float = field(init=False)

    def __post_init__(self):
        self.entrada = self.trechos[0].inicio - (ADIANTO if self.primeira else 0.0)

    @property
    def cena_base(self):
        return self.trechos[0].cena


def novas_cenas(roteiro: Roteiro) -> list[bool]:
    """Para a narração: True onde começa uma cena nova (pausa maior)."""
    res, anterior = [], None
    for tr in roteiro.trechos:
        if eh_carimbo(tr.cena):
            res.append(False)
            continue
        ch = chave_continuidade(tr.cena)
        res.append(ch != anterior)
        anterior = ch
    return res


def montar(roteiro: Roteiro, cron: Cronograma) -> tuple[list[TrechoTempo], list[Corrida]]:
    tts = []
    for i, (tr, m) in enumerate(zip(roteiro.trechos, cron.trechos)):
        prox = cron.trechos[i + 1].inicio if i + 1 < len(cron.trechos) else cron.total
        tts.append(TrechoTempo(i, tr.cena, tr.titulo_tela, tr.fonte_id, m.inicio, m.fim, prox, tr.ilustracao, tr.enfase))

    corridas: list[Corrida] = []
    chave_atual = None
    for tt in tts:
        if corridas and eh_carimbo(tt.cena):
            corridas[-1].trechos.append(tt)
            continue
        ch = chave_continuidade(tt.cena)
        if corridas and ch == chave_atual:
            corridas[-1].trechos.append(tt)
        else:
            corridas.append(Corrida([tt], primeira=not corridas))
            chave_atual = ch

    for k, cr in enumerate(corridas):
        cr.ini = 0.0 if k == 0 else corridas[k - 1].fim
        if k + 1 < len(corridas):
            cr.fim = (cr.trechos[-1].fim + corridas[k + 1].trechos[0].inicio) / 2
        else:
            cr.fim = cron.total
    return tts, corridas


class Contexto:
    """O que uma cena recebe para desenhar o quadro do instante t."""

    def __init__(self, t: float, corrida: Corrida, roteiro: Roteiro):
        self.t = t
        self.corrida = corrida
        self.roteiro = roteiro
        self.entrada = corrida.entrada
        # trechos (não carimbo) da corrida e o atual
        self.trechos = [tt for tt in corrida.trechos if not eh_carimbo(tt.cena)]
        self.atual = 0
        for k, tt in enumerate(self.trechos):
            if t >= tt.inicio - 0.1:
                self.atual = k
        self.cena = self.trechos[self.atual].cena

    @property
    def lt(self) -> float:
        """Tempo desde a entrada da cena."""
        return self.t - self.entrada

    def inicio(self, k: int) -> float:
        return self.entrada if k == 0 else self.trechos[k].inicio

    def desde(self, condicao) -> float | None:
        """Instante (do trecho) em que `condicao(cena)` passou a valer, contínuo até o atual."""
        quando = None
        for k in range(self.atual + 1):
            if condicao(self.trechos[k].cena):
                if quando is None:
                    quando = self.inicio(k)
            else:
                quando = None
        return quando

    def trecho(self, k: int) -> TrechoTempo:
        return self.trechos[k]

    @property
    def n(self) -> int:
        return len(self.trechos)
