"""Marcos famosos desenhados por código, para ilustrar lugares (cena `lugar` com `marco`).

Cada marco desenha dentro do retângulo (X, Y, PW, PH), já recortado, sobre céu e chão
próprios. `lt` = tempo desde a entrada (animações sutis). Para adicionar: escreva
`def _nome(c, X, Y, PW, PH, lt)` e registre em MARCOS com uma descrição.
"""

import math

import skia

from motor.estilo import AMARELO, BRANCO, C, CIANO, VERDE, VERMELHO, ease_out, hx, misturar, paint
from motor.ilustracoes.lugares import _ceu, _colinas

PEDRA, PEDRA_SOMBRA, ESCURO = hx("D9DEE8"), hx("A9B2C6"), hx("1A2238")


def _chao(c, X, Y, PW, PH, cor="162038", altura=95):
    c.drawRect(skia.Rect.MakeXYWH(X, Y + PH - altura, PW, altura), paint(hx(cor)))


def _sobe(c, lt, Y, PH):
    """Animação de entrada: o marco sobe do chão."""
    k = ease_out(lt / 0.8)
    c.translate(0, (1 - k) * PH * 0.15)
    return k


def _poligono(pts):
    p = skia.Path()
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    p.close()
    return p


def _arvores(c, X, Y, PW, PH, cor="1F3B3A"):
    for k in range(9):
        cx = X + 40 + k * 100 + (30 if k % 2 else 0)
        c.drawCircle(cx, Y + PH - 100, 40 + (k % 3) * 8, paint(hx(cor)))


# ---------------------------------------------------------------- marcos

def _torre_trelica(c, X, Y, PW, PH, lt):   # ex.: Torre Eiffel (Paris)
    _ceu(c, X, Y, PW, PH, lt, ("101A33", "3B2F5C", "B0607A"))
    _colinas(c, X, Y, PW, PH, lt)
    _chao(c, X, Y, PW, PH)
    c.save()
    _sobe(c, lt, Y, PH)
    cx, base, topo = X + PW / 2, Y + PH - 95, Y + 70
    cor = hx("8C6A4F")
    perna = paint(cor, 1, stroke=10)
    alt = base - topo
    pts_e = [(cx - 230, base), (cx - 120, base - alt * 0.3), (cx - 55, base - alt * 0.62), (cx - 14, topo + 40)]
    pts_d = [(2 * cx - x, y) for x, y in pts_e]
    for pts in (pts_e, pts_d):
        p = skia.Path()
        p.moveTo(*pts[0])
        for q in pts[1:]:
            p.lineTo(*q)
        c.drawPath(p, perna)
    for frac, larg in ((0.3, 120), (0.62, 55)):   # plataformas
        y = base - alt * frac
        c.drawRect(skia.Rect.MakeLTRB(cx - larg - 22, y - 10, cx + larg + 22, y + 6), paint(cor))
    arco = skia.Path()
    arco.moveTo(cx - 175, base)
    arco.quadTo(cx, base - alt * 0.32, cx + 175, base)
    c.drawPath(arco, paint(cor, 1, stroke=9))
    xadrez = paint(cor, 0.7, stroke=3)
    for i in range(14):   # treliça
        f0, f1 = i / 14, (i + 1) / 14
        y0, y1 = base - alt * f0 * 0.95, base - alt * f1 * 0.95
        w0 = 230 * (1 - f0) ** 1.6 + 14
        w1 = 230 * (1 - f1) ** 1.6 + 14
        c.drawLine(cx - w0, y0, cx + w1, y1, xadrez)
        c.drawLine(cx + w0, y0, cx - w1, y1, xadrez)
    c.drawLine(cx, topo + 40, cx, topo - 10, paint(cor, 1, stroke=6))
    c.drawCircle(cx, topo - 14, 6, paint(AMARELO))
    c.restore()


