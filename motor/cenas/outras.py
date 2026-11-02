"""Cenas: diagrama_causal, pessoa, lugar, mapa, texto_grande, chamada."""

import json
import math
from functools import lru_cache

import skia

from motor import estilo as E
from motor.estilo import (AMARELO, BRANCO, CINZA, FUNDO, PAINEL, PAINEL_LN, VERMELHO, W, back_out, cor,
                          ease_io, ease_out, paint, pilula, texto, vis)
from motor.ilustracoes.lugares import LUGARES
from motor.ilustracoes.pessoas import retrato


# ---------------------------------------------------------------- diagrama causal

POSICOES = {
    2: [(540, 830), (540, 1280)],
    3: [(300, 860), (780, 1100), (300, 1340)],
    4: [(540, 780), (260, 1060), (820, 1060), (540, 1340)],
}


def _caixa_no(rotulo):
    f = E.font("ExtraBold", 40)
    w = min(520, f.measureText(rotulo) + 70)
    return w, 96


def _no(c, cx, cy, rotulo, col, a):
    if a <= 0.002:
        return
    w, h = _caixa_no(rotulo)
    r = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(cx - w / 2, cy - h / 2, w, h), 26, 26)
    c.drawRRect(r, paint(PAINEL, a))
    c.drawRRect(r, paint(col, a, stroke=4))
    texto(c, rotulo, cx, cy + 14, 40, BRANCO, a, "ExtraBold", "center", maxw=w - 40)


def _borda(cx, cy, w, h, dx, dy):
    """Ponto na borda da caixa centrada em (cx, cy) na direção (dx, dy)."""
    if dx == 0 and dy == 0:
        return cx, cy
    s = min((w / 2 + 14) / abs(dx) if dx else 1e9, (h / 2 + 14) / abs(dy) if dy else 1e9)
    return cx + dx * s, cy + dy * s


def diagrama_causal(c, ctx):
    cena, t = ctx.cena, ctx.t
    t0 = ctx.entrada
    pos = {n.id: p for n, p in zip(cena.nos, POSICOES[len(cena.nos)])}
    a, e = vis(t, t0 - 0.05, None)
    if cena.subtitulo:
        E.linhas(c, [cena.subtitulo], 560 + (1 - e) * 16, 54, peso="Bold", alpha=a)
    for i, n in enumerate(cena.nos):
        k = ease_out((t - (t0 + 0.3 + i * 0.35)) / 0.35)
        _no(c, *pos[n.id], n.rotulo, cor(n.cor, i + 1), a * k)
    t_setas = t0 + 0.3 + len(cena.nos) * 0.35 + 0.2
    for j, s in enumerate(cena.setas):
        if s.de not in pos or s.para not in pos:
            continue
        (x0, y0), (x1, y1) = pos[s.de], pos[s.para]
        dx, dy = x1 - x0, y1 - y0
        lado = _caixa_no(next(n.rotulo for n in cena.nos if n.id == s.de))
        lado2 = _caixa_no(next(n.rotulo for n in cena.nos if n.id == s.para))
        ax, ay = _borda(x0, y0, *lado, dx, dy)
        bx, by = _borda(x1, y1, *lado2, -dx, -dy)
        k = ease_io((t - (t_setas + j * 0.4)) / 0.4)
        col = CINZA if s.tracejada else AMARELO
        E.seta(c, ax, ay, bx, by, col, a * (0.8 if s.tracejada else 1), k, tracejada=s.tracejada,
               w=5 if s.tracejada else 6)
        if k > 0.9:
            rot = s.rotulo or ("?" if s.tracejada else "")
            if rot:
                mx, my = (ax + bx) / 2, (ay + by) / 2
                ox = 35 if abs(dy) > abs(dx) else 0
                oy = -30 if abs(dx) >= abs(dy) else 20
                texto(c, rot, mx + ox, my + oy, 64 if rot == "?" else 34, CINZA, a, "Black")


# ---------------------------------------------------------------- pessoa

def _quebrar(s, f, maxw):
    palavras, linhas_, atual = s.split(), [], ""
    for p in palavras:
        teste = (atual + " " + p).strip()
        if f.measureText(teste) <= maxw or not atual:
            atual = teste
        else:
            linhas_.append(atual)
            atual = p
    if atual:
        linhas_.append(atual)
    return linhas_


