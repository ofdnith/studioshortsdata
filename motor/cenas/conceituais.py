"""Cenas de apoio: icones, numero_grande, objeto, comparacao, linha_do_tempo, passos, citacao."""

import math

import skia

from motor import estilo as E
from motor.estilo import (AMARELO, BRANCO, CINZA, FUNDO, PAINEL, PAINEL_LN, VERDE, VERMELHO, W, back_out, barra,
                          clamp, cor, ease_io, ease_out, fmt_num, paint, pilula, texto, vis)
from motor.ilustracoes.objetos import desenhar_objeto
from motor.ilustracoes.pessoas import retrato


def _boneco(c, x, y, s, col, a):
    c.drawCircle(x, y - s * 0.55, s * 0.28, paint(col, a))
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x - s * 0.36, y - s * 0.2, s * 0.72, s * 0.75),
                                      s * 0.3, s * 0.3), paint(col, a))


# ---------------------------------------------------------------- ícones (isotipo)

def icones(c, ctx):
    cena, t = ctx.cena, ctx.t
    total = max(1, min(cena.total, 100))
    cols = 10 if total > 40 else (5 if total > 12 else 4)
    linhas = math.ceil(total / cols)
    cel = min(84, 760 / cols, 620 / linhas)
    x0 = W / 2 - cols * cel / 2
    y0 = 700 + (620 - linhas * cel) / 2
    destaque = max(0, min(cena.destaque, total))
    col_d = cor(cena.cor, 0) if cena.cor else AMARELO
    q = ctx.desde(lambda cc: cc.destaque == cena.destaque) or ctx.entrada
    t_pinta = q + (1.0 if q == ctx.entrada else 0.3)
    for i in range(total):
        r, k_ = divmod(i, cols)
        x, y = x0 + k_ * cel + cel / 2, y0 + r * cel + cel / 2
        kk = back_out((t - (ctx.entrada + i * min(0.012, 0.9 / total))) / 0.3)
        if kk <= 0:
            continue
        pinta = i < destaque and t > t_pinta + i * min(0.02, 0.8 / max(1, destaque))
        col = col_d if pinta else E.misturar(FUNDO, CINZA, 0.45)
        if cena.icone == "circulo":
            c.drawCircle(x, y, cel * 0.36 * kk, paint(col, 1))
        else:
            _boneco(c, x, y + cel * 0.12, cel * 0.75 * kk, col, 1)
    if cena.rotulo:
        a, e = vis(t, t_pinta + 0.3, None)
        E.linhas(c, E.quebrar_marcado(cena.rotulo, 64, "Black", 900), y0 + linhas * cel + 40 + (1 - e) * 16, 64,
                 peso="Black", alpha=a, destaque=col_d)


# ---------------------------------------------------------------- número grande

def numero_grande(c, ctx):
    cena, t = ctx.cena, ctx.t
    lt = t - ctx.entrada
    y_num = 1000 if cena.objeto else 900
    if cena.objeto:
        desenhar_objeto(c, cena.objeto, W / 2, 720, 220, 1, lt)
    k = ease_io((lt - 0.2) / 1.4)
    v = cena.valor * k
    casas = cena.casas if k >= 1 else (0 if float(cena.valor).is_integer() else cena.casas)
    s = f"{cena.prefixo}{fmt_num(v, casas)}{cena.sufixo}"
    tam = 220
    f = E.font("Black", tam)
    while f.measureText(s) > 900 and tam > 60:
        tam -= 6
        f = E.font("Black", tam)
    a = ease_out(lt / 0.3)
    tw = f.measureText(s)
    c.drawString(s, W / 2 - tw / 2, y_num + tam * 0.35, f, paint(AMARELO, a))
    if cena.contexto:
        ac, e = vis(t, ctx.entrada + 1.0, None)
        E.linhas(c, E.quebrar_marcado(cena.contexto, 50, "Bold", 880), y_num + tam * 0.35 + 50 + (1 - e) * 16, 50,
                 peso="Bold", alpha=ac, cor_=BRANCO)


# ---------------------------------------------------------------- objeto ilustrado

