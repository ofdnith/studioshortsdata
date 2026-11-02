"""Gráficos fáceis de ler: medidor, bolhas, funil, mapa_calor, inclinacao, escala, arvore."""

import math

import skia

from motor import estilo as E
from motor.estilo import (AMARELO, BRANCO, CINZA, FUNDO, PAINEL, PAINEL_LN, VERDE, VERMELHO, W, back_out, barra,
                          clamp, cor, ease_io, ease_out, fmt_num, paint, painel, pilula, texto, vis)
from motor.cenas.graficos2 import selo_ilustrativo


def _u(v, unidade, casas=None):
    return E.com_unidade(v, unidade, casas)


def _anterior(ctx, campo):
    """Valor do campo no trecho anterior da mesma corrida (para animar a mudança), ou None."""
    if ctx.atual == 0:
        return None
    return getattr(ctx.trecho(ctx.atual - 1).cena, campo, None)


def _destaque_k(ctx, cena, attr="destaque"):
    alvo = getattr(cena, attr)
    if not alvo:
        return 0
    q = ctx.desde(lambda cc: getattr(cc, attr) == alvo)
    return ease_io((ctx.t - (q + 0.2)) / 0.3) if q is not None else 0


# ---------------------------------------------------------------- medidor

def medidor(c, ctx):
    cena, t = ctx.cena, ctx.t
    ap = ease_out((t - ctx.entrada) / 0.4)
    cx, cy, R = W / 2, 1090, 360
    lo, hi = cena.minimo, cena.maximo
    frac = lambda v: clamp((v - lo) / ((hi - lo) or 1))  # noqa: E731
    # arco de fundo (com zonas verde/amarelo/vermelho, se pedido)
    ret = skia.Rect.MakeLTRB(cx - R, cy - R, cx + R, cy + R)
    if cena.zonas:
        for i, col in enumerate((VERDE, AMARELO, VERMELHO)):
            arco = skia.Path()
            arco.addArc(ret, 180 + i * 60, 60)
            c.drawPath(arco, paint(col, ap * 0.85, stroke=46))
    else:
        arco = skia.Path()
        arco.addArc(ret, 180, 180)
        c.drawPath(arco, paint(PAINEL_LN, ap, stroke=46))
    # ponteiro: anima do valor anterior (mesma corrida) até o atual
    ant = _anterior(ctx, "valor")
    ini = ctx.inicio(ctx.atual)
    de = frac(ant) if ant is not None else 0.0
    k = ease_io((t - (ini + (0.3 if ant is None else 0.15))) / 1.0)
    f = de + (frac(cena.valor) - de) * k
    if not cena.zonas:
        cheio = skia.Path()
        cheio.addArc(ret, 180, 180 * f)
        c.drawPath(cheio, paint(cor(cena.cor, 3) if cena.cor else AMARELO, ap, stroke=46))
    ang = math.pi * (1 - f)
    px, py = cx + (R - 70) * math.cos(ang), cy - (R - 70) * math.sin(ang)
    c.drawLine(cx, cy, px, py, paint(BRANCO, ap, stroke=12))
    c.drawCircle(cx, cy, 26, paint(BRANCO, ap))
    c.drawCircle(cx, cy, 11, paint(FUNDO, ap))
    texto(c, _u(lo, cena.unidade), cx - R, cy + 60, 30, CINZA, ap, "SemiBold", "center")
    texto(c, _u(hi, cena.unidade), cx + R, cy + 60, 30, CINZA, ap, "SemiBold", "center")
    v = (ant if ant is not None else lo) + (cena.valor - (ant if ant is not None else lo)) * k
    texto(c, _u(v if k < 1 else cena.valor, cena.unidade, 0 if k < 1 else None), cx, cy + 170, 120, AMARELO, ap,
          "Black", "center", maxw=800)
    if cena.rotulo:
        texto(c, cena.rotulo, cx, cy + 240, 40, BRANCO, ap, "Bold", "center", maxw=880)
    if cena.ilustrativo:
        selo_ilustrativo(c, ap, y=1455)


# ---------------------------------------------------------------- bolhas (área proporcional)

