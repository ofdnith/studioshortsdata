"""Biblioteca de objetos desenhados por código (estilo flat, cores da identidade).

Cada objeto desenha num quadrado de -1..1 (centro 0,0); `desenhar_objeto` posiciona e escala.
`lt` é o tempo desde a entrada (para animações sutis). Para adicionar um objeto: escreva
`def _nome(c, a, lt)` e registre em OBJETOS.
"""

import math

import skia

from motor.estilo import (AMARELO, BRANCO, CIANO, CINZA, FUNDO, PAINEL, PAINEL_LN, ROXO, VERDE, VERMELHO,
                          back_out, clamp, ease_io, ease_out, hx, misturar, paint)

OURO, OURO_ESC = AMARELO, hx("D99A1E")
ROSA = hx("FF8FB1")


def _p(cor, a, stroke=None):
    return paint(cor, a, stroke=stroke)


def _rr(c, x, y, w, h, r, cor, a, stroke=None):
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), r, r), _p(cor, a, stroke))


def _caminho(pts, fechar=True):
    p = skia.Path()
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    if fechar:
        p.close()
    return p


# ---------------------------------------------------------------- objetos

def _aviao(c, a, lt):
    c.translate(0, math.sin(lt * 2) * 0.03)
    cor, esc = hx("C9D3E6"), hx("8FA0BC")
    asa = _caminho([(-0.15, 0.02), (0.25, 0.02), (-0.05, 0.75), (-0.32, 0.75)])
    c.drawPath(asa, _p(esc, a))
    _rr(c, -0.95, -0.16, 1.85, 0.32, 0.16, cor, a)
    c.drawPath(_caminho([(0.65, -0.14), (0.95, -0.55), (1.0, -0.55), (0.9, -0.1)]), _p(esc, a))
    c.drawPath(_caminho([(0.6, 0.0), (0.95, 0.0), (1.0, 0.25), (0.85, 0.25)]), _p(esc, a))
    c.drawPath(_caminho([(-0.1, -0.02), (0.2, -0.02), (0.0, -0.5), (-0.22, -0.5)]), _p(cor, a))
    for i in range(6):
        c.drawCircle(-0.55 + i * 0.18, -0.03, 0.045, _p(FUNDO, a))
    _rr(c, -0.95, -0.12, 0.25, 0.14, 0.07, CIANO, a)


def _dado(c, a, lt):
    k = ease_out(lt / 0.7)
    c.rotate((1 - k) * 200)
    _rr(c, -0.8, -0.8, 1.6, 1.6, 0.3, BRANCO, a)
    _rr(c, -0.8, -0.8, 1.6, 1.6, 0.3, hx("C9D3E6"), a, stroke=0.06)
    for x, y in [(-0.42, -0.42), (0.42, -0.42), (-0.42, 0), (0.42, 0), (-0.42, 0.42), (0.42, 0.42)]:
        c.drawCircle(x, y, 0.13, _p(FUNDO, a))


def _moeda(c, a, lt):
    giro = math.cos(lt * 3.2)
    c.scale(max(0.08, abs(giro)), 1)
    c.drawCircle(0, 0, 0.85, _p(OURO_ESC, a))
    c.drawCircle(0, -0.04, 0.8, _p(OURO, a))
    c.drawCircle(0, -0.04, 0.62, _p(OURO_ESC, a, stroke=0.06))
    c.save()
    c.scale(0.01, 0.01)   # texto em tamanho normal (fontes minúsculas renderizam mal)
    from motor.estilo import font
    f = font("Black", 95)
    txt = "$" if giro >= 0 else "R$"
    w = f.measureText(txt)
    c.drawString(txt, -w / 2, 28, f, _p(OURO_ESC, a))
    c.restore()


def _lupa(c, a, lt):
    c.translate(math.sin(lt * 1.6) * 0.12, math.cos(lt * 1.3) * 0.06)
    cabo = _p(hx("8FA0BC"), a, stroke=0.24)
    c.drawLine(0.35, 0.35, 0.85, 0.85, cabo)
    c.drawCircle(-0.15, -0.15, 0.62, _p(misturar(FUNDO, CIANO, 0.25), a))
    c.drawCircle(-0.15, -0.15, 0.62, _p(hx("C9D3E6"), a, stroke=0.14))
    arco = skia.Path()
    arco.addArc(skia.Rect.MakeLTRB(-0.6, -0.6, 0.3, 0.3), 200, 60)
    c.drawPath(arco, _p(BRANCO, a * 0.7, stroke=0.07))


