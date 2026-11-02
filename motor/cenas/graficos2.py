"""Gráficos novos: linha, distribuicao, histograma, pizza, ranking, simulacao.

Gráficos com dados de exemplo (não reais) mostram o selo "dados ilustrativos".
"""

import math
import random

import numpy as np
import skia

from motor import estilo as E
from motor.estilo import (AMARELO, BRANCO, CINZA, FUNDO, GRADE, PAINEL_LN, VERDE, VERMELHO, W, barra, clamp, cor,
                          ease_io, ease_out, fmt_num, paint, painel, pilula, texto)

# área dos gráficos (evita a coluna de ícones do Reels à direita, embaixo)
GX0, GX1, GY0, GY1 = 120, 915, 640, 1380


def selo_ilustrativo(c, a, x=GX1 - 10, y=GY0 + 30, txt="dados ilustrativos"):
    if a > 0.002:
        f = E.font("SemiBold", 22)
        tw = f.measureText(txt)
        pilula(c, txt, x - tw / 2 - 20, y, 22, E.misturar(FUNDO, CINZA, 0.15), CINZA, a, peso="SemiBold")


def _rotulo_valor(v, unidade, casas=None):
    s = fmt_num(v, casas)
    return f"{s}{unidade}" if unidade in ("%", "×") else (f"{s} {unidade}" if unidade else s)


def _escala(vmin, vmax, n=4):
    """Limites e marcas 'redondas' para o eixo."""
    if vmax == vmin:
        vmax = vmin + 1
    passo_bruto = (vmax - vmin) / n
    mag = 10 ** math.floor(math.log10(passo_bruto))
    passo = min((m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= passo_bruto), default=mag * 10)
    lo = math.floor(vmin / passo) * passo
    hi = math.ceil(vmax / passo) * passo
    return lo, hi, [lo + i * passo for i in range(int(round((hi - lo) / passo)) + 1)]


def _desenhar_parcial(c, pts, k, pnt):
    if len(pts) < 2 or k <= 0:
        return
    p = skia.Path()
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    med = skia.PathMeasure(p, False)
    seg = skia.Path()
    med.getSegment(0, med.getLength() * clamp(k), seg, True)
    c.drawPath(seg, pnt)


# ---------------------------------------------------------------- linha

def linha(c, ctx):
    cena, t = ctx.cena, ctx.t
    ap = ease_out((t - ctx.entrada) / 0.4)
    painel(c, GX0 - 30, GY0 - 40, GX1 - GX0 + 60, GY1 - GY0 + 130, ap)
    todos = [v for s in cena.series for v in s.valores]
    vmin, vmax = min(todos), max(todos)
    if vmin >= 0 and vmin < 0.35 * vmax:
        vmin = 0
    lo, hi, marcas = _escala(vmin, vmax)
    x0, x1, y0, y1 = GX0 + 70, GX1 - 30, GY0 + 40, GY1 - 30
    n = max(len(s.valores) for s in cena.series)

    def px(i):
        return x0 + (x1 - x0) * (i / max(1, n - 1))

    def py(v):
        return y1 - (v - lo) / (hi - lo) * (y1 - y0)

    for m in marcas:
        c.drawLine(x0, py(m), x1, py(m), paint(GRADE, ap, stroke=2))
        texto(c, _rotulo_valor(m, cena.unidade), x0 - 14, py(m) + 9, 24, CINZA, ap, "SemiBold", "right")
    passo_rot = max(1, math.ceil(n / 6))
    for i, rot in enumerate(cena.rotulos_x):
        if i % passo_rot == 0 or i == n - 1:
            texto(c, rot, px(i), y1 + 42, 24, CINZA, ap, "SemiBold", "center", maxw=150)
    k = ease_io((t - (ctx.entrada + 0.3)) / 1.6)
    for si, s in enumerate(cena.series):
        col = cor(s.cor, si)
        pts = [(px(i), py(v)) for i, v in enumerate(s.valores)]
        _desenhar_parcial(c, pts, k, paint(col, ap, stroke=7))
        vis = int(k * (len(pts) - 1) + 1e-6)
        for i in range(vis + 1):
            c.drawCircle(*pts[i], 7, paint(col, ap))
        if k >= 0.999:
            texto(c, _rotulo_valor(s.valores[-1], cena.unidade), pts[-1][0], pts[-1][1] - 22, 34, col, ap,
                  "Black", "center")
    if len(cena.series) > 1:
        x = x0
        for si, s in enumerate(cena.series):
            c.drawCircle(x + 10, GY0 + 2, 10, paint(cor(s.cor, si), ap))
            texto(c, s.nome, x + 28, GY0 + 11, 26, CINZA, ap, "SemiBold")
            x += E.font("SemiBold", 26).measureText(s.nome) + 70
    if cena.destaque and cena.destaque in cena.rotulos_x:
        q = ctx.desde(lambda cc: cc.destaque == cena.destaque) or ctx.entrada
        kd = ease_out((t - (q + (1.6 if q == ctx.entrada else 0.3))) / 0.4)
        if kd > 0:
            i = cena.rotulos_x.index(cena.destaque)
            p = paint(AMARELO, ap * kd, stroke=3)
            p.setPathEffect(skia.DashPathEffect.Make([14, 10], 0))
            c.drawLine(px(i), y0, px(i), y1, p)
            if cena.anotacao:
                pilula(c, cena.anotacao, min(max(px(i), 300), 760), y0 + 10, 30, FUNDO, AMARELO, ap * kd, maxw=700)
    if cena.ilustrativo:
        selo_ilustrativo(c, ap, y=GY1 + 70)