def bolhas(c, ctx):
    cena, t = ctx.cena, ctx.t
    itens = cena.itens
    vmax = max(i.valor for i in itens) or 1
    rmax = min(300, 860 / (len(itens) * 1.1) * (1 if len(itens) > 2 else 1.2))
    raios = [max(10, rmax * math.sqrt(i.valor / vmax)) for i in itens]
    total_w = sum(2 * r for r in raios) + 40 * (len(itens) - 1)
    x = W / 2 - total_w / 2
    base = 1240
    kd = _destaque_k(ctx, cena)
    for i, (it, r) in enumerate(zip(itens, raios)):
        x += r
        k = back_out((t - (ctx.entrada + 0.2 + i * 0.35)) / 0.5)
        em = cena.destaque == it.rotulo
        al = 1 - 0.55 * kd if cena.destaque and not em else 1
        if k > 0:
            col = cor(it.cor, i)
            c.drawCircle(x, base - r, r * k, paint(col, al * 0.9))
            if em and kd > 0:
                c.drawCircle(x, base - r, r * k + 10, paint(AMARELO, kd, stroke=6))
            rot_v = _u(it.valor, cena.unidade)
            tam = min(64, max(26, r * 0.42))
            dentro = r > E.font("Black", tam).measureText(rot_v) / 2 + 12
            texto(c, rot_v, x, (base - r + tam * 0.35) if dentro else (base - 2 * r - 20), tam,
                  FUNDO if dentro else col, al * min(1, k), "Black", "center", maxw=max(2 * r - 20, 200))
            texto(c, it.rotulo, x, base + 54, 34, CINZA, al * min(1, k), "Bold", "center", maxw=max(2 * r + 30, 180))
        x += r + 40
    if cena.ilustrativo:
        selo_ilustrativo(c, 1, y=1455)


# ---------------------------------------------------------------- funil

def funil(c, ctx):
    cena, t = ctx.cena, ctx.t
    et = cena.etapas
    n = len(et)
    vmax = et[0].valor or 1
    h = min(140, 760 / n)
    y0 = 1050 - n * h / 2
    for i, e in enumerate(et):
        k = ease_out((t - (ctx.entrada + 0.2 + i * 0.3)) / 0.45)
        if k <= 0:
            continue
        # largura pela raiz do valor: com quedas grandes (1.000 → 9) o funil continua legível
        w = max(170, 820 * math.sqrt(e.valor / vmax))
        w_prox = max(170, 820 * math.sqrt(et[i + 1].valor / vmax)) if i + 1 < n else w * 0.85
        y = y0 + i * h
        trap = skia.Path()
        trap.moveTo(W / 2 - w / 2, y + 6)
        trap.lineTo(W / 2 + w / 2, y + 6)
        trap.lineTo(W / 2 + w_prox / 2, y + h - 6)
        trap.lineTo(W / 2 - w_prox / 2, y + h - 6)
        trap.close()
        col = E.misturar(E.CIANO, AMARELO, i / max(1, n - 1))
        c.drawPath(trap, paint(col, k * 0.9))
        texto(c, _u(e.valor, cena.unidade), W / 2, y + h * 0.48, min(46, h * 0.38), FUNDO, k, "Black", "center")
        texto(c, e.rotulo, W / 2, y + h * 0.48 + min(34, h * 0.28), min(28, h * 0.22), FUNDO, k * 0.85, "Bold",
              "center", maxw=max(w_prox - 30, 110))
        if i > 0 and k > 0.8:
            pct = 100 * e.valor / (et[i - 1].valor or 1)
            texto(c, f"{fmt_num(pct, 0)}%", W / 2 + max(w, w_prox) / 2 + 20, y + 22, 28, CINZA, k, "Bold")
    if cena.ilustrativo:
        selo_ilustrativo(c, 1, y=1455)


# ---------------------------------------------------------------- mapa de calor

def mapa_calor(c, ctx):
    cena, t = ctx.cena, ctx.t
    nl, nc = len(cena.linhas), len(cena.colunas)
    rot_w = min(200, max(E.font("Bold", 30).measureText(l) for l in cena.linhas) + 30)
    x0 = 100 + rot_w
    cw = min(200, (950 - x0) / nc)
    ch = min(140, 640 / nl)
    y0 = 760
    vals = [v for linha in cena.valores for v in linha]
    lo, hi = min(vals), max(vals)
    for j, nome in enumerate(cena.colunas):
        texto(c, nome, x0 + j * cw + cw / 2, y0 - 20, 26, CINZA, ease_out((t - ctx.entrada) / 0.4), "Bold", "center",
              maxw=cw - 6)
    for i, nome in enumerate(cena.linhas):
        k_l = ease_out((t - (ctx.entrada + 0.2 + i * 0.15)) / 0.4)
        texto(c, nome, x0 - 16, y0 + i * ch + ch * 0.6, 30, BRANCO, k_l, "Bold", "right", maxw=rot_w - 10)
        for j in range(nc):
            v = cena.valores[i][j] if i < len(cena.valores) and j < len(cena.valores[i]) else 0
            k = ease_out((t - (ctx.entrada + 0.3 + i * 0.15 + j * 0.05)) / 0.35)
            if k <= 0:
                continue
            f = (v - lo) / ((hi - lo) or 1)
            col = E.misturar(E.hx("1E3A5F"), AMARELO, f) if f < 0.98 else AMARELO
            x, y = x0 + j * cw, y0 + i * ch
            barra(c, x + 4, y + 4, cw - 8, ch - 8, col, k, r=10)
            if cw > 70:
                texto(c, fmt_num(v), x + cw / 2, y + ch * 0.6, min(34, ch * 0.32), FUNDO if f > 0.55 else BRANCO, k,
                      "Bold", "center", maxw=cw - 14)
    if cena.ilustrativo:
        selo_ilustrativo(c, 1, y=1455)


