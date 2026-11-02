#!/usr/bin/env python3
"""Paradoxo de Simpson — Reels 1080x1920, 30 fps, sincronizado à narração (Piper faber).
uso: python3 make_video3.py preview T [T ...]  |  python3 make_video3.py render
"""
import json, math, os, subprocess, sys
sys.path.insert(0, "/home/claude/video2")
import skia
from make_video2 import (W, H, FPS, C, clamp, ease_out, ease_io, back_out, paint, font, draw_lines, vis, title,
                         pill, make_bg, INFO, BG, WHITE, GREY, RED, AMBER, GREEN, PANEL, PANEL_LN, hx)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
SCHED = json.load(open(os.path.join(HERE, "narr", "sched.json")))
TOTAL = SCHED["total"]; SEG = {s["id"]: s for s in SCHED["seg"]}; ORDER = [s["id"] for s in SCHED["seg"]]
def S(i): return SEG[i]["start"]
def E(i): return SEG[i]["end"]
def NX(i):
    j = ORDER.index(i) + 1
    return S(ORDER[j]) if j < len(ORDER) else None

MEN = hx("62C7FF"); WOM = hx("C792FF"); EASY = hx("3DDC97"); HARD = hx("FF6B6B")
# UCBAdmissions (6 maiores departamentos)
DEPT = {"A": (62.1, 82.4, 825, 108), "B": (63.0, 68.0, 560, 25), "C": (36.9, 34.1, 325, 593),
        "D": (33.1, 34.9, 417, 375), "E": (27.7, 23.9, 191, 393), "F": (5.9, 7.0, 373, 341)}
MEN_TOT, WOM_TOT = 2691, 1835

def bar(c, x, y, w, h, color, a, r=12):
    if w <= 0.5 or a <= 0.002: return
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), min(r, w / 2), min(r, h / 2)), paint(color, a))

def text_at(c, s, x, y, size, color=WHITE, a=1.0, weight="ExtraBold", align="left"):
    if a <= 0.002: return
    f = font(weight, size); tw = f.measureText(s)
    xx = x - tw / 2 if align == "center" else (x - tw if align == "right" else x)
    c.drawString(s, xx, y, f, paint(color, a))

def check(c, x, y, r, a, color=GREEN):
    if a <= 0.002: return
    c.drawCircle(x, y, r, paint(color, a)); p = paint(BG, a, stroke=r * 0.26)
    c.drawLine(x - r * 0.45, y, x - r * 0.12, y + r * 0.33, p); c.drawLine(x - r * 0.12, y + r * 0.33, x + r * 0.45, y - r * 0.35, p)

def legend(c, a, y=1462):
    if a <= 0.002: return
    for i, (col, lab) in enumerate([(MEN, "Homens"), (WOM, "Mulheres")]):
        x = W / 2 - 200 + i * 230
        c.drawCircle(x, y - 12, 13, paint(col, a)); text_at(c, lab, x + 24, y, 34, GREY, a, "SemiBold")

# ---------- seções ----------
B_A = (E("A3") + S("B1")) / 2; B_B = (E("B3") + S("C1")) / 2; B_C = (E("C3") + S("D1")) / 2
B_D = (E("D2") + S("E1")) / 2; B_E = (E("E3") + S("F1")) / 2
SECTIONS = [(0.0, B_A), (B_A, B_B), (B_B, B_C), (B_C, B_D), (B_D, B_E), (B_E, TOTAL)]

