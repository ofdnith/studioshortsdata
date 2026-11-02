"""Cenas de gráficos: barras, barras_pareadas, barra_empilhada, tabela."""

import skia

from motor import estilo as E
from motor.estilo import (AMARELO, BRANCO, CINZA, FUNDO, PAINEL, PAINEL_LN, VERDE, W, barra, check,
                          cor, ease_io, ease_out, fmt_num, pilula, texto)


def _valor(v, unidade, casas=None):
    s = fmt_num(v, casas)
    return f"{s}{unidade}" if unidade in ("%", "×", "x") else (f"{s} {unidade}" if unidade else s)


def _apagar(ctx, alvo_ok) -> float:
    """0..1: quanto os elementos fora do foco devem apagar (a partir do trecho do foco)."""
    q = ctx.desde(alvo_ok)
    return 0.0 if q is None else ease_io((ctx.t - (q + 0.1)) / 0.3)


# ---------------------------------------------------------------- barras

def barras(c, ctx):
    cena, t = ctx.cena, ctx.t
    n = len(cena.dados)
    t0 = ctx.entrada
    t_ini, t_fim = ctx.trecho(0).inicio, ctx.trecho(0).fim
    base, maxh = 1400, 680
    vmax = max(d.valor for d in cena.dados) or 1
    escala = maxh / vmax
    slot = 840 / n
    bw = min(280, slot * 0.66)
    passo = min(2.6, max(0.4, (t_fim - t_ini - 1.0) / n))
    tem_destaque = cena.destaque is not None
    kd = _apagar(ctx, lambda cc: cc.destaque is not None and cc.destaque == cena.destaque) if tem_destaque else 0
    for i, d in enumerate(cena.dados):
        cx = 120 + slot * (i + 0.5)
        col = cor(d.cor, i)
        ap = ease_out((t - (t0 + i * 0.15)) / 0.4)
        if ap <= 0:
            continue
        al = ap * (1 - 0.65 * kd if tem_destaque and d.rotulo != cena.destaque else 1)
        grow = ease_io((t - (t0 + 0.05 + i * 0.2)) / 0.6)
        # contagem: a primeira junto da entrada, as outras espalhadas pela fala
        inicio_cnt = (t0 + 0.3) if i == 0 else (max(t0, t_ini) + 0.3 + i * passo)
        cnt = ease_io((t - inicio_cnt) / 0.6)
        hgt = d.valor * escala * grow
        barra(c, cx - bw / 2, base - hgt, bw, hgt, col, al, r=18)
        c.drawLine(cx - bw / 2 - 30, base, cx + bw / 2 + 30, base, E.paint(PAINEL_LN, al, stroke=3))
        texto(c, d.rotulo, cx, base + 62, 44, CINZA, al, "Bold", "center", maxw=slot - 10)
        if grow > 0:
            lab = "?" if cnt <= 0 else _valor(d.valor * cnt if cnt < 1 else d.valor, cena.unidade,
                                               cena.casas if cnt >= 1 else 0)
            texto(c, lab, cx, base - hgt - 26, 96 if n <= 3 else 72, col if cnt > 0 else CINZA,
                  al * grow, "Black", "center", maxw=slot)


# ---------------------------------------------------------------- barras pareadas