def _balanca(c, a, lt):
    inc = math.sin(min(lt, 1.5) / 1.5 * math.pi / 2) * 14
    c.drawRect(skia.Rect.MakeLTRB(-0.05, -0.55, 0.05, 0.75), _p(hx("8FA0BC"), a))
    _rr(c, -0.45, 0.72, 0.9, 0.14, 0.07, hx("8FA0BC"), a)
    c.drawCircle(0, -0.6, 0.09, _p(OURO, a))
    c.save()
    c.translate(0, -0.55)
    c.rotate(inc)
    c.drawLine(-0.8, 0, 0.8, 0, _p(hx("C9D3E6"), a, stroke=0.07))
    for lado, cor in ((-0.8, CIANO), (0.8, VERMELHO)):
        c.save()
        c.translate(lado, 0)
        c.rotate(-inc)
        c.drawLine(0, 0, -0.25, 0.5, _p(CINZA, a, stroke=0.025))
        c.drawLine(0, 0, 0.25, 0.5, _p(CINZA, a, stroke=0.025))
        arco = skia.Path()
        arco.moveTo(-0.32, 0.5)
        arco.quadTo(0, 0.75, 0.32, 0.5)
        arco.close()
        c.drawPath(arco, _p(cor, a))
        c.restore()
    c.restore()


def _alvo(c, a, lt):
    for r, cor in ((0.9, VERMELHO), (0.68, BRANCO), (0.46, VERMELHO), (0.24, BRANCO), (0.1, VERMELHO)):
        c.drawCircle(0, 0, r, _p(cor, a))
    k = ease_out((lt - 0.4) / 0.35)
    if k > 0:
        x = 1.6 * (1 - k)
        c.drawLine(x + 0.02, -x * 0.6, x + 0.75, -x * 0.6 - 0.45, _p(hx("C9D3E6"), a, stroke=0.07))
        c.drawPath(_caminho([(x + 0.65, -x * 0.6 - 0.5), (x + 0.95, -x * 0.6 - 0.62),
                             (x + 0.8, -x * 0.6 - 0.36)]), _p(OURO, a))


def _cerebro(c, a, lt):
    pulso = 1 + 0.03 * math.sin(lt * 3)
    c.scale(pulso, pulso)
    cor, linha = ROSA, misturar(ROSA, FUNDO, 0.35)
    for x, y, r in [(-0.4, -0.25, 0.42), (0.0, -0.4, 0.42), (0.4, -0.25, 0.42), (-0.45, 0.2, 0.38),
                    (0.45, 0.2, 0.38), (0.0, 0.15, 0.45)]:
        c.drawCircle(x, y, r, _p(cor, a))
    pl = _p(linha, a, stroke=0.05)
    c.drawLine(0, -0.75, 0, 0.5, pl)
    for pts in [[(-0.7, -0.3), (-0.45, -0.1), (-0.6, 0.15)], [(-0.3, -0.6), (-0.2, -0.3), (-0.35, -0.05)],
                [(0.7, -0.3), (0.45, -0.1), (0.6, 0.15)], [(0.3, -0.6), (0.2, -0.3), (0.35, -0.05)],
                [(-0.3, 0.35), (-0.15, 0.2), (-0.05, 0.4)], [(0.3, 0.35), (0.15, 0.2), (0.05, 0.4)]]:
        p = skia.Path()
        p.moveTo(*pts[0])
        p.quadTo(*pts[1], *pts[2])
        c.drawPath(p, pl)
    c.drawRect(skia.Rect.MakeLTRB(-0.1, 0.5, 0.1, 0.8), _p(misturar(ROSA, FUNDO, 0.2), a))


def _ampulheta(c, a, lt):
    k = clamp(lt / 4)
    moldura = hx("8FA0BC")
    _rr(c, -0.6, -0.9, 1.2, 0.12, 0.05, moldura, a)
    _rr(c, -0.6, 0.78, 1.2, 0.12, 0.05, moldura, a)
    vidro = _caminho([(-0.45, -0.78), (0.45, -0.78), (0.06, 0), (0.45, 0.78), (-0.45, 0.78), (-0.06, 0)])
    c.drawPath(vidro, _p(misturar(FUNDO, CIANO, 0.2), a))
    c.save()
    c.clipPath(vidro, doAntiAlias=True)
    c.drawRect(skia.Rect.MakeLTRB(-0.5, -0.78 + 0.7 * k, 0.5, 0), _p(OURO, a))
    c.drawRect(skia.Rect.MakeLTRB(-0.5, 0.78 - 0.7 * k, 0.5, 0.78), _p(OURO, a))
    c.restore()
    if k < 1:
        c.drawLine(0, 0, 0, 0.78, _p(OURO, a, stroke=0.03))
    c.drawPath(vidro, _p(hx("C9D3E6"), a, stroke=0.05))