# ---------------------------------------------------------------- distribuição

def _pdf(forma, x, mu, sd):
    z = (x - mu) / sd
    if forma == "assimetrica":
        # log-normal deslocada: cauda longa à direita
        xs = np.maximum(x - (mu - 1.6 * sd), 1e-6) / sd
        return np.exp(-(np.log(xs) - 0.4) ** 2 / (2 * 0.45 ** 2)) / xs
    if forma == "bimodal":
        return np.exp(-((z + 1.4) ** 2) / 0.5) + 0.8 * np.exp(-((z - 1.4) ** 2) / 0.5)
    if forma == "uniforme":
        return np.where(np.abs(z) <= 1.7, 1.0, 0.0)
    return np.exp(-z ** 2 / 2)


def distribuicao(c, ctx):
    cena, t = ctx.cena, ctx.t
    ap = ease_out((t - ctx.entrada) / 0.4)
    painel(c, GX0 - 30, GY0 - 40, GX1 - GX0 + 60, GY1 - GY0 + 130, ap)
    mu, sd = cena.media, max(cena.desvio, 1e-9)
    xa, xb = mu - 3.6 * sd, mu + 3.6 * sd
    xs = np.linspace(xa, xb, 240)
    ys = _pdf(cena.forma, xs, mu, sd)
    ys = ys / ys.max()
    x0, x1, y0, y1 = GX0 + 20, GX1 - 20, GY0 + 120, GY1 - 40

    def px(v):
        return x0 + (v - xa) / (xb - xa) * (x1 - x0)

    def py(f):
        return y1 - f * (y1 - y0)

    c.drawLine(x0, y1, x1, y1, paint(PAINEL_LN, ap, stroke=3))
    for kk in (-2, -1, 0, 1, 2):
        v = mu + kk * sd
        c.drawLine(px(v), y1, px(v), y1 + 12, paint(CINZA, ap, stroke=2))
        texto(c, fmt_num(round(v, 2), None), px(v), y1 + 44, 24, CINZA if kk else BRANCO, ap, "SemiBold", "center")
    if cena.rotulo_eixo:
        texto(c, cena.rotulo_eixo, (x0 + x1) / 2, y1 + 84, 26, CINZA, ap, "SemiBold", "center")

    # amostras caindo e formando o histograma
    if cena.amostras:
        rng = np.random.default_rng(7)
        if cena.forma == "normal":
            amostras = rng.normal(mu, sd, 400)
        else:
            amostras = rng.choice(xs, 400, p=ys / ys.sum())
        bins = np.linspace(xa, xb, 31)
        k_am = clamp((t - (ctx.entrada + 0.3)) / 2.2)
        n = int(len(amostras) * k_am)
        cont, _ = np.histogram(amostras[:n], bins)
        hmax = np.histogram(amostras, bins)[0].max()
        for i, cnt in enumerate(cont):
            if cnt:
                h = cnt / hmax * (y1 - y0) * 0.95
                barra(c, px(bins[i]) + 2, y1 - h, px(bins[i + 1]) - px(bins[i]) - 4, h, E.CIANO, ap * 0.45, r=4)
        t_curva, d_curva = ctx.entrada + 2.3, 0.8
    else:
        t_curva, d_curva = ctx.entrada + 0.3, 1.0
    kc = ease_io((t - t_curva) / d_curva)
    fim_curva = t_curva + d_curva   # área e linhas só depois da curva desenhada

    curva = [(px(x), py(y)) for x, y in zip(xs, ys)]
    if cena.sombrear_ate > cena.sombrear_de:
        q = ctx.desde(lambda cc: cc.sombrear_ate > cc.sombrear_de) or ctx.entrada
        ks = ease_io((t - (max(q + 0.3, fim_curva) if q == ctx.entrada else q + 0.3)) / 0.7)
        if ks > 0:
            de, ate = max(cena.sombrear_de, xa), min(cena.sombrear_ate, xb)
            ate_k = de + (ate - de) * ks
            area = skia.Path()
            area.moveTo(px(de), y1)
            for x, y in zip(xs, ys):
                if de <= x <= ate_k:
                    area.lineTo(px(x), py(y))
            area.lineTo(px(ate_k), y1)
            area.close()
            c.drawPath(area, paint(AMARELO, ap * 0.35))
            if ks > 0.95 and cena.rotulo_area:
                f_mid = float(np.interp((de + ate) / 2, xs, ys))
                texto(c, cena.rotulo_area, px((de + ate) / 2), py(f_mid * 0.45), 44, AMARELO, ap, "Black", "center")
    _desenhar_parcial(c, curva, kc, paint(BRANCO, ap, stroke=6))
    for j, ln in enumerate(cena.linhas):
        q = ctx.desde(lambda cc, j=j: len(cc.linhas) > j) or ctx.entrada
        kl = ease_out((t - ((fim_curva + 0.5) if q == ctx.entrada else q + 0.3) - j * 0.3) / 0.4)
        if kl > 0:
            col = cor(ln.cor, j + 3) if ln.cor else VERMELHO
            p = paint(col, ap * kl, stroke=4)
            p.setPathEffect(skia.DashPathEffect.Make([16, 10], 0))
            c.drawLine(px(ln.x), y1, px(ln.x), y0 - 30, p)
            texto(c, ln.rotulo, px(ln.x), y0 - 44 - (j % 2) * 38, 28, col, ap * kl, "Bold", "center", maxw=300)
    if cena.ilustrativo:
        selo_ilustrativo(c, ap, y=GY0 - 8)