def pessoa(c, ctx):
    cena, t = ctx.cena, ctx.t
    p = ctx.roteiro.pessoa(cena.pessoa)
    a, e = vis(t, ctx.entrada + 0.15, None, 0.35)
    if a <= 0.002:
        return
    dy = (1 - e) * 24
    retrato(c, W / 2, 820 + dy, 230, a, ctx.lt, p)
    nome = p.nome if p else cena.pessoa
    texto(c, nome, W / 2, 1150 + dy, 60, BRANCO, a, "ExtraBold", "center", maxw=900)
    sub = ", ".join(x for x in [p.descricao if p else "", f"({p.datas})" if p and p.datas else ""] if x)
    sub = sub.replace(", (", " (")
    texto(c, sub, W / 2, 1210 + dy, 34, CINZA, a, "SemiBold", "center", maxw=900)
    if p and p.feito:
        k = ease_out((t - (ctx.entrada + 0.9)) / 0.4)
        f = E.font("Bold", 38)
        for i, ln in enumerate(_quebrar(p.feito, f, 860)[:2]):
            texto(c, ln, W / 2, 1290 + i * 50 + dy, 38, AMARELO, a * k, "Bold", "center")


# ---------------------------------------------------------------- lugar e mapa

def lugar(c, ctx):
    cena, t = ctx.cena, ctx.t
    desenho = LUGARES.get(cena.lugar.lower())
    if desenho is None:   # sem ilustração: cai no mapa
        nome = cena.lugar if " " in cena.lugar or cena.lugar[:1].isupper() else \
            " ".join(p if p in ("de", "da", "do", "das", "dos") else p.capitalize()
                     for p in cena.lugar.replace("-", " ").replace("_", " ").split())
        return _globo(c, ctx, nome, cena.lat, cena.lon, cena.legenda)
    a = vis(t, ctx.entrada, None, 0.3)[0]
    lt = t - ctx.entrada
    X, Y, PW, PH = 120, 640, 840, 790
    rr = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(X, Y, PW, PH), 34, 34)
    c.save()
    c.clipRRect(rr, doAntiAlias=True)
    if a < 0.999:
        c.saveLayerAlpha(None, int(255 * a))
    desenho(c, X, Y, PW, PH, lt)
    if a < 0.999:
        c.restore()
    c.restore()
    c.drawRRect(rr, paint(PAINEL_LN, a, stroke=2))
    k = ease_out((lt - 0.9) / 0.4)
    if k > 0 and cena.legenda:
        pilula(c, cena.legenda, W / 2, Y + PH - 46, 32, FUNDO, AMARELO, a * k, maxw=800)


@lru_cache(maxsize=None)
def _continentes():
    return json.loads((E.PASTA / "dados" / "continentes.json").read_text())["aneis"]