def _termometro(c, a, lt):
    k = ease_io(lt / 1.6)
    _rr(c, -0.18, -0.9, 0.36, 1.35, 0.18, BRANCO, a)
    c.drawCircle(0, 0.62, 0.32, _p(BRANCO, a))
    c.drawCircle(0, 0.62, 0.23, _p(VERMELHO, a))
    topo = 0.4 - 1.15 * k
    _rr(c, -0.08, topo, 0.16, 0.6 - topo, 0.08, VERMELHO, a)
    for i in range(6):
        y = -0.75 + i * 0.22
        c.drawLine(0.22, y, 0.38, y, _p(CINZA, a, stroke=0.035))


def _trofeu(c, a, lt):
    c.drawCircle(-0.5, -0.35, 0.3, _p(OURO_ESC, a, stroke=0.1))
    c.drawCircle(0.5, -0.35, 0.3, _p(OURO_ESC, a, stroke=0.1))
    taca = skia.Path()
    taca.moveTo(-0.55, -0.75)
    taca.lineTo(0.55, -0.75)
    taca.quadTo(0.55, 0.1, 0, 0.2)
    taca.quadTo(-0.55, 0.1, -0.55, -0.75)
    c.drawPath(taca, _p(OURO, a))
    c.drawRect(skia.Rect.MakeLTRB(-0.09, 0.2, 0.09, 0.5), _p(OURO_ESC, a))
    _rr(c, -0.4, 0.5, 0.8, 0.14, 0.04, OURO, a)
    _rr(c, -0.5, 0.64, 1.0, 0.2, 0.05, hx("8FA0BC"), a)
    brilho = 0.5 + 0.5 * math.sin(lt * 2.5)
    c.drawLine(-0.32, -0.6, -0.25, -0.2, _p(BRANCO, a * 0.5 * brilho, stroke=0.07))


def _cadeado(c, a, lt):
    abre = ease_out((lt - 0.8) / 0.4) * 0.25
    c.save()
    c.translate(0, -abre)
    arco = skia.Path()
    arco.addArc(skia.Rect.MakeLTRB(-0.42, -0.85, 0.42, 0.0), 180, 180)
    c.drawPath(arco, _p(hx("C9D3E6"), a, stroke=0.16))
    c.drawLine(-0.42, -0.42, -0.42, -0.05, _p(hx("C9D3E6"), a, stroke=0.16))
    c.drawLine(0.42, -0.42, 0.42, -0.05 + abre, _p(hx("C9D3E6"), a, stroke=0.16))
    c.restore()
    _rr(c, -0.65, -0.1, 1.3, 1.0, 0.16, OURO, a)
    c.drawCircle(0, 0.3, 0.13, _p(FUNDO, a))
    c.drawRect(skia.Rect.MakeLTRB(-0.05, 0.3, 0.05, 0.58), _p(FUNDO, a))


def _lampada(c, a, lt):
    brilho = 0.6 + 0.4 * math.sin(lt * 3)
    c.drawCircle(0, -0.25, 0.75, _p(OURO, a * 0.18 * brilho))
    for i in range(8):
        ang = math.radians(-180 + i * 25.7)
        r0, r1 = 0.78, 0.98
        c.drawLine(math.cos(ang) * r0, -0.25 + math.sin(ang) * r0, math.cos(ang) * r1,
                   -0.25 + math.sin(ang) * r1, _p(OURO, a * brilho, stroke=0.06))
    c.drawCircle(0, -0.25, 0.55, _p(OURO, a))
    c.drawPath(_caminho([(-0.3, 0.15), (0.3, 0.15), (0.22, 0.45), (-0.22, 0.45)]), _p(OURO, a))
    for i in range(3):
        _rr(c, -0.24, 0.47 + i * 0.12, 0.48, 0.09, 0.04, hx("8FA0BC"), a)
    c.drawLine(-0.12, -0.2, 0.0, 0.1, _p(OURO_ESC, a, stroke=0.04))
    c.drawLine(0.12, -0.2, 0.0, 0.1, _p(OURO_ESC, a, stroke=0.04))


def _computador(c, a, lt):
    _rr(c, -0.95, -0.75, 1.9, 1.2, 0.08, hx("C9D3E6"), a)
    _rr(c, -0.87, -0.67, 1.74, 1.02, 0.04, PAINEL, a)
    for i, h in enumerate([0.35, 0.55, 0.45, 0.7, 0.85]):
        k = ease_out((lt - 0.2 - i * 0.1) / 0.4)
        hh = h * 0.8 * k
        _rr(c, -0.7 + i * 0.3, 0.25 - hh, 0.2, hh, 0.03, AMARELO if i == 4 else CIANO, a)
    c.drawPath(_caminho([(-0.15, 0.45), (0.15, 0.45), (0.25, 0.75), (-0.25, 0.75)]), _p(hx("8FA0BC"), a))
    _rr(c, -0.5, 0.72, 1.0, 0.1, 0.04, hx("8FA0BC"), a)