# ---------------------------------------------------------------- inclinação (antes → depois)

def inclinacao(c, ctx):
    cena, t = ctx.cena, ctx.t
    xa, xb, y0, y1 = 300, 780, 760, 1380
    vals = [v for i in cena.itens for v in (i.antes, i.depois)]
    lo, hi = min(vals), max(vals)
    if lo >= 0 and lo < 0.4 * hi:
        lo = 0
    py = lambda v: y1 - (v - lo) / ((hi - lo) or 1) * (y1 - y0)  # noqa: E731
    ap = ease_out((t - ctx.entrada) / 0.4)
    for x, rot in ((xa, cena.rotulo_antes), (xb, cena.rotulo_depois)):
        c.drawLine(x, y0 - 30, x, y1 + 10, paint(PAINEL_LN, ap, stroke=4))
        texto(c, rot, x, y0 - 60, 36, CINZA, ap, "Bold", "center", maxw=380)
    kd = _destaque_k(ctx, cena)
    for i, it in enumerate(cena.itens):
        col = cor(it.cor, i)
        em = cena.destaque == it.rotulo
        al = ap * (1 - 0.6 * kd if cena.destaque and not em else 1)
        ka = ease_out((t - (ctx.entrada + 0.3 + i * 0.15)) / 0.3)
        kl = ease_io((t - (ctx.entrada + 0.8 + i * 0.2)) / 0.7)
        if ka <= 0:
            continue
        ya, yb = py(it.antes), py(it.depois)
        c.drawCircle(xa, ya, 12, paint(col, al * ka))
        texto(c, _u(it.antes, cena.unidade), xa - 26, ya + 12, 32, col, al * ka, "Bold", "right")
        texto(c, it.rotulo, xa - 26, ya + 46, 24, CINZA, al * ka, "SemiBold", "right", maxw=200)
        if kl > 0:
            c.drawLine(xa, ya, xa + (xb - xa) * kl, ya + (yb - ya) * kl, paint(col, al, stroke=7 if em else 5))
        if kl >= 1:
            c.drawCircle(xb, yb, 12, paint(col, al))
            texto(c, _u(it.depois, cena.unidade), xb + 26, yb + 12, 32, col, al, "Black")
    if cena.ilustrativo:
        selo_ilustrativo(c, ap, y=1455)


# ---------------------------------------------------------------- escala (régua)

def escala(c, ctx):
    cena, t = ctx.cena, ctx.t
    x0, x1, y = 130, 930, 1080
    lo, hi = cena.minimo, cena.maximo
    px = lambda v: x0 + clamp((v - lo) / ((hi - lo) or 1)) * (x1 - x0)  # noqa: E731
    ap = ease_out((t - ctx.entrada) / 0.4)
    kr = ease_io((t - ctx.entrada) / 0.6)
    if cena.faixa_ate > cena.faixa_de:
        q = ctx.desde(lambda cc: cc.faixa_ate > cc.faixa_de) or ctx.entrada
        kf = ease_out((t - (q + (0.7 if q == ctx.entrada else 0.2))) / 0.5)
        if kf > 0:
            barra(c, px(cena.faixa_de), y - 50, (px(cena.faixa_ate) - px(cena.faixa_de)) * kf, 100,
                  E.misturar(FUNDO, VERDE, 0.35), ap, r=16)
            if cena.rotulo_faixa:
                texto(c, cena.rotulo_faixa, (px(cena.faixa_de) + px(cena.faixa_ate)) / 2, y + 100, 32, VERDE,
                      ap * kf, "Bold", "center", maxw=600)
    c.drawLine(x0, y, x0 + (x1 - x0) * kr, y, paint(BRANCO, ap, stroke=8))
    for k_ in range(6):
        v = lo + (hi - lo) * k_ / 5
        c.drawLine(px(v), y - 14, px(v), y + 14, paint(BRANCO, ap * kr, stroke=4))
        texto(c, _u(round(v, 2), cena.unidade), px(v), y + 60, 26, CINZA, ap * kr, "SemiBold", "center")
    for j, m in enumerate(cena.marcadores):
        q = ctx.desde(lambda cc, j=j: len(cc.marcadores) > j) or ctx.entrada
        k = back_out((t - (q + (0.9 if q == ctx.entrada else 0.2) + j * 0.35)) / 0.45)
        if k <= 0:
            continue
        col = cor(m.cor, j) if m.cor else (AMARELO if j == 0 else E.CIANO)
        x = px(m.valor)
        topo = y - 170 - (j % 2) * 110
        c.drawLine(x, topo + 40, x, y - 20, paint(col, min(1, k), stroke=4))
        c.drawPath(_triangulo(x, y - 18), paint(col, min(1, k)))
        pilula(c, f"{m.rotulo}: {_u(m.valor, cena.unidade)}" if m.rotulo else _u(m.valor, cena.unidade),
               min(max(x, 260), 820), topo + 10, 30, FUNDO, col, min(1, k), peso="Bold", maxw=560)
    if cena.ilustrativo:
        selo_ilustrativo(c, ap, y=1455)


