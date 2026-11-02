"""Biblioteca de lugares desenhados por código. Cresce com o uso.

Para adicionar um lugar: escreva `def meu_lugar(c, X, Y, PW, PH, lt)` desenhando dentro do
retângulo (já recortado) e registre em LUGARES com um id curto e minúsculo.
"""

import math

import skia

from motor.estilo import AMARELO, BRANCO, C, CINZA, PAINEL_LN, VERMELHO, back_out, ease_out, hx, paint, texto

# Contorno simplificado da Califórnia (lon, lat).
CA = [(-124.2, 42.0), (-120.0, 42.0), (-120.0, 39.0), (-114.6, 35.1), (-114.7, 32.7), (-117.1, 32.5),
      (-117.3, 33.2), (-118.4, 33.8), (-119.2, 34.3), (-120.6, 34.6), (-120.9, 35.4), (-121.9, 36.6),
      (-122.4, 37.2), (-122.5, 37.8), (-123.0, 38.0), (-123.7, 38.9), (-123.8, 39.8), (-124.4, 40.4),
      (-124.1, 41.0)]
BERK = (-122.27, 37.87)


def _ceu(c, X, Y, PW, PH, lt, cores=("101A33", "2B2F5C", "6B4A5E")):
    sky = skia.GradientShader.MakeLinear([(0, Y), (0, Y + PH)], [C(hx(k)) for k in cores], [0, 0.6, 1])
    c.drawRect(skia.Rect.MakeXYWH(X, Y, PW, PH), skia.Paint(Shader=sky))
    for i in range(26):   # estrelas
        sx = X + (i * 157) % PW
        sy = Y + 30 + (i * 89) % 330
        tw = 0.4 + 0.6 * (0.5 + 0.5 * math.sin(lt * 3 + i))
        c.drawCircle(sx, sy, 2.4, paint(BRANCO, 0.6 * tw))


def _colinas(c, X, Y, PW, PH, lt):
    par = lt * 6

    def hills(base, amp, col, ph):
        p = skia.Path()
        p.moveTo(X - 20, Y + PH)
        for k in range(46):
            x = X - 20 + k * (PW + 40) / 45
            p.lineTo(x, Y + base - amp * (0.6 * math.sin(k * 0.33 + ph) + 0.4 * math.sin(k * 0.71 + ph * 2)))
        p.lineTo(X + PW + 20, Y + PH)
        p.close()
        c.drawPath(p, paint(col))

    c.save(); c.translate(-par * 0.3, 0); hills(520, 60, hx("2A3560"), 0.4); c.restore()
    c.save(); c.translate(-par * 0.6, 0); hills(610, 40, hx("1E2747"), 1.7); c.restore()


def berkeley(c, X, Y, PW, PH, lt):
    """Campus: torre Sather (Campanile), colinas e mapa da Califórnia."""
    _ceu(c, X, Y, PW, PH, lt)
    c.drawCircle(X + 640, Y + 560, 160, paint(AMARELO, 0.18, blur=60))
    _colinas(c, X, Y, PW, PH, lt)
    rise = ease_out(lt / 0.8)
    tx = X + 520
    base = Y + PH - 90
    stone, shade, dark = hx("D9DEE8"), hx("A9B2C6"), hx("1A2238")
    if rise > 0.02:
        c.save()
        c.translate(0, (1 - rise) * 60)
        sw = 74
        c.drawRect(skia.Rect.MakeLTRB(tx - sw / 2, base - 330, tx + sw / 2, base), paint(stone))
        c.drawRect(skia.Rect.MakeLTRB(tx + sw / 2 - 18, base - 330, tx + sw / 2, base), paint(shade))
        for k in range(5):
            yy = base - 60 - k * 55
            c.drawRect(skia.Rect.MakeLTRB(tx - sw / 2, yy, tx + sw / 2, yy + 4), paint(shade))
        bw, bt = 96, base - 430
        c.drawRect(skia.Rect.MakeLTRB(tx - bw / 2, bt, tx + bw / 2, base - 330), paint(stone))
        c.drawRect(skia.Rect.MakeLTRB(tx - bw / 2 - 6, base - 336, tx + bw / 2 + 6, base - 326), paint(shade))
        for j in range(3):
            ox = tx - 30 + j * 30
            p = skia.Path()
            p.addRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(ox - 9, bt + 40, 18, 52), 9, 9))
            c.drawPath(p, paint(dark))
        c.drawCircle(tx, base - 360, 15, paint(dark))
        c.drawCircle(tx, base - 360, 11, paint(hx("F2E3B8")))
        c.drawLine(tx, base - 360, tx, base - 368, paint(dark, stroke=2.5))
        c.drawLine(tx, base - 360, tx + 6, base - 360, paint(dark, stroke=2.5))
        c.drawRect(skia.Rect.MakeLTRB(tx - bw / 2 - 6, bt - 8, tx + bw / 2 + 6, bt + 2), paint(shade))
        roof = skia.Path()
        roof.moveTo(tx - bw / 2, bt - 6); roof.lineTo(tx, bt - 110); roof.lineTo(tx + bw / 2, bt - 6); roof.close()
        c.drawPath(roof, paint(hx("8FA0BC")))
        c.drawCircle(tx, bt - 116, 6, paint(AMARELO))
        c.restore()
    c.drawRect(skia.Rect.MakeXYWH(X, Y + PH - 95, PW, 95), paint(hx("162038")))
    for k in range(9):
        cxk = X + 40 + k * 100 + (30 if k % 2 else 0)
        c.drawCircle(cxk, Y + PH - 100, 44 + (k % 3) * 8, paint(hx("1F3B3A")))
    # mapa da Califórnia
    mx, my, mw, mh = X + 40, Y + 40, 230, 270
    m = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(mx, my, mw, mh), 22, 22)
    c.drawRRect(m, paint(hx("0B1220"), 0.85))
    c.drawRRect(m, paint(PAINEL_LN, 1, stroke=2))

    def proj(lon, lat):
        return (mx + 20 + (lon + 124.6) / 10.3 * (mw - 40), my + 20 + (42.3 - lat) / 10.0 * (mh - 60))

    p = skia.Path()
    p.moveTo(*proj(*CA[0]))
    for q in CA[1:]:
        p.lineTo(*proj(*q))
    p.close()
    c.drawPath(p, paint(hx("2E3C5F")))
    c.drawPath(p, paint(CINZA, 0.8, stroke=2))
    bx, by = proj(*BERK)
    pk = ease_out((lt - 0.6) / 0.4)
    if pk > 0:
        pulse = (lt * 1.2) % 1.0
        c.drawCircle(bx, by, 8 + 22 * pulse, paint(VERMELHO, (1 - pulse) * 0.8 * pk, stroke=3))
        c.drawCircle(bx, by, 9 * back_out(pk), paint(VERMELHO, pk))
        texto(c, "Califórnia", mx + mw / 2, my + mh - 18, 24, CINZA, 1, "SemiBold", "center")


LUGARES = {
    "berkeley": berkeley,
}
