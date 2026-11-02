"""Cenas de pontos: dispersao (morph entre conjuntos) e grade_graficos (pequenos múltiplos)."""

import csv
import math
from functools import lru_cache

import numpy as np
import skia
from scipy.optimize import linear_sum_assignment

from motor import estilo as E
from motor.estilo import (AMARELO, CINZA, FUNDO, PAINEL, PAINEL_LN, PONTO, VERDE, VERMELHO, W,
                          back_out, clamp, ease_io, ease_out, paint, painel, pilula)

DADOS = E.PASTA / "dados"
NOMES_DATASAURUS = {"dino": "dinossauro", "star": "estrela", "circle": "círculo", "bullseye": "alvo",
                    "x_shape": "xis", "v_lines": "linhas verticais", "h_lines": "linhas horizontais",
                    "slant_up": "diagonal", "dots": "pontos", "high_lines": "faixas", "wide_lines": "moldura",
                    "away": "nuvem", "slant_down": "diagonal invertida"}


@lru_cache(maxsize=None)
def _embutidos() -> dict[str, np.ndarray]:
    res: dict[str, list] = {}
    with open(DADOS / "DatasaurusDozen.tsv") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            res.setdefault(f"datasaurus/{r['dataset']}", []).append((float(r["x"]), float(r["y"])))
    with open(DADOS / "anscombe.csv") as f:
        for r in csv.DictReader(f):
            res.setdefault(f"anscombe/{r['dataset']}", []).append((float(r["x"]), float(r["y"])))
    return {k: np.array(v) for k, v in res.items()}


def conjunto(ref) -> tuple[str, np.ndarray]:
    """('nome legível', pontos Nx2) de um conjunto embutido ou inline."""
    if isinstance(ref, str):
        pts = _embutidos().get(ref)
        if pts is None:
            raise ValueError(f"Conjunto de pontos desconhecido: {ref}")
        chave = ref.split("/", 1)[1]
        return NOMES_DATASAURUS.get(chave, chave), pts
    return ref.nome, np.array([(p.x, p.y) for p in ref.pontos])


def _casar(prev: np.ndarray, pts: np.ndarray) -> np.ndarray:
    """Reordena `pts` para casar com `prev` (matching húngaro); iguala o número de pontos."""
    if len(pts) != len(prev):
        idx = np.linspace(0, len(pts) - 1, len(prev)).round().astype(int)
        pts = pts[idx]
    custo = ((prev[:, None, :] - pts[None, :, :]) ** 2).sum(-1)
    _, col = linear_sum_assignment(custo)
    return pts[col]


def mapeador(x, y, w, h, xr, yr, pad=36):
    def f(px, py):
        return (x + pad + (px - xr[0]) / (xr[1] - xr[0]) * (w - 2 * pad),
                y + h - pad - (py - yr[0]) / (yr[1] - yr[0]) * (h - 2 * pad))
    return f


def faixa(arrs, margem=0.08):
    todos = np.vstack(arrs)
    lo, hi = todos.min(0), todos.max(0)
    d = np.maximum(hi - lo, 1e-9)
    return (lo[0] - d[0] * margem, hi[0] + d[0] * margem), (lo[1] - d[1] * margem, hi[1] + d[1] * margem)


def pontos(c, pts, m, r, alpha=1.0, cor_=PONTO, pop=None):
    p = paint(cor_, alpha)
    for i, (px, py) in enumerate(pts):
        k = 1.0 if pop is None else pop[i]
        if k <= 0:
            continue
        sx, sy = m(px, py)
        c.drawCircle(sx, sy, r * (back_out(k) if k < 1 else 1), p)


def etiqueta(c, s, x, y, alpha, cor_=AMARELO):
    if alpha > 0.002:
        pilula(c, s, x + E.font("Bold", 30).measureText(s) / 2 + 27, y, 30, (30, 24, 8), cor_, alpha)


def painel_estatisticas(c, stats, alpha, y=548, checks=None):
    if alpha <= 0.002 or not stats:
        return
    n = len(stats)
    cw = 900 / n
    for i, st in enumerate(stats):
        cx = W / 2 + (i - (n - 1) / 2) * cw
        r = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(cx - cw / 2 + 8, y, cw - 16, 116), 22, 22)
        c.drawRRect(r, paint(PAINEL, alpha))
        c.drawRRect(r, paint(PAINEL_LN, alpha, stroke=2))
        E.texto(c, st.rotulo.upper(), cx, y + 40, 24, CINZA, alpha, "SemiBold", "center", maxw=cw - 40)
        E.texto(c, st.valor, cx, y + 90, 38, E.BRANCO, alpha, "ExtraBold", "center", maxw=cw - 40)
        if checks is not None:
            k = ease_out((checks - i * 0.15) / 0.3)
            if k > 0:
                E.check(c, cx + cw / 2 - 26, y + 18, 17 * back_out(k), alpha)


# ---------------------------------------------------------------- dispersão

BX, BY, BW, BH = 160, 690, 760, 760


def _sequencia(ctx):
    """Sequência de conjuntos da corrida: cada trecho mostra os seus, espalhados pela fala.
    Calculada uma vez por corrida (o pareamento húngaro é caro)."""
    if getattr(ctx.corrida, "_seq", None) is not None:
        return ctx.corrida._seq
    seq = []   # (t_inicio_morph, nome, pontos)
    prev = None
    for k in range(ctx.n):
        tr = ctx.trecho(k)
        cs = ctx.trecho(k).cena.conjuntos
        t_ini = ctx.inicio(k)
        dur = max(1.0, tr.fim - max(t_ini, tr.inicio))
        passo = dur / max(1, len(cs))
        for j, ref in enumerate(cs):
            nome, pts = conjunto(ref)
            if prev is not None:
                pts = _casar(prev, pts)
            tj = t_ini if (k == 0 and j == 0) else max(t_ini, tr.inicio) + 0.3 + j * passo
            if prev is not None and np.allclose(prev, pts):
                continue
            seq.append((tj, nome, pts))
            prev = pts
    ctx.corrida._seq = seq
    return seq