def _documento(c, a, lt):
    folha = _caminho([(-0.65, -0.9), (0.35, -0.9), (0.65, -0.6), (0.65, 0.9), (-0.65, 0.9)])
    c.drawPath(folha, _p(BRANCO, a))
    c.drawPath(_caminho([(0.35, -0.9), (0.35, -0.6), (0.65, -0.6)]), _p(hx("C9D3E6"), a))
    for i in range(7):
        k = ease_out((lt - i * 0.08) / 0.3)
        w = (0.95 if i % 3 else 0.6) * k
        c.drawLine(-0.45, -0.5 + i * 0.2, -0.45 + w, -0.5 + i * 0.2, _p(CINZA, a, stroke=0.06))
    c.drawCircle(0.35, 0.6, 0.18, _p(VERMELHO, a))


def _crescimento(c, a, lt):
    for i, h in enumerate([0.4, 0.6, 0.85, 1.25]):
        k = ease_out((lt - i * 0.12) / 0.4)
        _rr(c, -0.85 + i * 0.45, 0.85 - h * k, 0.32, h * k, 0.05, CIANO, a)
    k = ease_io((lt - 0.4) / 0.8)
    p = skia.Path()
    pts = [(-0.85, 0.3), (-0.35, 0.05), (0.05, 0.15), (0.75, -0.75)]
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    medida = skia.PathMeasure(p, False)
    seg = skia.Path()
    medida.getSegment(0, medida.getLength() * k, seg, True)
    c.drawPath(seg, _p(VERDE, a, stroke=0.1))
    if k > 0.95:
        c.drawPath(_caminho([(0.88, -0.9), (0.55, -0.82), (0.8, -0.58)]), _p(VERDE, a))


def _coracao(c, a, lt):
    s = 1 + 0.06 * max(0, math.sin(lt * 6))
    c.save()
    c.scale(s, s)
    p = skia.Path()
    p.moveTo(0, 0.75)
    p.cubicTo(-1.1, 0.0, -0.6, -0.95, 0, -0.4)
    p.cubicTo(0.6, -0.95, 1.1, 0.0, 0, 0.75)
    c.drawPath(p, _p(VERMELHO, a))
    c.restore()
    ecg = _caminho([(-0.95, 0.0), (-0.35, 0.0), (-0.2, -0.35), (0.0, 0.35), (0.15, -0.15), (0.25, 0.0),
                    (0.95, 0.0)], fechar=False)
    c.drawPath(ecg, _p(BRANCO, a, stroke=0.07))


def _pessoas(c, a, lt):
    for i, (x, cor) in enumerate([(-0.55, CIANO), (0, AMARELO), (0.55, ROXO)]):
        k = back_out((lt - i * 0.12) / 0.4)
        if k <= 0:
            continue
        c.save()
        c.translate(x, 0.1)
        c.scale(k, k)
        c.drawCircle(0, -0.42, 0.2, _p(cor, a))
        _rr(c, -0.26, -0.18, 0.52, 0.65, 0.22, cor, a)
        c.restore()


def _relogio(c, a, lt):
    c.drawCircle(0, 0, 0.85, _p(BRANCO, a))
    c.drawCircle(0, 0, 0.85, _p(hx("8FA0BC"), a, stroke=0.08))
    for i in range(12):
        ang = math.radians(i * 30)
        c.drawLine(math.sin(ang) * 0.68, -math.cos(ang) * 0.68, math.sin(ang) * 0.76, -math.cos(ang) * 0.76,
                   _p(FUNDO, a, stroke=0.05))
    am = math.radians(lt * 120)
    c.drawLine(0, 0, math.sin(am) * 0.6, -math.cos(am) * 0.6, _p(VERMELHO, a, stroke=0.05))
    ah = math.radians(lt * 10 + 60)
    c.drawLine(0, 0, math.sin(ah) * 0.4, -math.cos(ah) * 0.4, _p(FUNDO, a, stroke=0.08))
    c.drawCircle(0, 0, 0.06, _p(FUNDO, a))