# ---------------------------------------------------------------- histograma

def histograma(c, ctx):
    cena, t = ctx.cena, ctx.t
    ap = ease_out((t - ctx.entrada) / 0.4)
    n = len(cena.barras)
    vmax = max(b.valor for b in cena.barras) or 1
    x0, x1, y1, hmax = GX0, GX1, GY1 - 40, GY1 - GY0 - 160
    w = (x1 - x0) / n
    q = ctx.desde(lambda cc: bool(cc.destaque) and cc.destaque == cena.destaque) if cena.destaque else None
    kd = ease_io((t - (q + 0.2)) / 0.3) if q is not None else 0
    for i, b in enumerate(cena.barras):
        k = ease_out((t - (ctx.entrada + 0.2 + i * 0.05)) / 0.5)
        h = b.valor / vmax * hmax * k
        em = b.rotulo in cena.destaque
        col = AMARELO if em and kd > 0 else E.CIANO
        al = ap * (1 - 0.6 * kd if cena.destaque and not em else 1)
        barra(c, x0 + i * w + 2, y1 - h, w - 4, h, col, al, r=6)
        if n <= 12 or i % 2 == 0:
            texto(c, b.rotulo, x0 + i * w + w / 2, y1 + 40, 22 if n > 8 else 26, CINZA, al, "SemiBold", "center",
                  maxw=w * 1.8)
        if n <= 10 and k > 0.9:
            texto(c, _rotulo_valor(b.valor, cena.unidade), x0 + i * w + w / 2, y1 - h - 14, 26, col, al, "Bold",
                  "center", maxw=w + 20)
    c.drawLine(x0, y1, x1, y1, paint(PAINEL_LN, ap, stroke=3))
    if cena.rotulo_eixo:
        texto(c, cena.rotulo_eixo, (x0 + x1) / 2, y1 + 84, 26, CINZA, ap, "SemiBold", "center")
    if cena.ilustrativo:
        selo_ilustrativo(c, ap, y=GY0 + 10)