def _torre_relogio(c, X, Y, PW, PH, lt):   # ex.: Big Ben (Londres)
    _ceu(c, X, Y, PW, PH, lt, ("0F1A2E", "2A3B5C", "5C6E8A"))
    _chao(c, X, Y, PW, PH, "18233A")
    c.save()
    _sobe(c, lt, Y, PH)
    cx, base = X + PW / 2, Y + PH - 95
    ouro = hx("C9A55A")
    c.drawRect(skia.Rect.MakeLTRB(cx - 70, base - 470, cx + 70, base), paint(ouro))
    c.drawRect(skia.Rect.MakeLTRB(cx + 40, base - 470, cx + 70, base), paint(hx("A88848")))
    for k in range(8):
        c.drawLine(cx - 45 + k * 13, base - 460, cx - 45 + k * 13, base - 10, paint(hx("A88848"), 1, stroke=3))
    c.drawRect(skia.Rect.MakeLTRB(cx - 85, base - 600, cx + 85, base - 470), paint(ouro))
    c.drawCircle(cx, base - 535, 52, paint(BRANCO))
    c.drawCircle(cx, base - 535, 52, paint(ESCURO, 1, stroke=6))
    ang = lt * 0.6
    c.drawLine(cx, base - 535, cx + 34 * math.sin(ang), base - 535 - 34 * math.cos(ang), paint(ESCURO, 1, stroke=5))
    c.drawLine(cx, base - 535, cx + 22 * math.sin(ang / 12 + 2), base - 535 - 22 * math.cos(ang / 12 + 2),
               paint(ESCURO, 1, stroke=7))
    c.drawPath(_poligono([(cx - 85, base - 600), (cx + 85, base - 600), (cx, base - 760)]), paint(hx("4A5C4A")))
    c.drawLine(cx, base - 760, cx, base - 800, paint(ouro, 1, stroke=5))
    for dx in (-200, 200):   # prédio ao lado
        c.drawRect(skia.Rect.MakeLTRB(cx + dx - 110, base - 220, cx + dx + 110, base), paint(hx("A88848")))
        for j in range(5):
            c.drawRect(skia.Rect.MakeXYWH(cx + dx - 95 + j * 42, base - 190, 22, 50), paint(hx("2A3B5C")))
    c.restore()


def _estatua_tocha(c, X, Y, PW, PH, lt):   # ex.: Estátua da Liberdade (Nova York)
    _ceu(c, X, Y, PW, PH, lt, ("0F1F3A", "2B4A7A", "E6A06B"))
    c.drawRect(skia.Rect.MakeXYWH(X, Y + PH - 150, PW, 150), paint(hx("1C3A5E")))
    c.save()
    _sobe(c, lt, Y, PH)
    cx, base = X + PW / 2, Y + PH - 150
    verde = hx("6FB59E")
    c.drawRect(skia.Rect.MakeLTRB(cx - 110, base - 200, cx + 110, base), paint(hx("B9A88A")))
    c.drawRect(skia.Rect.MakeLTRB(cx - 80, base - 260, cx + 80, base - 200), paint(hx("CDBE9F")))
    corpo = _poligono([(cx - 70, base - 260), (cx + 70, base - 260), (cx + 45, base - 560), (cx - 45, base - 560)])
    c.drawPath(corpo, paint(verde))
    c.drawCircle(cx, base - 595, 38, paint(verde))
    for i in range(7):   # coroa
        ang = math.radians(-160 + i * 23)
        c.drawLine(cx, base - 615, cx + 70 * math.cos(ang), base - 615 + 70 * math.sin(ang), paint(verde, 1, stroke=7))
    c.drawLine(cx + 40, base - 540, cx + 110, base - 700, paint(verde, 1, stroke=26))
    chama = 0.85 + 0.15 * math.sin(lt * 9)
    c.drawCircle(cx + 115, base - 725, 38 * chama, paint(AMARELO, 0.35, blur=14))
    c.drawPath(_poligono([(cx + 98, base - 712), (cx + 132, base - 712), (cx + 115, base - 712 - 50 * chama)]),
               paint(AMARELO))
    c.drawRect(skia.Rect.MakeLTRB(cx - 80, base - 470, cx - 40, base - 400), paint(hx("5A9A86")))
    c.restore()