def _megafone(c, a, lt):
    corpo = _caminho([(-0.6, -0.2), (0.5, -0.65), (0.5, 0.65), (-0.6, 0.2)])
    c.drawPath(corpo, _p(VERMELHO, a))
    _rr(c, -0.85, -0.25, 0.3, 0.5, 0.08, hx("C9D3E6"), a)
    _rr(c, 0.45, -0.7, 0.14, 1.4, 0.07, hx("C9D3E6"), a)
    for i in range(3):
        k = ((lt * 1.2) - i * 0.25) % 1.0
        arco = skia.Path()
        r = 0.25 + k * 0.4
        arco.addArc(skia.Rect.MakeLTRB(0.6 - r, -r, 0.6 + r, r), -40, 80)
        c.drawPath(arco, _p(AMARELO, a * (1 - k), stroke=0.06))


# ---------------------------------------------------------------- objetos (lote 2)

def _robo(c, a, lt):
    c.translate(0, math.sin(lt * 2.4) * 0.03)
    metal, esc = hx("C9D3E6"), hx("8FA0BC")
    c.drawLine(0, -0.72, 0, -0.9, _p(esc, a, stroke=0.05))
    c.drawCircle(0, -0.93, 0.07, _p(VERMELHO if int(lt * 2) % 2 else AMARELO, a))
    _rr(c, -0.55, -0.72, 1.1, 0.75, 0.2, metal, a)
    piscar = 0.15 if abs((lt % 3.2) - 1.6) < 0.08 else 1.0
    for x in (-0.22, 0.22):
        c.save(); c.translate(x, -0.38); c.scale(1, piscar)
        c.drawCircle(0, 0, 0.11, _p(CIANO, a)); c.restore()
    _rr(c, -0.2, -0.17, 0.4, 0.07, 0.035, esc, a)
    _rr(c, -0.45, 0.1, 0.9, 0.7, 0.16, esc, a)
    c.drawCircle(0, 0.42, 0.12, _p(AMARELO, a))
    for x in (-0.72, 0.62):
        _rr(c, x, 0.15, 0.1, 0.45, 0.05, metal, a)


def _celular(c, a, lt):
    _rr(c, -0.45, -0.9, 0.9, 1.8, 0.14, hx("2A3550"), a)
    _rr(c, -0.38, -0.78, 0.76, 1.5, 0.06, PAINEL, a)
    for i in range(3):
        k = ease_out((lt - i * 0.2) / 0.35)
        _rr(c, -0.3, -0.62 + i * 0.4, 0.6 * k, 0.28, 0.06, [CIANO, AMARELO, VERDE][i], a * 0.85)
    c.drawCircle(0, 0.8, 0.05, _p(CINZA, a))


def _email(c, a, lt):
    k = ease_out((lt - 0.2) / 0.4)
    _rr(c, -0.85, -0.5, 1.7, 1.1, 0.08, BRANCO, a)
    c.drawPath(_caminho([(-0.85, -0.5), (0, 0.12), (0.85, -0.5)], fechar=False), _p(hx("8FA0BC"), a, stroke=0.07))
    c.drawCircle(0.72, -0.5, 0.2 * back_out(k), _p(VERMELHO, a))
    from motor.estilo import font
    if k > 0.3:
        c.save(); c.scale(0.01, 0.01)
        f = font("Black", 26)
        c.drawString("1", 72 - f.measureText("1") / 2 * 0 - 8, -40, f, _p(BRANCO, a))
        c.restore()


def _cartao(c, a, lt):
    c.rotate(-8 + math.sin(lt * 1.5) * 3)
    _rr(c, -0.85, -0.55, 1.7, 1.1, 0.12, hx("3A4E8A"), a)
    c.drawRect(skia.Rect.MakeLTRB(-0.85, -0.32, 0.85, -0.14), _p(FUNDO, a))
    _rr(c, -0.65, 0.0, 0.32, 0.24, 0.05, OURO, a)
    for i in range(4):
        _rr(c, -0.65 + i * 0.36, 0.34, 0.28, 0.08, 0.04, hx("C9D3E6"), a * 0.8)
    c.drawCircle(0.5, 0.15, 0.13, _p(VERMELHO, a * 0.9))
    c.drawCircle(0.66, 0.15, 0.13, _p(OURO, a * 0.9))


def _carrinho(c, a, lt):
    c.translate(math.sin(lt * 1.6) * 0.05, 0)
    cesta = _caminho([(-0.7, -0.45), (0.75, -0.45), (0.55, 0.25), (-0.55, 0.25)])
    for i, cor in enumerate([VERMELHO, VERDE, AMARELO]):
        k = back_out((lt - i * 0.15) / 0.4)
        if k > 0:
            _rr(c, -0.5 + i * 0.36, -0.45 - 0.35 * k, 0.28, 0.35 * k, 0.05, cor, a)
    c.drawPath(cesta, _p(hx("C9D3E6"), a, stroke=0.08))
    for i in range(1, 4):
        x = -0.7 + i * 0.36
        c.drawLine(x, -0.45, x * 0.85, 0.25, _p(hx("C9D3E6"), a, stroke=0.04))
    c.drawLine(-0.7, -0.45, -0.95, -0.75, _p(hx("8FA0BC"), a, stroke=0.08))
    for x in (-0.4, 0.4):
        c.drawCircle(x, 0.5, 0.13, _p(hx("8FA0BC"), a))