def sec_A(c, t):
    source_line(c, "Fonte: Bickel, Hammel & O'Connell (1975), Science", 1.0)
    title(c, t, ["Berkeley *discriminava*", "mulheres?"], -0.5, S("A2") - 0.1, size=84)
    a, e = vis(t, S("A1") + 1.2, S("A2") - 0.1)
    if a > 0: draw_lines(c, ["4.526 candidatos"], 500 + (1 - e) * 16, 44, weight="SemiBold", color=GREY, alpha=a)
    berkeley_scene(c, vis(t, -1.0, S("A2") - 0.3, 0.3, 0.3)[0], t + 1.5)
    title(c, t, ["Aprovados nos 6 maiores", "departamentos"], S("A2") - 0.05, S("A3") - 0.1, size=70)
    title(c, t, ["Caso *encerrado*?"], S("A3") - 0.05, None, top=300, size=88)
    base = 1400; scale = 15.0   # px por ponto percentual
    for i, (lab, v, col) in enumerate([("Homens", 44.5, MEN), ("Mulheres", 30.4, WOM)]):
        cx = 330 + i * 420
        ap = ease_out((t - (S("A2") - 0.1 + i * 0.15)) / 0.4)
        grow = ease_io((t - (S("A2") - 0.05 + i * 0.2)) / 0.6)
        cnt = ease_io((t - (S("A2") + 0.3 + i * 2.6)) / 0.6)
        hgt = v * scale * grow
        bar(c, cx - 140, base - hgt, 280, hgt, col, ap, r=18)
        c.drawLine(cx - 170, base, cx + 170, base, paint(PANEL_LN, ap, stroke=3))
        text_at(c, lab, cx, base + 62, 44, GREY, ap, "Bold", "center")
        if grow > 0:
            lab_v = "?" if cnt <= 0 else f"{int(v * cnt + 0.5)}%"
            text_at(c, lab_v, cx, base - hgt - 26, 96, col if cnt > 0 else GREY, ap * grow, "Black", "center")
    # carimbo "NÃO"
    k = ease_out((t - (S("A3") + 0.75)) / 0.3)
    if k > 0:
        c.save(); c.translate(W / 2, 1060); c.rotate(-12); s = 1.6 - 0.6 * back_out((t - (S("A3") + 0.75)) / 0.3); c.scale(s, s)
        f = font("Black", 150); tw = f.measureText("NÃO")
        r = skia.Rect.MakeXYWH(-tw / 2 - 40, -125, tw + 80, 170)
        c.drawRRect(skia.RRect.MakeRectXY(r, 20, 20), paint(BG, 0.75 * k))
        c.drawRRect(skia.RRect.MakeRectXY(r, 20, 20), paint(RED, k, stroke=10))
        c.drawString("NÃO", -tw / 2, 12, f, paint(RED, k)); c.restore()

ROW_Y0, ROW_H = 640, 128; BX0, BMAX = 210, 620
def sec_B(c, t):
    source_line(c, "Fonte: Bickel, Hammel & O'Connell (1975), Science", 1.0)
    title(c, t, ["Separando por", "*departamento*…"], S("B1") - 0.05, S("B2") - 0.1, size=80)
    title(c, t, ["Elas na frente", "em *4 de 6*"], S("B2") - 0.05, S("B3") - 0.1, size=84, accent=GREEN)
    title(c, t, ["Depto. A:", "*82%* × 62%"], S("B3") - 0.05, None, size=84, accent=WOM)
    fa = ease_io((t - (S("B3") + 0.1)) / 0.3)
    for i, (d, (m, w, _, _)) in enumerate(DEPT.items()):
        y = ROW_Y0 + i * ROW_H
        ap = ease_out((t - (S("B1") + 0.2 + i * 0.16)) / 0.4)
        if ap <= 0: continue
        al = ap * (1 - 0.7 * fa if d != "A" else 1)
        text_at(c, d, 120, y + 78, 64, WHITE, al, "Black", "center")
        g = ease_io((t - (S("B1") + 0.35 + i * 0.16)) / 0.6)
        for j, (v, col) in enumerate([(m, MEN), (w, WOM)]):
            yy = y + 14 + j * 52; bw = BMAX * v / 100 * g
            bar(c, BX0, yy, max(bw, 6), 42, col, al, r=10)
            text_at(c, f"{v * g:.0f}%", BX0 + max(bw, 6) + 14, yy + 34, 34, col, al, "Bold")
        if w > m:
            check(c, 990, y + 62, 26, al * ease_out((t - (S("B2") + 0.3 + i * 0.12)) / 0.3))
    legend(c, ease_out((t - S("B1") - 0.5) / 0.4))

def stacked(c, y, h, shares, a, hl_set, hl_k, label, label_col):
    x0, wfull = 120, 840
    text_at(c, label, x0, y - 22, 46, label_col, a, "ExtraBold")
    x = x0
    for d, sh in shares:
        w = wfull * sh
        easy = d in ("A", "B"); col = EASY if easy else HARD
        dim = 1.0 if hl_k == 0 or d in hl_set else 1 - 0.65 * hl_k
        bar(c, x + 2, y, w - 4, h, col, a * dim * (0.92 if easy else 0.85), r=10)
        if w > 50: text_at(c, d, x + w / 2, y + h / 2 + 16, 44, BG, a * dim, "Black", "center")
        x += w