def objeto(c, ctx):
    cena, t = ctx.cena, ctx.t
    lt = t - ctx.entrada
    c.drawCircle(W / 2, 930, 330, paint(AMARELO, 0.06 * ease_out(lt / 0.4), blur=40))
    desenhar_objeto(c, cena.objeto, W / 2, 930, 560, 1, lt)
    if cena.legenda:
        a, e = vis(t, ctx.entrada + 0.6, None)
        E.linhas(c, E.quebrar_marcado(cena.legenda, 56, "ExtraBold", 880), 1270 + (1 - e) * 16, 56, alpha=a)


# ---------------------------------------------------------------- comparação

ESTILOS_COMP = {
    "versus": (E.CIANO, E.ROXO, "VS"),
    "mito_fato": (VERMELHO, VERDE, None),
    "antes_depois": (CINZA, AMARELO, "→"),
}


def comparacao(c, ctx):
    cena, t = ctx.cena, ctx.t
    ce, cd, meio = ESTILOS_COMP.get(cena.estilo, ESTILOS_COMP["versus"])
    lados = [(cena.esquerda, ce, 110, -1), (cena.direita, cd, 545, 1)]
    q = ctx.desde(lambda cc: bool(cc.vencedor) and cc.vencedor == cena.vencedor) if cena.vencedor else None
    kv = ease_out((t - (q + 0.3)) / 0.4) if q is not None else 0
    for i, (lado, col, x, sinal) in enumerate(lados):
        ap = ease_out((t - (ctx.entrada + 0.15 + i * 0.35)) / 0.45)
        if ap <= 0:
            continue
        perdeu = cena.vencedor and cena.vencedor != ("esquerda" if i == 0 else "direita")
        al = ap * (1 - 0.55 * kv if perdeu else 1)
        y = 660 + (1 - ap) * 30
        r = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, 400, 720), 30, 30)
        c.drawRRect(r, paint(PAINEL, al))
        c.drawRRect(r, paint(col, al, stroke=5 if not perdeu else 2))
        if cena.estilo == "mito_fato":
            marca = "MITO" if i == 0 else "FATO"
            pilula(c, marca, x + 200, y + 60, 30, col, FUNDO, al, peso="Black")
        if lado.objeto:
            desenhar_objeto(c, lado.objeto, x + 200, y + 230, 210, al, t - ctx.entrada - i * 0.35)
        y_tit = y + (380 if lado.objeto else 140)
        h_tit = E.linhas(c, E.quebrar_marcado(lado.titulo, 46, "Black", 350), y_tit, 46,
                         peso="Black", cor_=col, alpha=al, x=x + 200, maxw=360)
        if lado.texto:
            E.linhas(c, E.quebrar_marcado(lado.texto, 32, "SemiBold", 350), y_tit + h_tit + 22, 32,
                     peso="SemiBold", cor_=BRANCO, alpha=al, x=x + 200, maxw=360)
        if cena.estilo == "mito_fato" and ap > 0.9:
            cx, cy = x + 200, y + 650
            c.drawCircle(cx, cy, 34, paint(col, al))
            if i == 0:
                pp = paint(FUNDO, al, stroke=8)
                c.drawLine(cx - 13, cy - 13, cx + 13, cy + 13, pp)
                c.drawLine(cx + 13, cy - 13, cx - 13, cy + 13, pp)
            else:
                E.check(c, cx, cy, 34, al, col)
    if meio:
        am = ease_out((t - (ctx.entrada + 0.6)) / 0.3)
        c.drawCircle(527, 1020, 52 * back_out((t - (ctx.entrada + 0.6)) / 0.3) if am > 0 else 0, paint(AMARELO, am))
        texto(c, meio, 527, 1036, 40, FUNDO, am, "Black", "center")


# ---------------------------------------------------------------- linha do tempo