def _estatua_bracos(c, X, Y, PW, PH, lt):   # ex.: Cristo Redentor (Rio de Janeiro)
    _ceu(c, X, Y, PW, PH, lt, ("0E2A4A", "2E6A9A", "F2B279"))
    c.drawCircle(X + 180, Y + 520, 140, paint(AMARELO, 0.15, blur=50))
    morro = _poligono([(X - 10, Y + PH), (X + PW * 0.25, Y + PH * 0.62), (X + PW * 0.5, Y + PH * 0.42),
                       (X + PW * 0.72, Y + PH * 0.6), (X + PW + 10, Y + PH)])
    c.drawPath(morro, paint(hx("1F4A3A")))
    pao = _poligono([(X + PW * 0.02, Y + PH), (X + PW * 0.1, Y + PH * 0.72), (X + PW * 0.18, Y + PH * 0.66),
                     (X + PW * 0.24, Y + PH)])
    c.drawPath(pao, paint(hx("2C5E48")))
    c.drawRect(skia.Rect.MakeXYWH(X, Y + PH - 70, PW, 70), paint(hx("1C3A5E")))
    c.save()
    k = _sobe(c, lt, Y, PH)
    cx, base = X + PW * 0.5, Y + PH * 0.42
    pedra = hx("E8E6DF")
    c.drawRect(skia.Rect.MakeLTRB(cx - 28, base - 40, cx + 28, base), paint(hx("CFCBC0")))
    corpo = _poligono([(cx - 34, base - 40), (cx + 34, base - 40), (cx + 24, base - 260), (cx - 24, base - 260)])
    c.drawPath(corpo, paint(pedra))
    abre = 175 * ease_out((lt - 0.3) / 0.6)
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(cx - abre - 10, base - 255, cx + abre + 10, base - 222),
                                      14, 14), paint(pedra))
    c.drawCircle(cx, base - 285, 26, paint(pedra))
    c.restore()


def _ponte_suspensa(c, X, Y, PW, PH, lt):   # ex.: Golden Gate (São Francisco)
    _ceu(c, X, Y, PW, PH, lt, ("12223F", "3A4E7A", "E39A6A"))
    c.drawRect(skia.Rect.MakeXYWH(X, Y + PH - 230, PW, 230), paint(hx("1D3557")))
    for i in range(8):
        yy = Y + PH - 200 + i * 26
        c.drawLine(X + (i * 70 + lt * 40) % PW, yy, X + (i * 70 + lt * 40) % PW + 60, yy, paint(BRANCO, 0.15, stroke=3))
    c.save()
    _sobe(c, lt, Y, PH)
    vermelho = hx("C8452E")
    tab = Y + PH - 300
    c.drawRect(skia.Rect.MakeLTRB(X - 10, tab, X + PW + 10, tab + 22), paint(vermelho))
    torres = [X + PW * 0.25, X + PW * 0.75]
    for tx in torres:
        c.drawRect(skia.Rect.MakeLTRB(tx - 24, Y + 150, tx + 24, Y + PH - 230), paint(vermelho))
        for yy in (Y + 200, Y + 330, Y + 460):
            c.drawRect(skia.Rect.MakeLTRB(tx - 34, yy, tx + 34, yy + 16), paint(vermelho))
    cabo = paint(vermelho, 1, stroke=6)
    for ini, fim in ((X - 10, torres[0]), (torres[0], torres[1]), (torres[1], X + PW + 10)):
        y0 = Y + 160 if ini in torres else tab - 40
        y1 = Y + 160 if fim in torres else tab - 40
        yc = tab - 10
        p = skia.Path()
        p.moveTo(ini, y0)
        p.quadTo((ini + fim) / 2, yc, fim, y1)
        c.drawPath(p, cabo)
        for j in range(1, 12):   # tirantes do tabuleiro até o cabo
            u = j / 12
            x = ini + (fim - ini) * u
            y_cabo = (1 - u) ** 2 * y0 + 2 * (1 - u) * u * yc + u ** 2 * y1
            if y_cabo < tab - 4:
                c.drawLine(x, tab, x, y_cabo, paint(vermelho, 0.7, stroke=2))
    c.restore()