def sec_C(c, t):
    source_line(c, "Fonte: Bickel, Hammel & O'Connell (1975), Science", 1.0)
    title(c, t, ["Onde cada um", "*se candidatou*?"], S("C1") - 0.05, S("C2") - 0.1, size=82)
    title(c, t, ["Metade dos homens:", "depto. *fáceis*"], S("C2") - 0.05, S("C3") - 0.1, size=80, accent=EASY)
    title(c, t, ["93% das mulheres:", "os mais *concorridos*"], S("C3") - 0.05, None, size=80, accent=HARD)
    ap = ease_out((t - (S("C1") + 0.4)) / 0.5)
    ms = [(d, v[2] / MEN_TOT) for d, v in DEPT.items()]; ws = [(d, v[3] / WOM_TOT) for d, v in DEPT.items()]
    k2 = ease_io((t - (S("C2") + 0.2)) / 0.3) * (1 - ease_io((t - (S("C3") - 0.1)) / 0.3))
    k3 = ease_io((t - (S("C3") + 0.2)) / 0.3)
    stacked(c, 780, 150, ms, ap, {"A", "B"}, k2, "Homens", MEN)
    stacked(c, 1100, 150, ws, ease_out((t - (S("C1") + 0.7)) / 0.5), {"C", "D", "E", "F"}, k3, "Mulheres", WOM)
    if k2 > 0: pill(c, "52% em A e B", 120 + 840 * 0.515 / 2, 965, 34, (8, 40, 28), EASY, k2)
    if k3 > 0: pill(c, "93% em C, D, E e F", 120 + 840 * (0.073 + 0.927 / 2), 1285, 34, (48, 14, 14), HARD, k3)
    la = ease_out((t - (S("C1") + 1.4)) / 0.4)
    if la > 0:
        for i, (col, lab) in enumerate([(EASY, "fáceis: ~63% aprovados"), (HARD, "concorridos: 6–35%")]):
            yy = 1400 + i * 56
            bar(c, 150, yy - 28, 34, 34, col, la, r=8); text_at(c, lab, 200, yy, 36, GREY, la, "SemiBold")

def node(c, cx, cy, label, col, a):
    f = font("ExtraBold", 40); tw = f.measureText(label); w = tw + 70
    r = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(cx - w / 2, cy - 48, w, 96), 26, 26)
    c.drawRRect(r, paint(PANEL, a)); c.drawRRect(r, paint(col, a, stroke=4))
    c.drawString(label, cx - tw / 2, cy + 14, f, paint(WHITE, a))

def arrow(c, x0, y0, x1, y1, col, a, k=1.0, dash=False, w=6):
    if a <= 0.002 or k <= 0: return
    x1 = x0 + (x1 - x0) * k; y1 = y0 + (y1 - y0) * k
    p = paint(col, a, stroke=w)
    if dash: p.setPathEffect(skia.DashPathEffect.Make([18, 14], 0))
    c.drawLine(x0, y0, x1, y1, p)
    ang = math.atan2(y1 - y0, x1 - x0); L = 24
    path = skia.Path(); path.moveTo(x1, y1)
    path.lineTo(x1 - L * math.cos(ang - 0.45), y1 - L * math.sin(ang - 0.45))
    path.lineTo(x1 - L * math.cos(ang + 0.45), y1 - L * math.sin(ang + 0.45)); path.close()
    c.drawPath(path, paint(col, a))