def linha_do_tempo(c, ctx):
    cena, t = ctx.cena, ctx.t
    ev = cena.eventos
    n = len(ev)
    y0, y1 = 680, 1420
    passo = (y1 - y0) / max(1, n - 1) if n > 1 else 0
    xl = 300
    ap = ease_out((t - ctx.entrada) / 0.4)
    trechos_dur = max(1.5, ctx.trecho(0).fim - max(ctx.trecho(0).inicio, ctx.entrada))
    kl = ease_io((t - ctx.entrada) / max(1.2, trechos_dur * 0.8))
    c.drawLine(xl, y0, xl, y0 + (y1 - y0) * kl, paint(PAINEL_LN, ap, stroke=6))
    q = ctx.desde(lambda cc: cc.destaque == cena.destaque) if cena.destaque >= 0 else None
    for i, e in enumerate(ev):
        y = y0 + i * passo
        k = back_out((t - (ctx.entrada + 0.2 + i * trechos_dur * 0.8 / max(1, n))) / 0.35)
        if k <= 0:
            continue
        em = i == cena.destaque and q is not None and t > q
        col = AMARELO if em else E.CIANO
        c.drawCircle(xl, y, 20 * k, paint(col, 1))
        c.drawCircle(xl, y, 9 * k, paint(FUNDO, 1))
        texto(c, e.ano, xl - 40, y + 16, 46, col, min(1, k), "Black", "right", maxw=190)
        E.linhas(c, E.quebrar_marcado(e.texto, 36, "Bold", 560), y - 22, 36, peso="Bold",
                 cor_=BRANCO if em or cena.destaque < 0 else CINZA, alpha=min(1, k), x=xl + 44, align="left", maxw=570)


# ---------------------------------------------------------------- passos / lista

def passos(c, ctx):
    cena, t = ctx.cena, ctx.t
    itens = cena.itens
    n = len(itens)
    h = min(170, 720 / max(1, n))
    y0 = 680 + (720 - n * h) / 2
    # quando cada item aparece: no trecho em que passou a existir, espalhado pela fala
    for i, it in enumerate(itens):
        q = ctx.desde(lambda cc, i=i: len(cc.itens) > i) or ctx.entrada
        novos = [j for j in range(n) if (ctx.desde(lambda cc, j=j: len(cc.itens) > j) or ctx.entrada) == q]
        k_ini = next((k for k in range(ctx.atual + 1) if ctx.inicio(k) == q), 0)
        tr = ctx.trecho(k_ini)
        dur = max(1.0, tr.fim - max(q, tr.inicio) - 0.4)
        ti = max(q, tr.inicio if q != ctx.entrada else ctx.entrada) + 0.2 + novos.index(i) * dur / max(1, len(novos))
        k = ease_out((t - ti) / 0.4)
        if k <= 0:
            continue
        y = y0 + i * h + (1 - k) * 20
        cx = 170
        if cena.marcador == "check":
            E.check(c, cx, y + h * 0.42, 34, k)
        elif cena.marcador == "x":
            c.drawCircle(cx, y + h * 0.42, 34, paint(VERMELHO, k))
            pp = paint(FUNDO, k, stroke=8)
            c.drawLine(cx - 13, y + h * 0.42 - 13, cx + 13, y + h * 0.42 + 13, pp)
            c.drawLine(cx + 13, y + h * 0.42 - 13, cx - 13, y + h * 0.42 + 13, pp)
        else:
            c.drawCircle(cx, y + h * 0.42, 38, paint(AMARELO, k))
            texto(c, str(i + 1), cx, y + h * 0.42 + 15, 40, FUNDO, k, "Black", "center")
        E.linhas(c, E.quebrar_marcado(it, 42, "Bold", 700), y + h * 0.42 - 28, 42, peso="Bold", alpha=k, x=240,
                 align="left", maxw=700)


# ---------------------------------------------------------------- citação

def citacao(c, ctx):
    cena, t = ctx.cena, ctx.t
    lt = t - ctx.entrada
    a, e = vis(t, ctx.entrada, None, 0.35)
    texto(c, "“", 120, 820, 300, AMARELO, a * 0.9, "Black")
    tam = 64 if len(E.sem_marcas(cena.texto)) < 90 else 52
    ls = E.quebrar_marcado(cena.texto, tam, "ExtraBold", 840)
    altura = E.linhas(c, ls, 760 + (1 - e) * 16, tam, peso="ExtraBold", alpha=a, x=130, align="left", maxw=840)
    yb = 760 + altura + 70
    k = ease_out((lt - 0.8) / 0.4)
    p = ctx.roteiro.pessoa(cena.pessoa) if cena.pessoa else None
    x_txt = 130
    if cena.pessoa:
        retrato(c, 190, yb + 50, 60, k, lt, p)
        x_txt = 280
    texto(c, f"— {cena.autor}", x_txt, yb + 40, 38, BRANCO, k, "Bold", maxw=700)
    if cena.detalhe:
        texto(c, cena.detalhe, x_txt, yb + 86, 30, CINZA, k, "SemiBold", maxw=700)