def _coliseu(c, X, Y, PW, PH, lt):   # ex.: Coliseu (Roma)
    _ceu(c, X, Y, PW, PH, lt, ("15233F", "4A5A8A", "E7B07A"))
    _chao(c, X, Y, PW, PH, "3A3326")
    c.save()
    _sobe(c, lt, Y, PH)
    pedra, sombra = hx("D8B98A"), hx("A88A5E")
    cx, base, larg = X + PW / 2, Y + PH - 95, PW * 0.84
    andares = 4
    for a_ in range(andares):
        y1 = base - a_ * 120
        y0 = y1 - 120
        w = larg * (1 - a_ * 0.03)
        if a_ == andares - 1:   # andar de cima, parcialmente em ruína
            c.drawPath(_poligono([(cx - w / 2, y1), (cx + w * 0.1, y1), (cx - w * 0.05, y0 + 20), (cx - w / 2, y0)]),
                       paint(pedra))
            continue
        c.drawRect(skia.Rect.MakeLTRB(cx - w / 2, y0, cx + w / 2, y1), paint(pedra))
        c.drawRect(skia.Rect.MakeLTRB(cx - w / 2, y0, cx + w / 2, y0 + 10), paint(sombra))
        n = 9
        for j in range(n):
            ax = cx - w / 2 + (j + 0.5) * w / n
            arco = skia.Path()
            arco.addRRect(skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(ax - 24, y0 + 30, ax + 24, y1 - 6), 24, 24))
            c.drawPath(arco, paint(hx("2B2A3A")))
    c.restore()


def _templo(c, X, Y, PW, PH, lt):   # ex.: Partenon (Atenas), tribunais, bolsas de valores
    _ceu(c, X, Y, PW, PH, lt, ("13213D", "3E5C8C", "D9A56E"))
    _colinas(c, X, Y, PW, PH, lt)
    _chao(c, X, Y, PW, PH, "2F2A22")
    c.save()
    _sobe(c, lt, Y, PH)
    cx, base, w = X + PW / 2, Y + PH - 95, PW * 0.76
    c.drawRect(skia.Rect.MakeLTRB(cx - w / 2 - 20, base - 40, cx + w / 2 + 20, base), paint(PEDRA_SOMBRA))
    c.drawRect(skia.Rect.MakeLTRB(cx - w / 2, base - 70, cx + w / 2, base - 40), paint(PEDRA))
    n = 8
    for j in range(n):
        x = cx - w / 2 + 25 + j * (w - 50) / (n - 1)
        c.drawRect(skia.Rect.MakeLTRB(x - 20, base - 380, x + 20, base - 70), paint(PEDRA))
        for k_ in range(3):
            c.drawLine(x - 10 + k_ * 10, base - 370, x - 10 + k_ * 10, base - 80, paint(PEDRA_SOMBRA, 1, stroke=2))
    c.drawRect(skia.Rect.MakeLTRB(cx - w / 2 - 10, base - 420, cx + w / 2 + 10, base - 380), paint(PEDRA))
    c.drawPath(_poligono([(cx - w / 2 - 20, base - 420), (cx + w / 2 + 20, base - 420), (cx, base - 530)]),
               paint(PEDRA))
    c.drawPath(_poligono([(cx - w / 2 + 30, base - 428), (cx + w / 2 - 30, base - 428), (cx, base - 510)]),
               paint(PEDRA_SOMBRA))
    c.restore()