def caricature(c, cx, cy, a, lt, older=False):
    """Caricatura genérica: homem branco, ~29 anos, anos 1950 (terno e gravata). Não reproduz traços reais."""
    skin = hx("F2C7A5"); skin_dk = hx("D9A47F"); hair = hx("B8B8BC") if older else hx("4A3426"); suit = hx("3B4560")
    shirt = hx("F4F6FB"); lip = hx("9C4A3C"); eye = hx("2A1E1A")
    bob = math.sin(lt * 2.2) * 3
    # corpo
    body = skia.Path(); body.addRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(cx - 115, cy + 62, 230, 200), 80, 80))
    c.drawPath(body, paint(suit, a))
    collar = skia.Path(); collar.moveTo(cx - 30, cy + 64); collar.lineTo(cx, cy + 118); collar.lineTo(cx + 30, cy + 64); collar.close()
    c.drawPath(collar, paint(shirt, a))
    lap = paint(hx("2C3449"), a, stroke=4)
    c.drawLine(cx - 30, cy + 66, cx - 8, cy + 150, lap); c.drawLine(cx + 30, cy + 66, cx + 8, cy + 150, lap)
    tie = skia.Path(); tie.moveTo(cx - 8, cy + 74); tie.lineTo(cx + 8, cy + 74); tie.lineTo(cx + 12, cy + 132); tie.lineTo(cx, cy + 146); tie.lineTo(cx - 12, cy + 132); tie.close()
    c.drawPath(tie, paint(AMBER, a))
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(cx - 20, cy + 30, 40, 42), 10, 10), paint(skin_dk, a))
    # cabeça (caricatura: cabeça grande)
    hy = cy - 30 + bob; HW, HH = 70, 80
    c.drawCircle(cx - HW + 2, hy + 8, 15, paint(skin_dk, a)); c.drawCircle(cx + HW - 2, hy + 8, 15, paint(skin_dk, a))
    head = skia.Path(); head.addOval(skia.Rect.MakeXYWH(cx - HW, hy - HH, 2 * HW, 2 * HH))
    c.drawPath(head, paint(skin, a))
    # cabelo curto com risca lateral
    cap = skia.Path(); cap.addOval(skia.Rect.MakeXYWH(cx - HW - 5, hy - HH - 12, 2 * HW + 10, 2 * HH))
    cut = skia.Path(); cut.addRect(skia.Rect.MakeLTRB(cx - HW - 20, hy - HH - 30, cx + HW + 20, hy - (66 if older else 50)))
    hair_p = skia.Op(cap, cut, skia.PathOp.kIntersect_PathOp)
    side = skia.Path(); side.addRect(skia.Rect.MakeLTRB(cx - HW - 6, hy - 55, cx - HW + 9, hy - 12))
    side2 = skia.Path(); side2.addRect(skia.Rect.MakeLTRB(cx + HW - 9, hy - 55, cx + HW + 6, hy - 12))
    hair_p = skia.Op(hair_p, side, skia.PathOp.kUnion_PathOp); hair_p = skia.Op(hair_p, side2, skia.PathOp.kUnion_PathOp)
    hair_p = skia.Op(hair_p, cap, skia.PathOp.kIntersect_PathOp)
    if older:   # entradas: tira o topo da frente
        bald = skia.Path(); bald.addOval(skia.Rect.MakeXYWH(cx - 46, hy - HH - 4, 92, 46))
        hair_p = skia.Op(hair_p, bald, skia.PathOp.kDifference_PathOp)
    c.drawPath(hair_p, paint(hair, a))
    if older:
        wl = paint(skin_dk, a * 0.8, stroke=2.5)
        for k in range(2):
            p = skia.Path(); p.moveTo(cx - 28, hy - 44 + k * 9); p.quadTo(cx, hy - 50 + k * 9, cx + 28, hy - 44 + k * 9); c.drawPath(p, wl)
        for sx in (-1, 1):
            p = skia.Path(); p.moveTo(cx + sx * 20, hy + 22); p.quadTo(cx + sx * 30, hy + 38, cx + sx * 28, hy + 50); c.drawPath(p, wl)
    swoop = skia.Path(); swoop.moveTo(cx - 25, hy - HH - 4)
    swoop.cubicTo(cx + 25, hy - HH - 22, cx + 72, hy - 80, cx + 66, hy - 48)
    swoop.cubicTo(cx + 40, hy - 64, cx + 5, hy - 62, cx - 25, hy - 60); swoop.close()
    if not older:
        c.drawPath(swoop, paint(hair, a))
        c.drawLine(cx - 24, hy - HH + 4, cx - 30, hy - 58, paint(hx("2E2018"), a, stroke=3))   # risca
    # olhos (piscam)
    blink = 1.0
    for tb in (0.9, 3.4):
        d = abs(lt - tb)
        if d < 0.12: blink = max(0.12, d / 0.12)
    for sx in (-26, 26):
        c.save(); c.translate(cx + sx, hy - 2); c.scale(1, blink)
        c.drawOval(skia.Rect.MakeXYWH(-12, -9, 24, 18), paint(WHITE, a))
        c.drawCircle(2, 1, 6.5, paint(eye, a)); c.drawCircle(4, -1, 2, paint(WHITE, a))
        c.restore()
        c.drawLine(cx + sx - 14, hy - 22, cx + sx + 12, hy - 25 if sx < 0 else hy - 22, paint(hair, a, stroke=6))
    # nariz, bochechas e sorriso
    nose = skia.Path(); nose.moveTo(cx + 2, hy + 4); nose.quadTo(cx + 12, hy + 26, cx - 4, hy + 28)
    c.drawPath(nose, paint(skin_dk, a, stroke=4))
    c.drawCircle(cx - 40, hy + 30, 11, paint(hx("E8957C"), a * 0.45, blur=4)); c.drawCircle(cx + 40, hy + 30, 11, paint(hx("E8957C"), a * 0.45, blur=4))
    smile = skia.Path(); smile.moveTo(cx - 22, hy + 42); smile.quadTo(cx, hy + 58, cx + 22, hy + 42)
    c.drawPath(smile, paint(lip, a, stroke=5))