def _bola(c, a, lt):
    c.translate(0, -abs(math.sin(lt * 3)) * 0.18)
    c.rotate(lt * 90)
    c.drawCircle(0, 0, 0.8, _p(BRANCO, a))
    c.drawPath(_pentagono(0, 0, 0.26), _p(FUNDO, a))
    for i in range(5):
        ang = math.radians(-90 + i * 72)
        c.drawPath(_pentagono(0.62 * math.cos(ang), 0.62 * math.sin(ang), 0.17), _p(FUNDO, a))
    c.drawCircle(0, 0, 0.8, _p(hx("8FA0BC"), a, stroke=0.04))


def _pentagono(cx, cy, r):
    return _caminho([(cx + r * math.cos(math.radians(-90 + i * 72)), cy + r * math.sin(math.radians(-90 + i * 72)))
                     for i in range(5)])


def _pilula(c, a, lt):
    c.rotate(-35 + math.sin(lt * 2) * 6)
    _rr(c, -0.8, -0.3, 1.6, 0.6, 0.3, BRANCO, a)
    c.save()
    c.clipRect(skia.Rect.MakeLTRB(0, -0.4, 0.9, 0.4))
    _rr(c, -0.8, -0.3, 1.6, 0.6, 0.3, VERMELHO, a)
    c.restore()
    c.drawLine(-0.55, -0.15, -0.2, -0.15, _p(BRANCO, a * 0.6, stroke=0.06))


def _xicara(c, a, lt):
    for i in range(3):
        k = (lt * 0.8 + i * 0.33) % 1.0
        x = -0.3 + i * 0.3
        p = skia.Path()
        p.moveTo(x, -0.35 - k * 0.5)
        p.quadTo(x + 0.12, -0.5 - k * 0.5, x, -0.65 - k * 0.5)
        c.drawPath(p, _p(BRANCO, a * (1 - k) * 0.6, stroke=0.05))
    copo = skia.Path()
    copo.moveTo(-0.6, -0.3)
    copo.lineTo(0.6, -0.3)
    copo.quadTo(0.55, 0.45, 0, 0.5)
    copo.quadTo(-0.55, 0.45, -0.6, -0.3)
    c.drawPath(copo, _p(BRANCO, a))
    c.drawCircle(0.72, 0.02, 0.18, _p(BRANCO, a, stroke=0.08))
    c.drawOval(skia.Rect.MakeLTRB(-0.55, -0.36, 0.55, -0.22), _p(hx("B8743A"), a))
    c.drawOval(skia.Rect.MakeLTRB(-0.9, 0.48, 0.9, 0.66), _p(hx("C9D3E6"), a))


def _urna(c, a, lt):
    k = ease_io((lt - 0.2) / 0.7)
    _rr(c, -0.2, -0.95 + 0.55 * k, 0.4, 0.5, 0.03, BRANCO, a * (1 - 0.8 * max(0, k - 0.85) / 0.15))
    _rr(c, -0.75, -0.4, 1.5, 1.2, 0.08, hx("3A4E8A"), a)
    _rr(c, -0.35, -0.48, 0.7, 0.1, 0.05, FUNDO, a)
    c.save(); c.scale(0.01, 0.01)
    from motor.estilo import font
    f = font("Black", 30)
    c.drawString("VOTO", -f.measureText("VOTO") / 2, 25, f, _p(BRANCO, a))
    c.restore()


def _livro(c, a, lt):
    ab = ease_out(lt / 0.6)
    for lado in (-1, 1):
        pag = _caminho([(0, -0.6), (lado * 0.85 * ab, -0.68), (lado * 0.85 * ab, 0.55), (0, 0.62)])
        c.drawPath(pag, _p(BRANCO, a))
        for i in range(5):
            y = -0.45 + i * 0.2
            c.drawLine(lado * 0.12, y, lado * 0.7 * ab, y - 0.03, _p(CINZA, a * 0.7, stroke=0.035))
    c.drawPath(_caminho([(-0.9 * ab, 0.6), (0, 0.7), (0.9 * ab, 0.6), (0.9 * ab, 0.68), (0, 0.78),
                         (-0.9 * ab, 0.68)]), _p(VERMELHO, a))