# ---------------------------------------------------------------- pizza / rosca

def pizza(c, ctx):
    cena, t = ctx.cena, ctx.t
    ap = ease_out((t - ctx.entrada) / 0.4)
    cx, cy, R = W / 2, 930, 300
    total = sum(f.valor for f in cena.fatias) or 1
    k = ease_io((t - (ctx.entrada + 0.2)) / 1.0)
    q = ctx.desde(lambda cc: bool(cc.destaque) and cc.destaque == cena.destaque) if cena.destaque else None
    kd = ease_out((t - (q + 0.2)) / 0.4) if q is not None else 0
    ang = -90.0
    for i, f in enumerate(cena.fatias):
        varr = 360 * f.valor / total * k
        col = cor(f.cor, i)
        em = cena.destaque == f.rotulo
        dx = dy = 0
        if em and kd > 0:
            meio = math.radians(ang + varr / 2)
            dx, dy = math.cos(meio) * 26 * kd, math.sin(meio) * 26 * kd
        al = ap * (1 - 0.5 * kd if cena.destaque and not em else 1)
        p = skia.Path()
        p.moveTo(cx + dx, cy + dy)
        p.arcTo(skia.Rect.MakeLTRB(cx - R + dx, cy - R + dy, cx + R + dx, cy + R + dy), ang, varr, False)
        p.close()
        c.drawPath(p, paint(col, al))
        c.drawPath(p, paint(FUNDO, ap, stroke=4))
        if k > 0.98 and f.valor / total > 0.06:
            meio = math.radians(ang + varr / 2)
            r_txt = R * (0.78 if cena.rosca else 0.62)
            texto(c, f"{fmt_num(100 * f.valor / total, 0)}%", cx + dx + math.cos(meio) * r_txt,
                  cy + dy + math.sin(meio) * r_txt + 14, 40, FUNDO, al, "Black", "center")
        ang += varr
    if cena.rosca:
        c.drawCircle(cx, cy, R * 0.52, paint(E.hx("0E1626"), ap))
        if cena.centro:
            E.linhas(c, E.quebrar_marcado(cena.centro, 48, "ExtraBold", R * 0.9), cy - 40, 48, alpha=ap,
                     maxw=R * 0.95)
    la = ease_out((t - (ctx.entrada + 1.0)) / 0.4)
    ys = cy + R + 70
    col_w = 420
    for i, f in enumerate(cena.fatias):
        x = 150 + (i % 2) * col_w
        y = ys + (i // 2) * 52
        c.drawCircle(x, y - 10, 13, paint(cor(f.cor, i), la * ap))
        texto(c, f.rotulo, x + 26, y, 30, CINZA, la * ap, "SemiBold", maxw=col_w - 50)
    if cena.ilustrativo:
        selo_ilustrativo(c, ap, y=GY0 - 10)


# ---------------------------------------------------------------- ranking

def ranking(c, ctx):
    cena, t = ctx.cena, ctx.t
    itens = sorted(cena.itens, key=lambda i: i.valor, reverse=True)
    n = len(itens)
    vmax = itens[0].valor or 1
    rh = min(140, (GY1 - GY0) / n)
    y_ini = GY0 + ((GY1 - GY0) - rh * n) / 2
    x0, wmax = 400, 440
    q = ctx.desde(lambda cc: bool(cc.destaque) and cc.destaque == cena.destaque) if cena.destaque else None
    kd = ease_io((t - (q + 0.2)) / 0.3) if q is not None else 0
    for i, it in enumerate(itens):
        y = y_ini + i * rh
        k = ease_out((t - (ctx.entrada + 0.15 + i * 0.12)) / 0.5)
        if k <= 0:
            continue
        em = cena.destaque == it.rotulo
        col = cor(it.cor, 0) if it.cor else (AMARELO if em else E.CIANO)
        al = k * (1 - 0.6 * kd if cena.destaque and not em else 1)
        texto(c, f"{i + 1}", 120, y + rh * 0.62, 36, CINZA, al, "Black", "center")
        texto(c, it.rotulo, x0 - 20, y + rh * 0.62, 34, BRANCO, al, "Bold", "right", maxw=x0 - 170)
        w = wmax * it.valor / vmax * k
        barra(c, x0, y + rh * 0.2, w, rh * 0.6, col, al, r=10)
        texto(c, _rotulo_valor(it.valor * k if k < 1 else it.valor, cena.unidade, None if k >= 1 else 0),
              x0 + w + 14, y + rh * 0.62, 34, col, al, "Black")
    if cena.ilustrativo:
        selo_ilustrativo(c, 1, y=GY1 + 40)


# ---------------------------------------------------------------- simulação

def _serie_simulacao(experimento, n, semente=42):
    rnd = random.Random(semente)
    vals = [rnd.random() < 0.5 for _ in range(n)] if experimento == "moeda" else \
        [rnd.randint(1, 6) for _ in range(n)]
    acum = np.cumsum(vals) / np.arange(1, n + 1)
    return (acum * 100 if experimento == "moeda" else acum), vals


def simulacao(c, ctx):
    from motor.ilustracoes.objetos import desenhar_objeto

    cena, t = ctx.cena, ctx.t
    n = max(10, min(cena.lancamentos, 20000))
    serie, vals = _serie_simulacao(cena.experimento, n)
    esperado = 50.0 if cena.experimento == "moeda" else 3.5
    ap = ease_out((t - ctx.entrada) / 0.4)
    dur = max(2.0, sum(tr.fim - max(tr.inicio, ctx.entrada) for tr in ctx.trechos) - 1.0)
    k = clamp((t - (ctx.entrada + 0.6)) / dur)
    # escala logarítmica no número de lançamentos: o começo caótico fica visível
    m = max(1, int(round(n ** k)))
    painel(c, GX0 - 30, GY0 + 60, GX1 - GX0 + 60, GY1 - GY0 - 20, ap)
    x0, x1, y0, y1 = GX0 + 60, GX1 - 30, GY0 + 140, GY1 - 70
    lo, hi = (0, 100) if cena.experimento == "moeda" else (1, 6)

    def px(i):
        return x0 + math.log(i + 1) / math.log(n + 1) * (x1 - x0)

    def py(v):
        return y1 - (v - lo) / (hi - lo) * (y1 - y0)

    for v in ((0, 25, 50, 75, 100) if cena.experimento == "moeda" else (1, 2, 3, 4, 5, 6)):
        c.drawLine(x0, py(v), x1, py(v), paint(GRADE, ap, stroke=2))
        texto(c, f"{v}{'%' if cena.experimento == 'moeda' else ''}", x0 - 12, py(v) + 9, 22, CINZA, ap,
              "SemiBold", "right")
    p = paint(AMARELO, ap, stroke=3)
    p.setPathEffect(skia.DashPathEffect.Make([14, 10], 0))
    c.drawLine(x0, py(esperado), x1, py(esperado), p)
    idx = np.unique(np.geomspace(1, m, num=min(m, 300)).astype(int)) - 1
    pts = [(px(i), py(serie[i])) for i in idx]
    if len(pts) > 1:
        path = skia.Path()
        path.moveTo(*pts[0])
        for q in pts[1:]:
            path.lineTo(*q)
        c.drawPath(path, paint(E.CIANO, ap, stroke=5))
        c.drawCircle(*pts[-1], 9, paint(E.CIANO, ap))
    for marca in (10, 100, 1000, 10000):
        if marca <= n:
            texto(c, fmt_num(marca), px(marca - 1), y1 + 38, 22, CINZA, ap, "SemiBold", "center")
    rot = "caras" if cena.experimento == "moeda" else "média dos dados"
    valor = serie[m - 1]
    texto(c, f"{fmt_num(m)} lançamentos", x0, GY0 + 40, 34, BRANCO, ap, "ExtraBold")
    texto(c, f"{rot}: {fmt_num(round(float(valor), 1), 1)}{'%' if cena.experimento == 'moeda' else ''}",
          x0, GY0 + 88, 34, E.CIANO, ap, "Bold")
    texto(c, f"esperado: {fmt_num(esperado, 1 if esperado % 1 else 0)}{'%' if cena.experimento == 'moeda' else ''}",
          x1, GY0 + 88, 28, AMARELO, ap, "Bold", "right")
    desenhar_objeto(c, "moeda" if cena.experimento == "moeda" else "dado", x1 - 50, GY0 + 10, 90, ap,
                    t - ctx.entrada, entrada=False)
    selo_ilustrativo(c, ap, txt="simulação", y=GY1 + 30)