def neutral_avatar(c, cx, cy, R, a):
    """Silhueta neutra (sem cor de pele nem idade) para quem não temos esses dados."""
    if a <= 0.002: return
    c.drawCircle(cx, cy, R, paint(hx("1A2540"), a))
    clip = skia.Path(); clip.addCircle(cx, cy, R)
    c.save(); c.clipPath(clip, doAntiAlias=True)
    g = hx("8A97B0")
    c.drawCircle(cx, cy - R * 0.18, R * 0.36, paint(g, a))
    c.drawOval(skia.Rect.MakeXYWH(cx - R * 0.72, cy + R * 0.28, R * 1.44, R * 1.2), paint(g, a))
    c.restore()
    c.drawCircle(cx, cy, R, paint(GREY, a, stroke=4))

def source_line(c, text, a, y=1518):
    if a <= 0.002: return
    f = font("SemiBold", 26)
    while f.measureText(text) > 900: f = font("SemiBold", int(f.getSize()) - 1)
    tw = f.measureText(text)
    c.drawString(text, W / 2 - tw / 2, y, f, paint(GREY, a * 0.95))

def person_card(c, a, e, lt):
    """Ilustração genérica (sem traços do rosto) + cartão com o nome."""
    if a <= 0.002: return
    cx, cy, R = 250, 735, 150
    dy = (1 - e) * 24
    c.save(); c.translate(0, dy)
    c.drawCircle(cx, cy, R + 10, paint(AMBER, a * 0.25, blur=18))
    c.drawCircle(cx, cy, R, paint(hx("1A2540"), a))
    clip = skia.Path(); clip.addCircle(cx, cy, R)
    c.save(); c.clipPath(clip, doAntiAlias=True)
    caricature(c, cx, cy, a, lt)
    c.restore()
    c.drawCircle(cx, cy, R, paint(AMBER, a, stroke=5))
    x = 440
    text_at(c, "Edward H. Simpson", x, cy - 62, 46, WHITE, a, "ExtraBold")
    text_at(c, "estatístico britânico (1922–2019)", x, cy - 10, 30, GREY, a, "SemiBold")
    text_at(c, "1951 · descreveu o paradoxo", x, cy + 40, 32, AMBER, a, "Bold")
    text_at(c, "decifrou códigos na 2ª Guerra", x, cy + 88, 30, GREY, a, "SemiBold")
    c.restore()

CA = [(-124.2, 42.0), (-120.0, 42.0), (-120.0, 39.0), (-114.6, 35.1), (-114.7, 32.7), (-117.1, 32.5), (-117.3, 33.2),
      (-118.4, 33.8), (-119.2, 34.3), (-120.6, 34.6), (-120.9, 35.4), (-121.9, 36.6), (-122.4, 37.2), (-122.5, 37.8),
      (-123.0, 38.0), (-123.7, 38.9), (-123.8, 39.8), (-124.4, 40.4), (-124.1, 41.0)]
BERK = (-122.27, 37.87)