def _formatura(c, a, lt):
    c.translate(0, -math.sin(min(lt, 1.2) / 1.2 * math.pi) * 0.25)
    c.drawPath(_caminho([(-0.95, -0.15), (0, -0.55), (0.95, -0.15), (0, 0.25)]), _p(hx("1E2A44"), a))
    c.drawPath(_caminho([(-0.5, 0.05), (0.5, 0.05), (0.45, 0.45), (-0.45, 0.45)]), _p(hx("1E2A44"), a))
    c.drawLine(0, -0.15, 0.7, 0.05, _p(OURO, a, stroke=0.04))
    c.drawLine(0.7, 0.05, 0.7, 0.45, _p(OURO, a, stroke=0.04))
    c.drawCircle(0.7, 0.5, 0.07, _p(OURO, a))
    c.drawCircle(0, -0.15, 0.06, _p(OURO, a))


def _dinheiro(c, a, lt):
    for i in range(4):
        k = back_out((lt - i * 0.12) / 0.35)
        if k <= 0:
            continue
        c.save()
        c.translate(0, 0.45 - i * 0.22 * k)
        _rr(c, -0.8, -0.2, 1.6, 0.4, 0.05, hx("3DAA6E"), a)
        _rr(c, -0.8, -0.2, 1.6, 0.4, 0.05, hx("2A7A4E"), a, stroke=0.03)
        c.drawCircle(0, 0, 0.12, _p(hx("2A7A4E"), a))
        c.restore()


def _foguete(c, a, lt):
    c.translate(0, -ease_io(lt / 2.5) * 0.25 + math.sin(lt * 20) * 0.01)
    chama = 0.7 + 0.3 * math.sin(lt * 25)
    c.drawPath(_caminho([(-0.18, 0.55), (0.18, 0.55), (0, 0.55 + 0.45 * chama)]), _p(AMARELO, a))
    c.drawPath(_caminho([(-0.1, 0.55), (0.1, 0.55), (0, 0.55 + 0.25 * chama)]), _p(VERMELHO, a))
    corpo = skia.Path()
    corpo.moveTo(0, -0.95)
    corpo.quadTo(0.38, -0.5, 0.28, 0.55)
    corpo.lineTo(-0.28, 0.55)
    corpo.quadTo(-0.38, -0.5, 0, -0.95)
    c.drawPath(corpo, _p(BRANCO, a))
    c.drawCircle(0, -0.3, 0.13, _p(CIANO, a))
    for lado in (-1, 1):
        c.drawPath(_caminho([(lado * 0.28, 0.1), (lado * 0.55, 0.6), (lado * 0.26, 0.5)]), _p(VERMELHO, a))


def _chuva(c, a, lt):
    nuvem = paint(hx("C9D3E6"), a)
    for x, y, r in [(-0.35, -0.2, 0.32), (0.05, -0.38, 0.4), (0.42, -0.18, 0.3), (0, -0.05, 0.35)]:
        c.drawCircle(x, y, r, nuvem)
    for i in range(6):
        k = (lt * 1.6 + i * 0.37) % 1.0
        x = -0.5 + i * 0.2
        c.drawLine(x, 0.3 + k * 0.6, x - 0.05, 0.42 + k * 0.6, _p(CIANO, a * (1 - k), stroke=0.05))


def _calendario(c, a, lt):
    _rr(c, -0.8, -0.7, 1.6, 1.5, 0.12, BRANCO, a)
    c.drawRect(skia.Rect.MakeLTRB(-0.8, -0.7, 0.8, -0.35), _p(VERMELHO, a))
    _rr(c, -0.8, -0.7, 1.6, 0.4, 0.12, VERMELHO, a)
    for x in (-0.4, 0.4):
        _rr(c, x - 0.05, -0.85, 0.1, 0.28, 0.05, hx("8FA0BC"), a)
    marcado = int(lt * 2) % 12
    for i in range(12):
        r_, k_ = divmod(i, 4)
        cx, cy = -0.55 + k_ * 0.37, -0.12 + r_ * 0.3
        c.drawCircle(cx, cy, 0.09, _p(AMARELO if i == marcado else hx("C9D3E6"), a))


def _casa(c, a, lt):
    c.drawPath(_caminho([(-0.9, -0.05), (0, -0.85), (0.9, -0.05)]), _p(VERMELHO, a))
    c.drawRect(skia.Rect.MakeLTRB(-0.7, -0.08, 0.7, 0.8), _p(hx("E8D9B8"), a))
    c.drawRect(skia.Rect.MakeLTRB(-0.15, 0.3, 0.15, 0.8), _p(hx("8C6A4F"), a))
    luz = 0.7 + 0.3 * math.sin(lt * 2)
    for x in (-0.5, 0.3):
        c.drawRect(skia.Rect.MakeLTRB(x, 0.08, x + 0.22, 0.3), _p(AMARELO, a * luz))
    c.drawRect(skia.Rect.MakeLTRB(0.45, -0.65, 0.6, -0.3), _p(hx("8C6A4F"), a))