def barras_pareadas(c, ctx):
    cena, t = ctx.cena, ctx.t
    ns, ng = len(cena.series), len(cena.grupos)
    t0 = ctx.entrada
    row_h = min(128, 780 / ng)
    y0 = 640
    bx0, bmax = 210, 620
    vmax = 100 if cena.unidade == "%" else max(max(g.valores) for g in cena.grupos) or 1
    bh = (row_h - 24) / ns - 10
    kf = _apagar(ctx, lambda cc: cc.destaque is not None and cc.destaque == cena.destaque) if cena.destaque else 0
    marca_desde = ctx.desde(lambda cc: cc.marcar_vencedor == cena.marcar_vencedor) if cena.marcar_vencedor else None
    i_marca = next((k for k, s in enumerate(cena.series) if s.nome == cena.marcar_vencedor), None)
    for i, g in enumerate(cena.grupos):
        y = y0 + i * row_h
        ap = ease_out((t - (t0 + 0.2 + i * 0.16)) / 0.4)
        if ap <= 0:
            continue
        al = ap * (1 - 0.7 * kf if cena.destaque and g.rotulo != cena.destaque else 1)
        texto(c, g.rotulo, 120, y + row_h / 2 + 14 + 8, min(64, row_h * 0.5) if len(g.rotulo) <= 2 else 30,
              BRANCO, al, "Black", "center", maxw=170)
        gr = ease_io((t - (t0 + 0.35 + i * 0.16)) / 0.6)
        for j, s in enumerate(cena.series):
            v = g.valores[j] if j < len(g.valores) else 0
            col = cor(s.cor, j)
            yy = y + 14 + j * (bh + 10)
            bw = bmax * v / vmax * gr
            barra(c, bx0, yy, max(bw, 6), bh, col, al, r=10)
            texto(c, _valor(v * gr, cena.unidade, 0), bx0 + max(bw, 6) + 14, yy + bh * 0.5 + 12,
                  min(34, bh * 0.8), col, al, "Bold")
        if marca_desde is not None and i_marca is not None:
            vals = g.valores
            if vals[i_marca] == max(vals) and vals.count(max(vals)) == 1:
                check(c, 990, y + row_h / 2 - 2, 26, al * ease_out((t - (marca_desde + 0.3 + i * 0.12)) / 0.3))
    # legenda
    la = ease_out((t - t0 - 0.5) / 0.4)
    if la > 0:
        larg = [E.font("SemiBold", 34).measureText(s.nome) + 70 for s in cena.series]
        x = W / 2 - sum(larg) / 2
        ly = min(1462, y0 + ng * row_h + 60)
        for j, s in enumerate(cena.series):
            c.drawCircle(x + 13, ly - 12, 13, E.paint(cor(s.cor, j), la))
            texto(c, s.nome, x + 36, ly, 34, CINZA, la, "SemiBold")
            x += larg[j]


# ---------------------------------------------------------------- barra empilhada

def barra_empilhada(c, ctx):
    cena, t = ctx.cena, ctx.t
    nb = len(cena.barras)
    ys, h = {1: ([880], 170), 2: ([780, 1100], 150), 3: ([700, 960, 1220], 130)}[nb]
    x0, wfull = 120, 840
    destaque = cena.destaque
    kd = _apagar(ctx, lambda cc: cc.destaque is not None and cc.destaque == destaque) if destaque else 0
    for bi, b in enumerate(cena.barras):
        y = ys[bi]
        ap = ease_out((t - (ctx.entrada + 0.4 + bi * 0.3)) / 0.5)
        if ap <= 0:
            continue
        texto(c, b.rotulo, x0, y - 22, 46, cor(b.cor, bi), ap, "ExtraBold")
        soma = sum(p.valor for p in b.partes) or 1
        x = x0
        for pi, p in enumerate(b.partes):
            w = wfull * p.valor / soma
            col = cor(p.cor, pi + 2)
            dim = 1.0
            if destaque and kd > 0 and destaque.barra == b.rotulo and p.rotulo not in destaque.partes:
                dim = 1 - 0.65 * kd
            elif destaque and kd > 0 and destaque.barra != b.rotulo:
                dim = 1 - 0.3 * kd
            cresce = ease_io((t - (ctx.entrada + 0.5 + bi * 0.3 + pi * 0.06)) / 0.4)
            barra(c, x + 2, y, (w - 4) * cresce, h, col, ap * dim * 0.92, r=10)
            if w > 50 and cresce > 0.9:
                texto(c, p.rotulo, x + w / 2, y + h / 2 + 16, 44 if len(p.rotulo) <= 3 else 32, FUNDO,
                      ap * dim, "Black", "center", maxw=w - 10)
            x += w
        if destaque and destaque.barra == b.rotulo and destaque.texto and kd > 0:
            xs, acum = [], x0
            for p in b.partes:
                w = wfull * p.valor / soma
                if p.rotulo in destaque.partes:
                    xs += [acum, acum + w]
                acum += w
            if xs:
                cx = (min(xs) + max(xs)) / 2
                cx = min(max(cx, 300), 780)
                pc = cor(next(p.cor for p in b.partes if p.rotulo in destaque.partes), 2)
                pilula(c, destaque.texto, cx, y + h + 35, 34, E.misturar(FUNDO, pc, 0.18), pc, kd)
    la = ease_out((t - (ctx.entrada + 1.4)) / 0.4)
    if la > 0 and cena.legenda:
        y_leg = ys[-1] + h + (110 if destaque else 80)
        for i, lg in enumerate(cena.legenda):
            yy = min(y_leg + i * 56, 1480 - (len(cena.legenda) - 1 - i) * 56)
            barra(c, 150, yy - 28, 34, 34, cor(lg.cor, i), la, r=8)
            texto(c, lg.texto, 200, yy, 36, CINZA, la, "SemiBold", maxw=760)