def berkeley_scene(c, a, lt):
    """Ilustração do campus: torre Sather (Campanile), colinas e mapa da Califórnia."""
    if a <= 0.002: return
    X, Y, PW, PH = 120, 640, 840, 790
    rr = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(X, Y, PW, PH), 34, 34)
    c.save(); c.clipRRect(rr, doAntiAlias=True)
    if a < 0.999: c.saveLayerAlpha(None, int(255 * a))
    sky = skia.GradientShader.MakeLinear([(0, Y), (0, Y + PH)], [C(hx("101A33")), C(hx("2B2F5C")), C(hx("6B4A5E"))], [0, 0.6, 1])
    c.drawRect(skia.Rect.MakeXYWH(X, Y, PW, PH), skia.Paint(Shader=sky))
    for i in range(26):   # estrelas
        sx = X + (i * 157) % PW; sy = Y + 30 + (i * 89) % 330
        tw = 0.4 + 0.6 * (0.5 + 0.5 * math.sin(lt * 3 + i))
        c.drawCircle(sx, sy, 2.4, paint(WHITE, 0.6 * tw))
    c.drawCircle(X + 640, Y + 560, 160, paint(AMBER, 0.18, blur=60))   # brilho do pôr do sol
    par = lt * 6
    def hills(base, amp, col, ph, sh):
        p = skia.Path(); p.moveTo(X - 20, Y + PH)
        for k in range(0, 46):
            hx_ = X - 20 + k * (PW + 40) / 45
            p.lineTo(hx_, Y + base - amp * (0.6 * math.sin(k * 0.33 + ph) + 0.4 * math.sin(k * 0.71 + ph * 2)) - sh)
        p.lineTo(X + PW + 20, Y + PH); p.close(); c.drawPath(p, paint(col))
    c.save(); c.translate(-par * 0.3, 0); hills(520, 60, hx("2A3560"), 0.4, 0); c.restore()
    c.save(); c.translate(-par * 0.6, 0); hills(610, 40, hx("1E2747"), 1.7, 0); c.restore()
    # torre
    rise = ease_out(lt / 0.8)
    tx = X + 520; base = Y + PH - 90; th = 470 * rise
    stone = hx("D9DEE8"); shade = hx("A9B2C6"); dark = hx("1A2238")
    if th > 10:
        c.save(); c.translate(0, (1 - rise) * 60)
        sw = 74
        c.drawRect(skia.Rect.MakeLTRB(tx - sw / 2, base - 330, tx + sw / 2, base), paint(stone))
        c.drawRect(skia.Rect.MakeLTRB(tx + sw / 2 - 18, base - 330, tx + sw / 2, base), paint(shade))
        for k in range(5):   # frisos
            yy = base - 60 - k * 55
            c.drawRect(skia.Rect.MakeLTRB(tx - sw / 2, yy, tx + sw / 2, yy + 4), paint(shade))
        bw = 96; bt = base - 430   # campanário
        c.drawRect(skia.Rect.MakeLTRB(tx - bw / 2, bt, tx + bw / 2, base - 330), paint(stone))
        c.drawRect(skia.Rect.MakeLTRB(tx - bw / 2 - 6, base - 336, tx + bw / 2 + 6, base - 326), paint(shade))
        for j in range(3):   # aberturas em arco
            ox = tx - 30 + j * 30
            p = skia.Path(); p.addRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(ox - 9, bt + 40, 18, 52), 9, 9)); c.drawPath(p, paint(dark))
        c.drawCircle(tx, base - 360, 15, paint(dark)); c.drawCircle(tx, base - 360, 11, paint(hx("F2E3B8")))
        c.drawLine(tx, base - 360, tx, base - 368, paint(dark, stroke=2.5)); c.drawLine(tx, base - 360, tx + 6, base - 360, paint(dark, stroke=2.5))
        c.drawRect(skia.Rect.MakeLTRB(tx - bw / 2 - 6, bt - 8, tx + bw / 2 + 6, bt + 2), paint(shade))
        roof = skia.Path(); roof.moveTo(tx - bw / 2, bt - 6); roof.lineTo(tx, bt - 110); roof.lineTo(tx + bw / 2, bt - 6); roof.close()
        c.drawPath(roof, paint(hx("8FA0BC")))
        c.drawCircle(tx, bt - 116, 6, paint(AMBER))
        c.restore()
    # árvores e chão
    c.drawRect(skia.Rect.MakeXYWH(X, Y + PH - 95, PW, 95), paint(hx("162038")))
    for k in range(9):
        cxk = X + 40 + k * 100 + (30 if k % 2 else 0)
        c.drawCircle(cxk, Y + PH - 100, 44 + (k % 3) * 8, paint(hx("1F3B3A")))
    # mapa da Califórnia
    mx, my, mw, mh = X + 40, Y + 40, 230, 270
    m = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(mx, my, mw, mh), 22, 22)
    c.drawRRect(m, paint(hx("0B1220"), 0.85)); c.drawRRect(m, paint(PANEL_LN, 1, stroke=2))
    def proj(lon, lat): return (mx + 20 + (lon + 124.6) / 10.3 * (mw - 40), my + 20 + (42.3 - lat) / 10.0 * (mh - 60))
    p = skia.Path(); p.moveTo(*proj(*CA[0]))
    for q in CA[1:]: p.lineTo(*proj(*q))
    p.close(); c.drawPath(p, paint(hx("2E3C5F"))); c.drawPath(p, paint(GREY, 0.8, stroke=2))
    bx, by = proj(*BERK)
    pk = ease_out((lt - 0.6) / 0.4)
    if pk > 0:
        pulse = (lt * 1.2) % 1.0
        c.drawCircle(bx, by, 8 + 22 * pulse, paint(RED, (1 - pulse) * 0.8 * pk, stroke=3))
        c.drawCircle(bx, by, 9 * back_out(pk), paint(RED, pk))
        text_at(c, "Califórnia", mx + mw / 2, my + mh - 18, 24, GREY, 1, "SemiBold", "center")
    if a < 0.999: c.restore()
    c.restore()
    c.drawRRect(rr, paint(PANEL_LN, a, stroke=2))
    k = ease_out((lt - 0.9) / 0.4)
    if k > 0: pill(c, "Universidade de Berkeley · 1973", W / 2, Y + PH - 46, 32, hx("0B1220"), AMBER, a * k)