def _triangulo(x, y):
    p = skia.Path()
    p.moveTo(x, y)
    p.lineTo(x - 14, y - 24)
    p.lineTo(x + 14, y - 24)
    p.close()
    return p


# ---------------------------------------------------------------- árvore de frequências

def _caixa(c, cx, cy, w, h, rotulo, valor, unidade, col, a, destaque=False):
    if a <= 0.002:
        return
    r = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(cx - w / 2, cy - h / 2, w, h), 22, 22)
    c.drawRRect(r, paint(E.misturar(FUNDO, col, 0.35) if destaque else PAINEL, a))
    c.drawRRect(r, paint(col, a, stroke=5 if destaque else 3))
    texto(c, _u(valor, unidade), cx, cy + 6, min(54, h * 0.42), BRANCO, a, "Black", "center", maxw=w - 20)
    texto(c, rotulo, cx, cy + h * 0.36, min(26, h * 0.2), CINZA if not destaque else BRANCO, a, "Bold", "center",
          maxw=w - 16)


def arvore(c, ctx):
    cena, t = ctx.cena, ctx.t
    destaques = set(cena.destaque)
    q = ctx.desde(lambda cc: set(cc.destaque) == destaques) if destaques else None
    kd = ease_io((t - (q + 0.2)) / 0.3) if q is not None else 0
    raiz_y, n1_y, n2_y = 700, 960, 1260
    a0 = ease_out((t - ctx.entrada) / 0.4)
    _caixa(c, W / 2, raiz_y, 380, 120, cena.rotulo_total, cena.total, cena.unidade, BRANCO, a0)
    ramos = cena.ramos
    n = len(ramos)
    folhas = sum(max(1, len(r.filhos)) for r in ramos)
    larg_folha = min(250, 900 / max(1, folhas))
    x_folha = W / 2 - larg_folha * folhas / 2
    for i, ramo in enumerate(ramos):
        col = cor(ramo.cor, i) if ramo.cor else (VERMELHO if i == 0 else VERDE)
        nf = max(1, len(ramo.filhos))
        cx = x_folha + larg_folha * nf / 2
        k1 = ease_out((t - (ctx.entrada + 0.5 + i * 0.3)) / 0.4)
        if k1 > 0:
            c.drawLine(W / 2, raiz_y + 60, cx, n1_y - 60, paint(PAINEL_LN, k1, stroke=4))
            _caixa(c, cx, n1_y, min(320, larg_folha * nf - 20), 110, ramo.rotulo, ramo.valor, cena.unidade, col, k1,
                   destaque=ramo.rotulo in destaques and kd > 0)
        for j, f in enumerate(ramo.filhos):
            fx = x_folha + larg_folha * (j + 0.5)
            k2 = ease_out((t - (ctx.entrada + 1.2 + i * 0.3 + j * 0.2)) / 0.4)
            if k2 > 0:
                em = f.rotulo in destaques and kd > 0
                al = k2 * (1 - 0.5 * kd if destaques and not em and kd > 0 else 1)
                c.drawLine(cx, n1_y + 55, fx, n2_y - 55, paint(PAINEL_LN, al, stroke=3))
                _caixa(c, fx, n2_y, larg_folha - 18, 110, f.rotulo, f.valor, cena.unidade,
                       cor(f.cor, j + 2) if f.cor else col, al, destaque=em)
        x_folha += larg_folha * nf
    if cena.ilustrativo:
        selo_ilustrativo(c, 1, y=1455)
