"""Caricatura genérica (nunca foto, sem copiar traços do rosto) e silhueta neutra.

A caricatura usa só: cor de pele, faixa etária e gênero da pessoa na época do fato.
Sem cor de pele ou idade com fonte: silhueta neutra.
"""

import math

import skia

from motor.estilo import AMARELO, BRANCO, CINZA, FUNDO_ILUS, hx, misturar, paint

PELES = {   # (pele, sombra)
    "clara": (hx("F2C7A5"), hx("D9A47F")),
    "media": (hx("E0AC82"), hx("C68B62")),
    "morena": (hx("C08A5E"), hx("A06F48")),
    "escura": (hx("8D5A3B"), hx("6E432A")),
}


def faixa_etaria(idade: int) -> str:
    return "jovem" if idade < 40 else ("madura" if idade < 60 else "idosa")


def caricatura(c, cx, cy, a, lt, cor_pele="clara", idade=35, genero="masculino"):
    """Desenha centrada em (cx, cy), cabendo num círculo de raio ~150."""
    skin, skin_dk = PELES.get(cor_pele, PELES["clara"])
    faixa = faixa_etaria(idade)
    escuro = hx("1E1612") if cor_pele == "escura" else hx("4A3426")
    hair = {"jovem": escuro, "madura": misturar(escuro, hx("B8B8BC"), 0.45), "idosa": hx("C9C9CE")}[faixa]
    older = faixa == "idosa"
    fem = genero == "feminino"
    roupa = hx("6B4E8A") if fem else hx("3B4560")
    shirt, lip, eye = BRANCO, hx("9C4A3C"), hx("2A1E1A")
    bob = math.sin(lt * 2.2) * 3
    hy = cy - 30 + bob
    HW, HH = 70, 80

    # cabelo de trás (feminino: mais longo)
    if fem:
        back = skia.Path()
        back.addRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(cx - HW - 16, hy - HH - 8, 2 * HW + 32,
                                                               HH * 2 + (10 if older else 40)), 60, 60))
        c.drawPath(back, paint(hair, a))

    # corpo
    body = skia.Path()
    body.addRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(cx - 115, cy + 62, 230, 200), 80, 80))
    c.drawPath(body, paint(roupa, a))
    if fem:
        gola = skia.Path()
        gola.moveTo(cx - 42, cy + 66); gola.quadTo(cx, cy + 118, cx + 42, cy + 66); gola.close()
        c.drawPath(gola, paint(skin_dk, a))
        c.drawCircle(cx, cy + 104, 7, paint(AMARELO, a))   # broche/colar
    else:
        collar = skia.Path()
        collar.moveTo(cx - 30, cy + 64); collar.lineTo(cx, cy + 118); collar.lineTo(cx + 30, cy + 64); collar.close()
        c.drawPath(collar, paint(shirt, a))
        lap = paint(hx("2C3449"), a, stroke=4)
        c.drawLine(cx - 30, cy + 66, cx - 8, cy + 150, lap)
        c.drawLine(cx + 30, cy + 66, cx + 8, cy + 150, lap)
        tie = skia.Path()
        tie.moveTo(cx - 8, cy + 74); tie.lineTo(cx + 8, cy + 74); tie.lineTo(cx + 12, cy + 132)
        tie.lineTo(cx, cy + 146); tie.lineTo(cx - 12, cy + 132); tie.close()
        c.drawPath(tie, paint(AMARELO, a))
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(cx - 20, cy + 30, 40, 42), 10, 10), paint(skin_dk, a))

    # cabeça (grande, estilo caricatura)
    c.drawCircle(cx - HW + 2, hy + 8, 15, paint(skin_dk, a))
    c.drawCircle(cx + HW - 2, hy + 8, 15, paint(skin_dk, a))
    head = skia.Path()
    head.addOval(skia.Rect.MakeXYWH(cx - HW, hy - HH, 2 * HW, 2 * HH))
    c.drawPath(head, paint(skin, a))

    # cabelo
    cap = skia.Path()
    cap.addOval(skia.Rect.MakeXYWH(cx - HW - 5, hy - HH - 12, 2 * HW + 10, 2 * HH))
    cut = skia.Path()
    cut.addRect(skia.Rect.MakeLTRB(cx - HW - 20, hy - HH - 30, cx + HW + 20, hy - (66 if older and not fem else 50)))
    hair_p = skia.Op(cap, cut, skia.PathOp.kIntersect_PathOp)
    for x0, x1 in ((cx - HW - 6, cx - HW + 9), (cx + HW - 9, cx + HW + 6)):
        side = skia.Path()
        side.addRect(skia.Rect.MakeLTRB(x0, hy - 55, x1, hy - (0 if fem else 12)))
        hair_p = skia.Op(hair_p, side, skia.PathOp.kUnion_PathOp)
    hair_p = skia.Op(hair_p, cap, skia.PathOp.kIntersect_PathOp)
    if older and not fem:   # entradas
        bald = skia.Path()
        bald.addOval(skia.Rect.MakeXYWH(cx - 46, hy - HH - 4, 92, 46))
        hair_p = skia.Op(hair_p, bald, skia.PathOp.kDifference_PathOp)
    c.drawPath(hair_p, paint(hair, a))
    if fem:   # franja
        fr = skia.Path()
        fr.moveTo(cx - HW + 4, hy - 40)
        fr.cubicTo(cx - 40, hy - HH - 10, cx + 50, hy - HH - 14, cx + HW - 2, hy - 36)
        fr.cubicTo(cx + 30, hy - 60, cx - 20, hy - 58, cx - HW + 4, hy - 40)
        fr.close()
        c.drawPath(fr, paint(hair, a))
    elif not older:
        swoop = skia.Path()
        swoop.moveTo(cx - 25, hy - HH - 4)
        swoop.cubicTo(cx + 25, hy - HH - 22, cx + 72, hy - 80, cx + 66, hy - 48)
        swoop.cubicTo(cx + 40, hy - 64, cx + 5, hy - 62, cx - 25, hy - 60)
        swoop.close()
        c.drawPath(swoop, paint(hair, a))
        c.drawLine(cx - 24, hy - HH + 4, cx - 30, hy - 58, paint(misturar(hair, (0, 0, 0), 0.35), a, stroke=3))

    if faixa != "jovem":   # rugas
        wl = paint(skin_dk, a * (0.8 if older else 0.5), stroke=2.5)
        for k in range(2 if older else 1):
            p = skia.Path()
            p.moveTo(cx - 28, hy - 44 + k * 9); p.quadTo(cx, hy - 50 + k * 9, cx + 28, hy - 44 + k * 9)
            c.drawPath(p, wl)
        for sx in (-1, 1):
            p = skia.Path()
            p.moveTo(cx + sx * 20, hy + 22); p.quadTo(cx + sx * 30, hy + 38, cx + sx * 28, hy + 50)
            c.drawPath(p, wl)

    # olhos (piscam)
    blink = 1.0
    for tb in (0.9, 3.4, 6.1):
        d = abs(lt - tb)
        if d < 0.12:
            blink = max(0.12, d / 0.12)
    for sx in (-26, 26):
        c.save(); c.translate(cx + sx, hy - 2); c.scale(1, blink)
        c.drawOval(skia.Rect.MakeXYWH(-12, -9, 24, 18), paint(BRANCO, a))
        c.drawCircle(2, 1, 6.5, paint(eye, a)); c.drawCircle(4, -1, 2, paint(BRANCO, a))
        c.restore()
        if fem:
            c.drawLine(cx + sx - 12, hy - 24, cx + sx + 10, hy - 26, paint(hair, a, stroke=4))
        else:
            c.drawLine(cx + sx - 14, hy - 22, cx + sx + 12, hy - 25 if sx < 0 else hy - 22, paint(hair, a, stroke=6))

    # nariz, bochechas e sorriso
    nose = skia.Path()
    nose.moveTo(cx + 2, hy + 4); nose.quadTo(cx + 12, hy + 26, cx - 4, hy + 28)
    c.drawPath(nose, paint(skin_dk, a, stroke=4))
    for sx in (-40, 40):
        c.drawCircle(cx + sx, hy + 30, 11, paint(hx("E8957C"), a * 0.45, blur=4))
    smile = skia.Path()
    smile.moveTo(cx - 22, hy + 42); smile.quadTo(cx, hy + 58, cx + 22, hy + 42)
    c.drawPath(smile, paint(hx("B5524A") if fem else lip, a, stroke=5))