def _carro(c, a, lt):
    c.translate(math.sin(lt * 1.2) * 0.06, 0)
    c.drawPath(_caminho([(-0.45, -0.1), (-0.25, -0.45), (0.3, -0.45), (0.55, -0.1)]), _p(CIANO, a))
    _rr(c, -0.9, -0.12, 1.8, 0.45, 0.14, CIANO, a)
    c.drawPath(_caminho([(-0.32, -0.13), (-0.2, -0.38), (0.0, -0.38), (0.0, -0.13)]), _p(PAINEL, a))
    c.drawPath(_caminho([(0.07, -0.13), (0.07, -0.38), (0.26, -0.38), (0.42, -0.13)]), _p(PAINEL, a))
    for x in (-0.5, 0.5):
        c.save(); c.translate(x, 0.33); c.rotate(lt * 360)
        c.drawCircle(0, 0, 0.18, _p(hx("2A3550"), a))
        c.drawLine(-0.1, 0, 0.1, 0, _p(CINZA, a, stroke=0.04))
        c.restore()
    c.drawCircle(0.82, 0.02, 0.06, _p(AMARELO, a))


def _microscopio(c, a, lt):
    metal = hx("C9D3E6")
    _rr(c, -0.6, 0.65, 1.2, 0.18, 0.06, hx("8FA0BC"), a)
    c.drawLine(0.25, 0.65, 0.25, -0.1, _p(hx("8FA0BC"), a, stroke=0.16))
    c.save(); c.translate(-0.05, -0.25); c.rotate(-30)
    _rr(c, -0.14, -0.6, 0.28, 0.9, 0.08, metal, a)
    _rr(c, -0.1, -0.78, 0.2, 0.2, 0.04, hx("8FA0BC"), a)
    c.restore()
    c.drawRect(skia.Rect.MakeLTRB(-0.5, 0.25, 0.4, 0.33), _p(hx("8FA0BC"), a))
    brilho = 0.5 + 0.5 * math.sin(lt * 4)
    c.drawCircle(-0.18, 0.2, 0.06, _p(VERDE, a * brilho))


OBJETOS = {
    "aviao": ("avião", _aviao), "dado": ("dado", _dado), "moeda": ("moeda", _moeda), "lupa": ("lupa", _lupa),
    "balanca": ("balança", _balanca), "alvo": ("alvo", _alvo), "cerebro": ("cérebro", _cerebro),
    "ampulheta": ("ampulheta", _ampulheta), "termometro": ("termômetro", _termometro),
    "trofeu": ("troféu", _trofeu), "cadeado": ("cadeado", _cadeado), "lampada": ("lâmpada (ideia)", _lampada),
    "computador": ("computador com gráfico", _computador), "documento": ("documento / artigo", _documento),
    "crescimento": ("gráfico subindo", _crescimento), "coracao": ("coração / saúde", _coracao),
    "pessoas": ("grupo de pessoas", _pessoas), "relogio": ("relógio / tempo", _relogio),
    "megafone": ("megafone / anúncio", _megafone),
    "robo": ("robô / IA", _robo), "celular": ("celular / aplicativo", _celular), "email": ("e-mail / spam", _email),
    "cartao": ("cartão de crédito", _cartao), "carrinho": ("carrinho de compras", _carrinho),
    "bola": ("bola de futebol", _bola), "pilula": ("pílula / remédio", _pilula), "xicara": ("xícara de chá/café", _xicara),
    "urna": ("urna / eleição", _urna), "livro": ("livro / estudo", _livro), "formatura": ("capelo / escola", _formatura),
    "dinheiro": ("dinheiro / salário", _dinheiro), "foguete": ("foguete / crescimento", _foguete),
    "chuva": ("nuvem com chuva / tempo", _chuva), "calendario": ("calendário / datas", _calendario),
    "casa": ("casa / moradia", _casa), "carro": ("carro / trânsito", _carro),
    "microscopio": ("microscópio / ciência", _microscopio),
}


def desenhar_objeto(c, nome: str, cx: float, cy: float, tamanho: float, a: float, lt: float, entrada=True):
    """Desenha o objeto centrado em (cx, cy) com lado ~`tamanho` px; entra com um 'pop'."""
    if a <= 0.002 or nome not in OBJETOS:
        return
    k = back_out(lt / 0.45) if entrada else 1.0
    if k <= 0:
        return
    c.save()
    c.translate(cx, cy)
    s = tamanho / 2 * k
    c.scale(s, s)
    OBJETOS[nome][1](c, a, lt)
    c.restore()
