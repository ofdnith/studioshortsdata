"""Legenda da fala, sincronizada, na faixa de baixo do vídeo (estilo Reels).

O texto da legenda é `trecho.legenda` (grafia correta, números em algarismos) ou, se vazio,
a própria fala. Os tempos das palavras são estimados pela proporção de caracteres dentro do
trecho narrado. A palavra que está sendo dita fica amarela.
"""

import re

import skia

from motor import estilo as E

Y_LEGENDA = 1560          # centro da faixa da legenda
LIMITE_CENA = 1480        # as cenas terminam acima disto quando há legenda
TAMANHO, LARG_MAX = 50, 900
MAX_PALAVRAS, MAX_CARACTERES = 6, 30


def blocos(texto: str, inicio: float, fim: float) -> list[dict]:
    """Divide em blocos curtos; cada palavra ganha o instante (estimado) em que é dita."""
    palavras = texto.split()
    if not palavras:
        return []
    total = sum(len(p) + 1 for p in palavras)
    t_pal, acum = [], 0
    for p in palavras:
        t_pal.append(inicio + (fim - inicio) * acum / total)
        acum += len(p) + 1
    res, atual = [], []
    for i, p in enumerate(palavras):
        atual.append(i)
        txt = " ".join(palavras[j] for j in atual)
        fecha = p.endswith((".", "?", "!", ",", ":", ";", "…"))
        prox_longo = i + 1 < len(palavras) and len(txt) + len(palavras[i + 1]) + 1 > MAX_CARACTERES
        if len(atual) >= MAX_PALAVRAS or fecha or prox_longo:
            res.append(atual)
            atual = []
    if atual:
        res.append(atual)
    out = []
    for k, idx in enumerate(res):
        t0 = t_pal[idx[0]] - 0.05
        t1 = t_pal[res[k + 1][0]] - 0.05 if k + 1 < len(res) else fim + 0.35
        out.append({"t0": t0, "t1": t1, "palavras": [(palavras[j], t_pal[j]) for j in idx]})
    return out


def numeros_em_algarismos(fala: str) -> str:
    """Fallback da legenda: 'quarenta e cinco por cento' -> '45%', 'mil novecentos e setenta e três' -> '1973'."""
    from motor.verificacao import numeros_falados
    out = fala
    for n in numeros_falados(fala):
        toks = n.texto.split()
        if not (n.valor >= 10 or n.porcento or not float(n.valor).is_integer() or len(toks) > 1):
            continue   # "um", "uma", "dois"... ficam por extenso
        padrao = r"\b" + r"\W+".join(map(re.escape, toks)) + (r"\s+por\s+cento" if n.porcento else "") + r"\b"
        if 1000 <= n.valor <= 2100 and float(n.valor).is_integer():
            num = str(int(n.valor))   # anos sem ponto
        else:
            casas = 0 if float(n.valor).is_integer() else min(2, len(repr(float(n.valor)).split(".")[1]))
            num = E.fmt_num(n.valor, casas)
        out = re.sub(padrao, num + ("%" if n.porcento else ""), out, count=1, flags=re.I)
    return out


class Legendas:
    def __init__(self, roteiro, tts):
        self.blocos = []
        for tt in tts:
            tr = roteiro.trechos[tt.indice]
            self.blocos += blocos((tr.legenda or numeros_em_algarismos(tr.fala)).strip(), tt.inicio, tt.fim)

    def desenhar(self, c, t: float):
        bloco = next((b for b in self.blocos if b["t0"] <= t < b["t1"]), None)
        if bloco is None:
            return
        tam = TAMANHO
        f = E.font("ExtraBold", tam)
        espaco = f.measureText(" ")
        larg = sum(f.measureText(p) for p, _ in bloco["palavras"]) + espaco * (len(bloco["palavras"]) - 1)
        while larg > LARG_MAX and tam > 30:
            tam -= 2
            f = E.font("ExtraBold", tam)
            espaco = f.measureText(" ")
            larg = sum(f.measureText(p) for p, _ in bloco["palavras"]) + espaco * (len(bloco["palavras"]) - 1)
        k = E.ease_out((t - bloco["t0"]) / 0.12)
        s = 0.92 + 0.08 * k
        c.save()
        c.translate(E.W / 2, Y_LEGENDA)
        c.scale(s, s)
        r = skia.Rect.MakeXYWH(-larg / 2 - 26, -tam * 0.95, larg + 52, tam * 1.6)
        c.drawRRect(skia.RRect.MakeRectXY(r, 22, 22), E.paint(E.hx("05080F"), 0.62 * k))
        x = -larg / 2
        E._registrar(" ".join(p for p, _ in bloco["palavras"]), tam, E.W / 2 - larg / 2, Y_LEGENDA + tam * 0.35,
                     larg, "left", k)
        for p, tp in bloco["palavras"]:
            dita = t >= tp
            atual = dita and all(t < tq or tq <= tp for _, tq in bloco["palavras"])
            cor = E.AMARELO if atual else (E.BRANCO if dita else E.misturar(E.BRANCO, E.FUNDO, 0.35))
            c.drawString(p, x, tam * 0.35, f, E.paint(cor, k))
            x += f.measureText(p) + espaco
        c.restore()