def silhueta(c, cx, cy, R, a):
    """Silhueta neutra (sem cor de pele nem idade)."""
    if a <= 0.002:
        return
    c.drawCircle(cx, cy, R, paint(FUNDO_ILUS, a))
    clip = skia.Path()
    clip.addCircle(cx, cy, R)
    c.save()
    c.clipPath(clip, doAntiAlias=True)
    g = hx("8A97B0")
    c.drawCircle(cx, cy - R * 0.18, R * 0.36, paint(g, a))
    c.drawOval(skia.Rect.MakeXYWH(cx - R * 0.72, cy + R * 0.28, R * 1.44, R * 1.2), paint(g, a))
    c.restore()
    c.drawCircle(cx, cy, R, paint(CINZA, a, stroke=4))


def retrato(c, cx, cy, R, a, lt, pessoa):
    """Círculo com a caricatura (se houver dados) ou a silhueta."""
    if a <= 0.002:
        return
    if pessoa is None or pessoa.cor_pele is None or pessoa.idade_na_epoca is None:
        silhueta(c, cx, cy, R, a)
        return
    c.drawCircle(cx, cy, R + 10, paint(AMARELO, a * 0.25, blur=18))
    c.drawCircle(cx, cy, R, paint(FUNDO_ILUS, a))
    clip = skia.Path()
    clip.addCircle(cx, cy, R)
    c.save()
    c.clipPath(clip, doAntiAlias=True)
    c.translate(cx, cy)
    c.scale(R / 150, R / 150)
    caricatura(c, 0, 0, a, lt, pessoa.cor_pele, pessoa.idade_na_epoca, pessoa.genero or "masculino")
    c.restore()
    c.drawCircle(cx, cy, R, paint(AMARELO, a, stroke=5))