def _globo(c, ctx, nome, lat, lon, legenda):
    t = ctx.t
    lt = t - ctx.entrada
    a = vis(t, ctx.entrada, None, 0.3)[0]
    cx, cy, R = W / 2, 1010, 380
    giro = 1 - ease_io(lt / 1.4)
    lon0 = (lon if lon is not None else -30) - 50 * giro
    lat0 = (lat if lat is not None else 10) * (0.85 + 0.15 * (1 - giro))
    la0, lo0 = math.radians(lat0), math.radians(lon0)

    def proj(lo, la):
        la, lo = math.radians(la), math.radians(lo)
        cosc = math.sin(la0) * math.sin(la) + math.cos(la0) * math.cos(la) * math.cos(lo - lo0)
        x = math.cos(la) * math.sin(lo - lo0)
        y = math.cos(la0) * math.sin(la) - math.sin(la0) * math.cos(la) * math.cos(lo - lo0)
        if cosc < 0:   # lado de trás: encosta na borda
            n = math.hypot(x, y) or 1
            x, y = x / n, y / n
        return cx + x * R, cy - y * R, cosc >= 0

    c.drawCircle(cx, cy, R + 14, paint(AMARELO, a * 0.12, blur=30))
    c.drawCircle(cx, cy, R, paint(E.hx("13203A"), a))
    clip = skia.Path()
    clip.addCircle(cx, cy, R)
    c.save()
    c.clipPath(clip, doAntiAlias=True)
    grade = paint(E.hx("22314F"), a, stroke=1.5)
    for la in range(-60, 90, 30):
        path, ok = skia.Path(), False
        for lo in range(-180, 181, 5):
            x, y, vis_ = proj(lo, la)
            if vis_:
                (path.lineTo if ok else path.moveTo)(x, y)
            ok = vis_
        c.drawPath(path, grade)
    for lo in range(-180, 180, 30):
        path, ok = skia.Path(), False
        for la in range(-90, 91, 5):
            x, y, vis_ = proj(lo, la)
            if vis_:
                (path.lineTo if ok else path.moveTo)(x, y)
            ok = vis_
        c.drawPath(path, grade)
    terra, borda = paint(E.hx("2E3C5F"), a), paint(CINZA, a * 0.6, stroke=1.5)
    for anel in _continentes():
        pts = [proj(lo, la) for lo, la in anel]
        if not any(v for _, _, v in pts):
            continue
        path = skia.Path()
        path.moveTo(pts[0][0], pts[0][1])
        for x, y, _ in pts[1:]:
            path.lineTo(x, y)
        path.close()
        c.drawPath(path, terra)
        c.drawPath(path, borda)
    c.restore()
    c.drawCircle(cx, cy, R, paint(PAINEL_LN, a, stroke=3))
    if lat is not None and lon is not None:
        pk = ease_out((lt - 1.3) / 0.4)
        if pk > 0:
            x, y, _ = proj(lon, lat)
            pulso = (lt * 1.2) % 1.0
            c.drawCircle(x, y, 12 + 34 * pulso, paint(VERMELHO, (1 - pulso) * 0.8 * pk, stroke=4))
            c.drawCircle(x, y, 14 * back_out(pk), paint(VERMELHO, pk))
            c.drawCircle(x, y, 5 * pk, paint(BRANCO, pk))
            pilula(c, nome, min(max(x, 280), 800), y - 70, 34, FUNDO, BRANCO, pk, peso="ExtraBold", maxw=700)
    elif a > 0:
        pilula(c, nome, W / 2, cy, 40, FUNDO, BRANCO, a, peso="ExtraBold", maxw=800)
    k = ease_out((lt - 1.6) / 0.4)
    if legenda and k > 0:
        pilula(c, legenda, W / 2, cy + R + 50, 32, FUNDO, AMARELO, a * k, maxw=800)


def mapa(c, ctx):
    cena = ctx.cena
    _globo(c, ctx, cena.lugar, cena.lat, cena.lon, cena.legenda)


# ---------------------------------------------------------------- texto grande e chamada

def _quebrar_marcado(s, tamanho, peso, maxw):
    return E.quebrar_marcado(s, tamanho, peso, maxw)


def texto_grande(c, ctx):
    cena, t = ctx.cena, ctx.t
    a, e = vis(t, ctx.entrada - 0.05, None, 0.3)
    tamanho = 96 if len(E.sem_marcas(cena.texto)) < 40 else 80
    ls = _quebrar_marcado(cena.texto, tamanho, "Black", 900)
    altura = len(ls) * tamanho * 1.17
    topo = 960 - altura / 2 + (1 - e) * 20
    # traço decorativo acima da frase
    k = ease_out((t - ctx.entrada) / 0.5)
    E.barra(c, W / 2 - 60 * k, topo - 50, 120 * k, 10, AMARELO, a, r=5)
    E.linhas(c, ls, topo, tamanho, peso="Black", alpha=a)
    if cena.subtitulo:
        k = ease_out((t - (ctx.entrada + 0.8)) / 0.4)
        E.linhas(c, _quebrar_marcado(cena.subtitulo, 44, "SemiBold", 860), topo + altura + 50, 44,
                 peso="SemiBold", cor_=CINZA, alpha=a * k)


def chamada(c, ctx):
    cena, t = ctx.cena, ctx.t
    a, e = vis(t, ctx.entrada - 0.05, None, 0.3)
    lt = t - ctx.entrada
    # mini gráfico animado como ícone
    for i, h in enumerate([0.45, 0.7, 0.55, 0.9, 1.0]):
        k = ease_out((lt - i * 0.08) / 0.4)
        hh = 220 * h * k * (0.92 + 0.08 * math.sin(lt * 3 + i))
        E.barra(c, 380 + i * 66, 900 - hh, 48, hh, AMARELO if i == 4 else E.CIANO, a * (1 if i == 4 else 0.6),
                r=10)
    c.drawLine(350, 902, 730, 902, paint(PAINEL_LN, a, stroke=4))
    pilula(c, cena.texto, W / 2, 1040 + (1 - e) * 20, 38, AMARELO, FUNDO, a, peso="ExtraBold", h=96)