def _piramides(c, X, Y, PW, PH, lt):   # ex.: Gizé (Egito)
    _ceu(c, X, Y, PW, PH, lt, ("1A2A4A", "6A7AA8", "F2C27A"))
    c.drawCircle(X + PW * 0.78, Y + 260, 70, paint(AMARELO, 0.9))
    c.drawCircle(X + PW * 0.78, Y + 260, 120, paint(AMARELO, 0.2, blur=30))
    c.drawRect(skia.Rect.MakeXYWH(X, Y + PH - 180, PW, 180), paint(hx("C79A5A")))
    c.save()
    _sobe(c, lt, Y, PH)
    base = Y + PH - 170
    for cx, h, w in ((X + PW * 0.32, 420, 520), (X + PW * 0.68, 330, 400), (X + PW * 0.9, 200, 240)):
        c.drawPath(_poligono([(cx - w / 2, base), (cx, base - h), (cx + w / 2, base)]), paint(hx("E2B56E")))
        c.drawPath(_poligono([(cx, base - h), (cx + w / 2, base), (cx + w * 0.1, base)]), paint(hx("B98A4A")))
    c.restore()


def _cupula(c, X, Y, PW, PH, lt):   # ex.: Taj Mahal (Índia), Capitólio, mesquitas
    _ceu(c, X, Y, PW, PH, lt, ("16223F", "4A5E9A", "F0B98A"))
    c.drawRect(skia.Rect.MakeXYWH(X, Y + PH - 160, PW, 160), paint(hx("1E3A5A")))
    c.save()
    _sobe(c, lt, Y, PH)
    cx, base = X + PW / 2, Y + PH - 160
    branco = hx("F1EEE6")
    c.drawRect(skia.Rect.MakeLTRB(cx - 220, base - 260, cx + 220, base), paint(branco))
    porta = skia.Path()
    porta.addRRect(skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(cx - 55, base - 210, cx + 55, base), 55, 55))
    c.drawPath(porta, paint(hx("C9C2B2")))
    c.drawRect(skia.Rect.MakeLTRB(cx - 70, base - 330, cx + 70, base - 260), paint(branco))
    cup = skia.Path()
    cup.moveTo(cx - 150, base - 330)
    cup.cubicTo(cx - 170, base - 520, cx - 10, base - 560, cx, base - 600)
    cup.cubicTo(cx + 10, base - 560, cx + 170, base - 520, cx + 150, base - 330)
    cup.close()
    c.drawPath(cup, paint(branco))
    c.drawLine(cx, base - 600, cx, base - 640, paint(AMARELO, 1, stroke=5))
    for dx in (-300, 300):
        c.drawRect(skia.Rect.MakeLTRB(cx + dx - 18, base - 450, cx + dx + 18, base), paint(branco))
        c.drawCircle(cx + dx, base - 460, 24, paint(branco))
    c.restore()


def _predio_classico(c, X, Y, PW, PH, lt):   # universidades, institutos, bibliotecas
    _ceu(c, X, Y, PW, PH, lt, ("101A33", "2B3F6A", "7A6E9A"))
    _chao(c, X, Y, PW, PH, "1D3A2E")
    _arvores(c, X, Y, PW, PH)
    c.save()
    _sobe(c, lt, Y, PH)
    cx, base, w = X + PW / 2, Y + PH - 110, PW * 0.74
    tijolo = hx("B5653F")
    c.drawRect(skia.Rect.MakeLTRB(cx - w / 2, base - 330, cx + w / 2, base), paint(tijolo))
    for r in range(3):
        for j in range(8):
            if 3 <= j <= 4 and r == 2:
                continue
            c.drawRect(skia.Rect.MakeXYWH(cx - w / 2 + 30 + j * (w - 60) / 8, base - 300 + r * 95, 36, 60),
                       paint(hx("F2E3B8"), 0.75 + 0.25 * math.sin(lt * 2 + j + r)))
    c.drawRect(skia.Rect.MakeLTRB(cx - 130, base - 360, cx + 130, base), paint(PEDRA))
    for j in range(4):
        x = cx - 100 + j * 66
        c.drawRect(skia.Rect.MakeLTRB(x - 12, base - 330, x + 12, base - 20), paint(PEDRA_SOMBRA))
    c.drawPath(_poligono([(cx - 150, base - 360), (cx + 150, base - 360), (cx, base - 450)]), paint(PEDRA))
    c.drawLine(cx, base - 450, cx, base - 560, paint(PEDRA_SOMBRA, 1, stroke=4))
    onda = math.sin(lt * 4) * 6
    c.drawPath(_poligono([(cx, base - 560), (cx + 70, base - 545 + onda), (cx, base - 520)]), paint(VERMELHO))
    c.drawRect(skia.Rect.MakeLTRB(cx - 160, base - 12, cx + 160, base + 8), paint(PEDRA_SOMBRA))
    c.restore()