def sec_D(c, t):
    source_line(c, 'Fonte: Simpson, E. H. (1951), Journal of the Royal Statistical Society', 1.0)
    title(c, t, ["Paradoxo", "de *Simpson*"], S("D1") - 0.05, None, size=100)
    pa, pe = vis(t, S("D1") + 0.15, S("D2") - 0.1, 0.35)
    person_card(c, pa, pe, t - S("D1"))
    a, e = vis(t, S("D1") + 1.8, S("D2") - 0.1)
    if a > 0:
        draw_lines(c, ["Uma tendência em cada grupo", "*se inverte* no total."], 905 + (1 - e) * 16, 46, weight="SemiBold", color=GREY, alpha=a, accent=AMBER)
        for i, (head, body, col) in enumerate([("Por departamento", "elas na frente em 4 de 6", WOM),
                                                ("No total", "eles na frente: 45% × 30%", MEN)]):
            k = ease_out((t - (S("D1") + 2.4 + i * 0.9)) / 0.4)
            if k <= 0: continue
            y = 1045 + i * 200 + (1 - k) * 24
            r = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(120, y, 840, 180), 30, 30)
            c.drawRRect(r, paint(PANEL, a * k)); c.drawRRect(r, paint(col, a * k, stroke=4))
            text_at(c, head, W / 2, y + 68, 38, GREY, a * k, "SemiBold", "center")
            text_at(c, body, W / 2, y + 135, 50, col, a * k, "ExtraBold", "center")
    a, e = vis(t, S("D2") - 0.05, None)
    if a > 0:
        draw_lines(c, ["Variável escondida:", "*o departamento*"], 560 + (1 - e) * 16, 54, weight="Bold", alpha=a)
        k = [ease_out((t - (S("D2") + 0.3 + i * 0.35)) / 0.35) for i in range(3)]
        node(c, 300, 900, "Gênero", WOM, a * k[0])
        node(c, 780, 1130, "Departamento", AMBER, a * k[1])
        node(c, 300, 1360, "Aprovação", GREEN, a * k[2])
        arrow(c, 380, 950, 640, 1080, AMBER, a, ease_io((t - (S("D2") + 0.9)) / 0.4))
        arrow(c, 640, 1180, 400, 1310, AMBER, a, ease_io((t - (S("D2") + 1.3)) / 0.4))
        kd = ease_io((t - (S("D2") + 1.8)) / 0.4)
        arrow(c, 300, 960, 300, 1290, GREY, a * 0.8, kd, dash=True, w=5)
        if kd > 0.9: text_at(c, "?", 335, 1145, 64, GREY, a, "Black")

KID = {"A": (93, 73, 78, 87, 263), "B": (87, 69, 83, 270, 80)}  # pequenas, grandes, total, n_peq, n_gra
def sec_E(c, t):
    source_line(c, 'Fonte: Charig et al. (1986), British Medical Journal', 1.0)
    title(c, t, ["Pedras nos rins", "· *1986* ·"], S("E1") - 0.05, S("E2") - 0.1, size=84)
    title(c, t, ["No total,", "*B parece melhor*"], S("E2") - 0.05, S("E3") - 0.1, size=84, accent=RED)
    title(c, t, ["A ficou com os", "*casos difíceis*"], S("E3") - 0.05, None, size=84)
    x0, cw, y0, rh = 230, 250, 650, 150
    cols = ["Pequenas", "Grandes", "Total"]
    ap = ease_out((t - (S("E1") + 0.3)) / 0.4)
    col_t = [S("E1") + 2.5, S("E1") + 3.8, S("E2") + 0.6]
    for j, name in enumerate(cols):
        a = ap if j < 2 else ease_out((t - col_t[2] + 0.3) / 0.4)
        text_at(c, name, x0 + cw * j + cw / 2, y0 + 50, 38, GREY if j < 2 else AMBER, a, "Bold", "center")
    for i, rname in enumerate(["A", "B"]):
        y = y0 + 80 + i * rh
        text_at(c, rname, 150, y + 98, 72, WHITE, ap, "Black", "center")
        for j in range(3):
            k = ease_out((t - col_t[j]) / 0.35)
            if k <= 0: continue
            v = KID[rname][j]; other = KID["B" if rname == "A" else "A"][j]; win = v > other
            x = x0 + cw * j + 12
            r = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y + 10, cw - 24, rh - 24), 22, 22)
            colw = (GREEN if j < 2 else AMBER) if win else PANEL_LN
            c.drawRRect(r, paint(PANEL, k)); c.drawRRect(r, paint(colw, k, stroke=4 if win else 2))
            text_at(c, f"{v}%", x + (cw - 24) / 2, y + 98, 64, (GREEN if j < 2 else AMBER) if win else GREY, k, "Black", "center")
    # composição dos casos
    ka = ease_out((t - (S("E3") + 0.3)) / 0.4)
    if ka > 0:
        for i, rname in enumerate(["A", "B"]):
            y = 1060 + i * 170
            npq, ngr = KID[rname][3], KID[rname][4]
            text_at(c, f"Tratamento {rname}", 120, y, 38, WHITE, ka, "Bold")
            g = ease_io((t - (S("E3") + 0.5 + i * 0.3)) / 0.6)
            wp = 840 * npq / 350 * g; wg = 840 * ngr / 350 * g
            bar(c, 120, y + 22, wp - 3, 74, hx("7FA6D9"), ka, r=10)
            bar(c, 120 + wp + 3, y + 22, wg - 3, 74, HARD, ka, r=10)
            if g > 0.8:
                text_at(c, f"{npq} pequenas", 140, y + 72, 30, BG, ka, "Bold")
                text_at(c, f"{ngr} grandes", 120 + wp + wg - 20, y + 72, 30, BG, ka, "Bold", "right")