def dispersao(c, ctx):
    t = ctx.t
    seq = _sequencia(ctx)
    xr, yr = faixa([p for _, _, p in seq])
    m = mapeador(BX, BY, BW, BH, xr, yr, pad=40)
    ap = ease_out((t - ctx.entrada) / 0.4)
    painel(c, BX, BY, BW, BH, ap, grade=4)
    cur, nome_atual = seq[0][2], seq[0][1]
    for i, (tj, nome, pts) in enumerate(seq[1:], 1):
        if t < tj:
            break
        md = min(0.7, (seq[i + 1][0] - tj) * 0.6) if i + 1 < len(seq) else 0.7
        k = ease_io((t - tj) / md)
        cur = cur + (pts - cur) * k if k < 1 else pts
        if k > 0.5:
            nome_atual = nome
    pontos(c, cur, m, 8.5 if len(cur) > 40 else 12, ap)
    cena = ctx.cena
    if cena.reta:
        q = ctx.desde(lambda cc: cc.reta is not None)
        kr = ease_io((t - (q + 0.3)) / 0.6)
        if kr > 0:
            x0, x1 = xr[0], xr[0] + (xr[1] - xr[0]) * kr
            c.drawLine(*m(x0, cena.reta.a + cena.reta.b * x0), *m(x1, cena.reta.a + cena.reta.b * x1),
                       paint(AMARELO, ap * 0.9, stroke=5))
    if cena.mostrar_nome:
        etiqueta(c, nome_atual, BX + 40, BY + 52, ap)
    if cena.estatisticas:
        q = ctx.desde(lambda cc: bool(cc.estatisticas))
        sa = ease_out((t - q) / 0.3)
        painel_estatisticas(c, cena.estatisticas, sa)


# ---------------------------------------------------------------- grade de gráficos

def _layout(n):
    if n == 2:
        return [(110, 830, 420), (550, 830, 420)]
    if n == 3:
        return [(140, 670, 380), (560, 670, 380), (350, 1072, 380)]
    return [(140, 670, 380), (560, 670, 380), (140, 1072, 380), (560, 1072, 380)]


def grade_graficos(c, ctx):
    cena, t = ctx.cena, ctx.t
    conj = [conjunto(g.conjunto)[1] for g in cena.graficos]
    xr, yr = faixa(conj, 0.1)
    foco = cena.foco
    q_foco = ctx.desde(lambda cc: cc.foco == foco) if foco is not None else None
    kf = ease_io((t - (q_foco - 0.1)) / 0.25) if q_foco is not None else 0
    for i, (g, pts, (x, y, gw)) in enumerate(zip(cena.graficos, conj, _layout(len(cena.graficos)))):
        m = mapeador(x, y, gw, gw, xr, yr, pad=34)
        ap = ease_out((t - (ctx.entrada + 0.2 + i * 0.12)) / 0.35)
        if ap <= 0:
            continue
        dim = 1.0 if foco is None or i == foco else 1 - 0.7 * kf
        al = ap * dim
        c.save()
        s = 0.94 + 0.06 * ap
        c.translate(x + gw / 2, y + gw / 2); c.scale(s, s); c.translate(-x - gw / 2, -y - gw / 2)
        painel(c, x, y, gw, gw, al, grade=3)
        E.texto(c, g.titulo, x + 22, y + 48, 34, CINZA, al, "Black", maxw=gw - 44)
        if g.reta:
            q = ctx.desde(lambda cc, i=i: cc.graficos[i].reta is not None)
            kr = ease_io((t - (q + 1.2 + i * 0.1)) / 0.6) if q is not None else 0
            if kr > 0:
                x0, x1 = xr[0] + 1, xr[0] + 1 + (xr[1] - xr[0] - 2) * kr
                c.drawLine(*m(x0, g.reta.a + g.reta.b * x0), *m(x1, g.reta.a + g.reta.b * x1),
                           paint(AMARELO, al * 0.9, stroke=5))
        pop = [clamp((t - (ctx.entrada + 0.8 + i * 0.25 + j * 0.06)) / 0.25) for j in range(len(pts))]
        pontos(c, pts, m, 10, al, pop=pop)
        if g.curva and foco == i:
            kc = ease_io((t - (q_foco + 0.2)) / 0.7)
            if kc > 0:
                co = np.polyfit(pts[:, 0], pts[:, 1], 2)
                x_lo, x_hi = pts[:, 0].min(), pts[:, 0].max()
                path = skia.Path()
                for n_, xv in enumerate(np.linspace(x_lo, x_lo + (x_hi - x_lo) * kc, 40)):
                    sx, sy = m(xv, np.polyval(co, xv))
                    (path.moveTo if n_ == 0 else path.lineTo)(sx, sy)
                c.drawPath(path, paint(VERDE, al, stroke=5))
        if g.outlier and foco == i:
            ko = ease_out((t - (q_foco + 0.4)) / 0.4)
            if ko > 0:
                sx, sy = m(g.outlier.x, g.outlier.y)
                pulso = 0.5 + 0.5 * math.sin((t - q_foco) * 6)
                c.drawCircle(sx, sy, 24 + 6 * pulso, paint(VERMELHO, al * ko, stroke=5))
        c.restore()