def _arranha_ceus(c, X, Y, PW, PH, lt):   # cidades grandes / centros financeiros
    _ceu(c, X, Y, PW, PH, lt, ("0B1328", "1E2A55", "4A3A70"))
    c.save()
    _sobe(c, lt, Y, PH)
    base = Y + PH - 60
    predios = [(0.05, 0.12, 360), (0.17, 0.1, 520), (0.27, 0.13, 430), (0.4, 0.12, 640), (0.52, 0.1, 380),
               (0.62, 0.14, 560), (0.76, 0.1, 470), (0.86, 0.12, 330)]
    for i, (fx, fw, h) in enumerate(predios):
        x0, w = X + PW * fx, PW * fw
        c.drawRect(skia.Rect.MakeLTRB(x0, base - h, x0 + w, base), paint(hx("1B2440" if i % 2 else "232E52")))
        for r in range(int(h / 34)):
            for k_ in range(int(w / 26)):
                aceso = (i * 7 + r * 3 + k_ * 5 + int(lt * 1.5)) % 5 != 0
                if aceso:
                    c.drawRect(skia.Rect.MakeXYWH(x0 + 8 + k_ * 26, base - h + 14 + r * 34, 12, 18),
                               paint(hx("F2D27A"), 0.75))
    c.drawRect(skia.Rect.MakeXYWH(X, base, PW, 60), paint(hx("0E1424")))
    c.restore()


def _farol(c, X, Y, PW, PH, lt):   # costa, portos, navegação
    _ceu(c, X, Y, PW, PH, lt, ("0A1430", "1F2E5A", "3A4E7A"))
    c.drawRect(skia.Rect.MakeXYWH(X, Y + PH - 200, PW, 200), paint(hx("16304F")))
    c.save()
    _sobe(c, lt, Y, PH)
    cx, base = X + PW * 0.6, Y + PH - 200
    c.drawPath(_poligono([(cx - 220, base + 40), (cx - 90, base - 40), (cx + 130, base - 30), (cx + 260, base + 40)]),
               paint(hx("3A3A4A")))
    torre = _poligono([(cx - 60, base - 30), (cx + 60, base - 30), (cx + 36, base - 430), (cx - 36, base - 430)])
    c.drawPath(torre, paint(BRANCO))
    c.save()
    c.clipPath(torre, doAntiAlias=True)
    for k_ in range(4):
        c.drawRect(skia.Rect.MakeLTRB(cx - 80, base - 110 - k_ * 100, cx + 80, base - 60 - k_ * 100), paint(VERMELHO))
    c.restore()
    c.drawRect(skia.Rect.MakeLTRB(cx - 46, base - 500, cx + 46, base - 430), paint(hx("F2E3B8")))
    c.drawPath(_poligono([(cx - 56, base - 500), (cx + 56, base - 500), (cx, base - 560)]), paint(VERMELHO))
    ang = lt * 1.2
    feixe = _poligono([(cx, base - 465), (cx + 520 * math.cos(ang), base - 465 - 60),
                       (cx + 520 * math.cos(ang), base - 465 + 60)])
    c.drawPath(feixe, paint(AMARELO, 0.18))
    c.restore()