def sec_F(c, t):
    title(c, t, ["Antes de confiar", "no *total*, pergunte:"], S("F1") - 0.05, None, size=78)
    a, e = vis(t, S("F1") + 2.2, None)
    if a > 0:
        draw_lines(c, ["“Que variável", "está *escondida*?”"], 640 + (1 - e) * 20, 92, weight="Black", alpha=a)
    for i, (case, var, col) in enumerate([("Berkeley", "o departamento", AMBER), ("Pedras nos rins", "o tamanho da pedra", HARD)]):
        k = ease_out((t - (S("F1") + 3.0 + i * 0.6)) / 0.4)
        if k <= 0: continue
        y = 930 + i * 210 + (1 - k) * 20
        r = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(120, y, 840, 170), 28, 28)
        c.drawRRect(r, paint(PANEL, k)); c.drawRRect(r, paint(col, k, stroke=3))
        text_at(c, case, 170, y + 70, 36, GREY, k, "SemiBold")
        text_at(c, "escondida: " + var, 170, y + 128, 46, col, k, "ExtraBold")
    a, e = vis(t, S("F2") - 0.05, None, 0.3)
    if a > 0:
        pill(c, "Siga para mais curiosidades de dados", W / 2, 1420 + (1 - e) * 20, 38, AMBER, BG, a, weight="ExtraBold", h=96)

FNS = [sec_A, sec_B, sec_C, sec_D, sec_E, sec_F]

def frame(surf, bg, t):
    c = surf.getCanvas(); c.drawImage(bg, 0, 0)
    for i, (a, b) in enumerate(SECTIONS):
        last = i == len(SECTIONS) - 1
        if a <= t < b or (last and t >= b):
            fin = 1.0 if i == 0 else ease_io((t - a) / 0.2)
            fout = 1.0 if last else 1 - ease_io((t - (b - 0.2)) / 0.2)
            al = min(fin, fout)
            if al < 0.999: c.saveLayerAlpha(None, int(255 * al))
            FNS[i](c, t)
            if al < 0.999: c.restore()

def preview(ts):
    os.makedirs(os.path.join(HERE, "preview"), exist_ok=True)
    bg = make_bg(); surf = skia.Surface.MakeRaster(INFO)
    for x in ts:
        frame(surf, bg, float(x)); p = os.path.join(HERE, "preview", f"t{float(x):05.1f}.png")
        surf.makeImageSnapshot().save(p, skia.kPNG)

def render():
    os.makedirs(OUT, exist_ok=True); bg = make_bg(); surf = skia.Surface.MakeRaster(INFO)
    nfr = round(TOTAL * FPS); cuts = [round(a * FPS) for a, _ in SECTIONS] + [nfr]; names = []
    for k in range(len(SECTIONS)):
        name = f"sec{k}"; tmp = os.path.join(OUT, name + ".part.mp4")
        p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
                              "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                              "-pix_fmt", "yuv420p", "-r", str(FPS), tmp], stdin=subprocess.PIPE)
        for n in range(cuts[k], cuts[k + 1]):
            frame(surf, bg, n / FPS); p.stdin.write(surf.makeImageSnapshot().tobytes())
        p.stdin.close()
        if p.wait() != 0: sys.exit("falhou " + name)
        os.replace(tmp, os.path.join(OUT, name + ".mp4")); names.append(name); print("ok", name, flush=True)
    lst = os.path.join(OUT, "list.txt"); open(lst, "w").write("".join(f"file '{n}.mp4'\n" for n in names))
    out = os.path.join(OUT, "paradoxo_de_simpson_v2.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
                    "-i", os.path.join(HERE, "narr", "narracao.wav"), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out], check=True)
    print(out)

if __name__ == "__main__":
    preview(sys.argv[2:]) if sys.argv[1] == "preview" else render()