# ---------------------------------------------------------------- tabela

def tabela(c, ctx):
    cena, t = ctx.cena, ctx.t
    nc, nl = len(cena.colunas), len(cena.linhas)
    x0 = 230
    cw = min(250, 750 / nc)
    rh = min(150, 640 / nl)
    y0 = 650
    ap = ease_out((t - (ctx.entrada + 0.3)) / 0.4)

    # quando cada coluna aparece: no trecho em que passou a existir, espalhadas pela fala
    t_col = []
    for j in range(nc):
        q = ctx.desde(lambda cc, j=j: len(cc.colunas) > j)
        k_ini = next(k for k in range(ctx.atual + 1) if ctx.inicio(k) == q) if q is not None else 0
        novas = [jj for jj in range(nc)
                 if ctx.desde(lambda cc, jj=jj: len(cc.colunas) > jj) == q]
        tr = ctx.trecho(k_ini)
        dur = max(0.8, tr.fim - max(q, tr.inicio) - 0.5)
        pos = novas.index(j) if j in novas else 0
        base = (q + 0.6) if k_ini == 0 and q < tr.inicio else max(q, tr.inicio) + 0.5
        t_col.append(base + pos * dur * 0.7 / max(1, len(novas)))

    for j, nome in enumerate(cena.colunas):
        total = cena.coluna_total and j == nc - 1
        a = ap * ease_out((t - t_col[j] + 0.3) / 0.4)
        texto(c, nome, x0 + cw * j + cw / 2, y0 + 50, 38, AMARELO if total else CINZA, a, "Bold", "center",
              maxw=cw - 10)
    for i, ln in enumerate(cena.linhas):
        y = y0 + 80 + i * rh
        texto(c, ln.rotulo, 150, y + rh * 0.65, 72 if len(ln.rotulo) <= 2 else 34, BRANCO, ap, "Black",
              "center", maxw=200)
        for j in range(nc):
            k = ease_out((t - t_col[j]) / 0.35)
            if k <= 0 or j >= len(ln.valores):
                continue
            v = ln.valores[j]
            coluna = [l.valores[j] for l in cena.linhas if j < len(l.valores)]
            melhor = max(coluna) if cena.vencedor == "maior" else min(coluna)
            vence = cena.vencedor is not None and v == melhor and coluna.count(melhor) == 1
            total = cena.coluna_total and j == nc - 1
            cv = (AMARELO if total else VERDE) if vence else PAINEL_LN
            x = x0 + cw * j + 12
            r = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y + 10, cw - 24, rh - 24), 22, 22)
            c.drawRRect(r, E.paint(PAINEL, k))
            c.drawRRect(r, E.paint(cv, k, stroke=4 if vence else 2))
            texto(c, _valor(v, cena.unidade), x + (cw - 24) / 2, y + rh * 0.65, min(64, rh * 0.45),
                  ((AMARELO if total else VERDE) if vence else CINZA), k, "Black", "center", maxw=cw - 40)