def _hospital(c, X, Y, PW, PH, lt):   # saúde, medicina, estudos clínicos
    _ceu(c, X, Y, PW, PH, lt, ("10213F", "2E5A8A", "8AB4D8"))
    _chao(c, X, Y, PW, PH, "1D3A2E")
    _arvores(c, X, Y, PW, PH)
    c.save()
    _sobe(c, lt, Y, PH)
    cx, base, w = X + PW / 2, Y + PH - 110, PW * 0.66
    c.drawRect(skia.Rect.MakeLTRB(cx - w / 2, base - 420, cx + w / 2, base), paint(hx("E8EEF5")))
    for r in range(5):
        for j in range(6):
            c.drawRect(skia.Rect.MakeXYWH(cx - w / 2 + 34 + j * (w - 68) / 6, base - 390 + r * 70, 46, 40),
                       paint(hx("8AB4D8")))
    c.drawRect(skia.Rect.MakeLTRB(cx - 70, base - 110, cx + 70, base), paint(hx("5A86B0")))
    pulso = 1 + 0.05 * math.sin(lt * 4)
    c.save()
    c.translate(cx, base - 500)
    c.scale(pulso, pulso)
    c.drawCircle(0, 0, 70, paint(BRANCO))
    c.drawRect(skia.Rect.MakeLTRB(-16, -48, 16, 48), paint(VERMELHO))
    c.drawRect(skia.Rect.MakeLTRB(-48, -16, 48, 16), paint(VERMELHO))
    c.restore()
    c.restore()


def _montanhas(c, X, Y, PW, PH, lt):   # natureza, parques, regiões montanhosas
    _ceu(c, X, Y, PW, PH, lt, ("13254A", "3E6A9A", "C9E0F0"))
    c.save()
    _sobe(c, lt, Y, PH)
    base = Y + PH
    for cx, h, w, cor in ((X + PW * 0.3, 560, 640, "4A5E7A"), (X + PW * 0.72, 470, 560, "3A4E6A"),
                          (X + PW * 0.5, 380, 700, "2E405A")):
        pico = (cx, base - h)
        c.drawPath(_poligono([(cx - w / 2, base), pico, (cx + w / 2, base)]), paint(hx(cor)))
        neve = _poligono([(cx - w * 0.12, base - h * 0.78), pico, (cx + w * 0.12, base - h * 0.78),
                          (cx + w * 0.04, base - h * 0.74), (cx - w * 0.03, base - h * 0.8)])
        c.drawPath(neve, paint(BRANCO, 0.9))
    c.drawRect(skia.Rect.MakeXYWH(X, Y + PH - 90, PW, 90), paint(hx("1F3B3A")))
    c.restore()


MARCOS = {
    "torre_trelica": ("torre treliçada (ex.: Torre Eiffel, Paris)", _torre_trelica),
    "torre_relogio": ("torre do relógio (ex.: Big Ben, Londres)", _torre_relogio),
    "estatua_tocha": ("estátua com tocha (ex.: Estátua da Liberdade, Nova York)", _estatua_tocha),
    "estatua_bracos": ("estátua de braços abertos no morro (ex.: Cristo Redentor, Rio)", _estatua_bracos),
    "ponte_suspensa": ("ponte suspensa vermelha (ex.: Golden Gate, São Francisco)", _ponte_suspensa),
    "coliseu": ("anfiteatro de arcos (ex.: Coliseu, Roma)", _coliseu),
    "templo": ("templo de colunas (ex.: Partenon, Atenas; tribunais, bolsas)", _templo),
    "piramides": ("pirâmides no deserto (ex.: Gizé, Egito)", _piramides),
    "cupula": ("palácio com cúpula e torres (ex.: Taj Mahal; capitólios)", _cupula),
    "predio_classico": ("prédio de universidade/instituto (tijolo, colunas, bandeira)", _predio_classico),
    "arranha_ceus": ("cidade com arranha-céus à noite (centros financeiros)", _arranha_ceus),
    "farol": ("farol na costa (portos, navegação)", _farol),
    "hospital": ("hospital (saúde, estudos clínicos)", _hospital),
    "montanhas": ("montanhas nevadas (natureza, regiões de montanha)", _montanhas),
}
