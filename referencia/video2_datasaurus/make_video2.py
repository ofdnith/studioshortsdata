#!/usr/bin/env python3
"""Datasaurus + Quarteto de Anscombe — Reels 1080x1920, 30 fps, sincronizado à narração.
uso: python3 make_video2.py preview T [T ...]  |  python3 make_video2.py render
"""
import json, math, os, subprocess, sys
import numpy as np, pandas as pd, skia
from scipy.optimize import linear_sum_assignment

W, H, FPS = 1080, 1920, 30
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
SCHED = json.load(open(os.path.join(HERE, "narr", "sched.json")))
TOTAL = SCHED["total"]
SEG = {s["id"]: s for s in SCHED["seg"]}
ORDER = [s["id"] for s in SCHED["seg"]]
def S(i): return SEG[i]["start"]
def E(i): return SEG[i]["end"]
def NEXT(i):
    j = ORDER.index(i) + 1
    return S(ORDER[j]) if j < len(ORDER) else TOTAL

# ---------- estilo ----------
FONT_DIR = "/usr/share/fonts/opentype/inter/"
TF = {w: skia.Typeface.MakeFromFile(FONT_DIR + f"Inter-{w}.otf") for w in ["Medium", "SemiBold", "Bold", "ExtraBold", "Black"]}
def hx(s): s = s.lstrip("#"); return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))
BG = hx("0B1220"); GRIDC = hx("1B263C"); WHITE = hx("F4F6FB"); GREY = hx("97A3B8")
RED = hx("FF4D5E"); AMBER = hx("FFC145"); GREEN = hx("3DDC97"); CYAN = hx("62C7FF")
PANEL = hx("121B2E"); PANEL_LN = hx("24314C"); DOT = hx("E9EEF7")

def C(rgb, a=1.0): return skia.ColorSetARGB(int(round(255 * max(0, min(1, a)))), *rgb)
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease_out(x): x = clamp(x); return 1 - (1 - x) ** 3
def ease_io(x): x = clamp(x); return x * x * (3 - 2 * x)
def back_out(x):
    x = clamp(x); c1 = 1.9; return 1 + (c1 + 1) * (x - 1) ** 3 + c1 * (x - 1) ** 2
def paint(rgb, a=1.0, stroke=None, blur=None):
    p = skia.Paint(AntiAlias=True, Color=C(rgb, a))
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style); p.setStrokeWidth(stroke); p.setStrokeCap(skia.Paint.kRound_Cap)
    if blur: p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    return p

_f = {}
def font(w, s):
    if (w, s) not in _f:
        f = skia.Font(TF[w], s); f.setSubpixel(True); f.setEdging(skia.Font.Edging.kAntiAlias); _f[(w, s)] = f
    return _f[(w, s)]
def segs(line): return [(p, i % 2 == 1) for i, p in enumerate(line.split("*")) if p]
def lw(line, f): return sum(f.measureText(t) for t, _ in segs(line))
def draw_lines(c, lines, top, size, weight="ExtraBold", color=WHITE, accent=AMBER, alpha=1.0, lh=1.17,
               x=W / 2, align="center", maxw=920):
    while max(lw(l, font(weight, size)) for l in lines) > maxw and size > 10: size -= 1
    f = font(weight, size)
    for i, line in enumerate(lines):
        tw = lw(line, f); xx = x - tw / 2 if align == "center" else x
        base = top + i * size * lh + size * 0.80
        for t, acc in segs(line):
            c.drawString(t, xx, base, f, paint(accent if acc else color, alpha)); xx += f.measureText(t)

def vis(t, t0, t1, fin=0.22, fout=0.2):
    """0..1 de visibilidade com entrada/saída; devolve (alpha, e_entrada)."""
    e = ease_out((t - t0) / fin)
    a = e * (1 - ease_io((t - t1) / fout)) if t1 is not None else e
    return a, e

def title(c, t, lines, t0, t1, top=270, size=80, slide=26, **kw):
    a, e = vis(t, t0, t1)
    if a > 0.002: draw_lines(c, lines, top + (1 - e) * slide, size, alpha=a, **kw)

def pill(c, text, cx, cy, size, bg, fg, alpha=1.0, weight="Bold", h=None):
    f = font(weight, size); tw = f.measureText(text); h = h or size * 2.0; px = size * 0.9
    r = skia.Rect.MakeXYWH(cx - tw / 2 - px, cy - h / 2, tw + 2 * px, h)
    c.drawRRect(skia.RRect.MakeRectXY(r, h / 2, h / 2), paint(bg, alpha))
    c.drawString(text, cx - tw / 2, cy + size * 0.36, f, paint(fg, alpha))

# ---------- dados ----------
DS = pd.read_csv(os.path.join(HERE, "data", "DatasaurusDozen.tsv"), sep="\t")
AN = pd.read_csv(os.path.join(HERE, "data", "anscombe.csv"))
CHAIN = ["dino", "star", "circle", "bullseye", "x_shape", "v_lines", "h_lines", "slant_up", "dots",
         "high_lines", "wide_lines", "away", "slant_down", "dino"]
NOME = {"dino": "dinossauro", "star": "estrela", "circle": "círculo", "bullseye": "alvo", "x_shape": "xis",
        "v_lines": "linhas verticais", "h_lines": "linhas horizontais", "slant_up": "diagonal", "dots": "pontos",
        "high_lines": "faixas", "wide_lines": "moldura", "away": "nuvem", "slant_down": "diagonal invertida"}
ORD = []
prev = None
for name in CHAIN:
    pts = DS[DS.dataset == name][["x", "y"]].to_numpy()
    if prev is not None:
        cost = ((prev[:, None, :] - pts[None, :, :]) ** 2).sum(-1)
        r, cidx = linear_sum_assignment(cost); pts = pts[cidx]
    ORD.append(pts); prev = pts
ANS = {k: g[["x", "y"]].to_numpy() for k, g in AN.groupby("dataset")}

# ---------- gráficos ----------
def panel(c, x, y, w, h, alpha=1.0, grid=4):
    r = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), 26, 26)
    c.drawRRect(r, paint(PANEL, alpha)); c.drawRRect(r, paint(PANEL_LN, alpha, stroke=2))
    for i in range(1, grid):
        gx = x + w * i / grid; gy = y + h * i / grid
        c.drawLine(gx, y + 14, gx, y + h - 14, paint(GRIDC, alpha * 0.8, stroke=1.5))
        c.drawLine(x + 14, gy, x + w - 14, gy, paint(GRIDC, alpha * 0.8, stroke=1.5))

def mapper(x, y, w, h, xr, yr, pad=36):
    def f(px, py):
        return (x + pad + (px - xr[0]) / (xr[1] - xr[0]) * (w - 2 * pad),
                y + h - pad - (py - yr[0]) / (yr[1] - yr[0]) * (h - 2 * pad))
    return f

def dots(c, pts, m, r, alpha=1.0, color=DOT, pop=None):
    p = paint(color, alpha)
    for i, (px, py) in enumerate(pts):
        k = 1.0 if pop is None else pop[i]
        if k <= 0: continue
        sx, sy = m(px, py); c.drawCircle(sx, sy, r * (back_out(k) if k < 1 else 1), p)

# plot grande
BX, BY, BW, BH = 160, 690, 760, 760
BM = mapper(BX, BY, BW, BH, (10, 102), (-6, 104), pad=40)

def morph_pos(t, keys):
    """keys = [(t_inicio_morph, indice_no_CHAIN)], duração do morph md por item."""
    cur = ORD[keys[0][1]]
    for (t0, idx, md) in keys[1:]:
        if t < t0: break
        k = ease_io((t - t0) / md); cur = cur + (ORD[idx] - cur) * k if k < 1 else ORD[idx]
    return cur

STATS = [("MÉDIA x / y", "54,26 / 47,83"), ("DESVIO x / y", "16,76 / 26,93"), ("CORRELAÇÃO", "−0,06")]
def stats_panel(c, alpha, hl=(0, 0, 0), y=548, checks=0.0):
    if alpha <= 0.002: return
    cw = 300
    for i, (lab, val) in enumerate(STATS):
        cx = W / 2 + (i - 1) * cw
        h = hl[i]
        r = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(cx - cw / 2 + 8, y, cw - 16, 116), 22, 22)
        c.drawRRect(r, paint(PANEL, alpha)); c.drawRRect(r, paint(PANEL_LN, alpha, stroke=2))
        if h > 0: c.drawRRect(r, paint(AMBER, alpha * h, stroke=3.5))
        f = font("SemiBold", 24); tw = f.measureText(lab)
        c.drawString(lab, cx - tw / 2, y + 40, f, paint(GREY, alpha))
        f2 = font("ExtraBold", 36 if i < 2 else 40); vv = val; tw = f2.measureText(vv)
        col = tuple(int(a + (b - a) * h) for a, b in zip(WHITE, AMBER))
        c.drawString(vv, cx - tw / 2, y + 90, f2, paint(col, alpha))
        if checks > 0:
            k = ease_out((checks - i * 0.15) / 0.3)
            if k > 0:
                c.drawCircle(cx + cw / 2 - 26, y + 18, 17 * back_out(k), paint(GREEN, alpha))
                pc = paint(BG, alpha, stroke=4.5)
                c.drawLine(cx + cw / 2 - 34, y + 18, cx + cw / 2 - 28, y + 24, pc)
                c.drawLine(cx + cw / 2 - 28, y + 24, cx + cw / 2 - 18, y + 11, pc)

def tag(c, text, alpha, color=AMBER):
    if alpha > 0.002: pill(c, text, BX + 40 + font("Bold", 30).measureText(text) / 2 + 27, BY + 52, 30, (30, 24, 8), color, alpha)


# ---------- ilustrações e fontes (compartilhadas com o vídeo 3) ----------
def _ill():
    import importlib
    if "/home/claude/video3" not in sys.path: sys.path.insert(0, "/home/claude/video3")
    return importlib.import_module("make_video3")

def anscombe_card(c, a, e, lt):
    m = _ill(); cx, cy, R = 205, 500, 98
    c.save(); c.translate(0, (1 - e) * 20)
    c.drawCircle(cx, cy, R + 8, paint(AMBER, a * 0.25, blur=16))
    c.drawCircle(cx, cy, R, paint(hx("1A2540"), a))
    clip = skia.Path(); clip.addCircle(cx, cy, R)
    c.save(); c.clipPath(clip, doAntiAlias=True)
    c.translate(cx, cy); c.scale(R / 150, R / 150); m.caricature(c, 0, 0, a, lt, older=True)
    c.restore()
    c.drawCircle(cx, cy, R, paint(AMBER, a, stroke=5))
    x = 335
    def tx(s_, y, size, col, w):
        f = font(w, size); c.drawString(s_, x, y, f, paint(col, a))
    tx("Francis J. Anscombe", cy - 40, 44, WHITE, "ExtraBold")
    tx("estatístico inglês (1918–2001)", cy + 4, 28, GREY, "SemiBold")
    tx("1973 · 4 conjuntos, 11 pontos cada", cy + 46, 28, AMBER, "Bold")
    tx("fundou a Estatística de Yale", cy + 86, 26, GREY, "SemiBold")
    c.restore()

def authors_row(c, a, e):
    m = _ill()
    for i, name in enumerate(["Justin Matejka", "George Fitzmaurice"]):
        cx = 300 + i * 480; cy = 498 + (1 - e) * 20
        m.neutral_avatar(c, cx, cy, 62, a)
        f = font("Bold", 34); tw = f.measureText(name)
        c.drawString(name, cx - tw / 2, cy + 112, f, paint(WHITE, a))

def src(c, text): _ill().source_line(c, text, 1.0)

# ---------- seções ----------
B_A = (E("A3") + S("B1")) / 2; B_B = (E("B7") + S("C1")) / 2; B_C = (E("C4") + S("D1")) / 2
SECTIONS = [(0.0, B_A), (B_A, B_B), (B_B, B_C), (B_C, TOTAL)]

def sec_A(c, t):
    src(c, 'Fonte: Matejka & Fitzmaurice (2017), ACM CHI')
    title(c, t, ["Um *dinossauro*", "e uma *estrela*."], -0.5, S("A2") - 0.1, size=88)
    a2 = S("A2"); d2 = E("A2") - a2
    title(c, t, ["Mesmos números."], a2 - 0.05, S("A3") - 0.1, top=320, size=92)
    title(c, t, ["Como isso", "é *possível*?"], S("A3") - 0.05, None, size=88)
    hl = tuple(clamp((t - (a2 + d2 * f)) / 0.2) * (1 - clamp((t - (a2 + d2 * f + 1.1)) / 0.3)) for f in (0.0, 0.33, 0.68))
    stats_panel(c, 1.0, hl)
    panel(c, BX, BY, BW, BH)
    keys = [(0, 0, 0), (0.75, 1, 0.75), (S("A3") + 0.3, 2, 0.6), (S("A3") + 1.6, 3, 0.6)]
    dots(c, morph_pos(t, keys), BM, 8.5)
    nm = ["dinossauro", "estrela", "círculo", "alvo"]
    times = [-0.5, 1.3, S("A3") + 0.8, S("A3") + 2.1]
    for i, tt in enumerate(times):
        t1 = times[i + 1] - 0.45 if i + 1 < len(times) else None
        a, _ = vis(t, tt, t1, 0.25, 0.2); tag(c, nm[i], a)

# Anscombe: grade 2x2
GX = [130, 560]; GY = [690, 1080]; GW = 390
def g_map(i):
    x, y = GX[i % 2], GY[i // 2]
    return x, y, mapper(x, y, GW, GW, (2, 21), (2, 14.5), pad=34)
ROM = ["I", "II", "III", "IV"]
OUTL = {"III": (13.0, 12.74), "IV": (19.0, 12.5)}

def sec_B(c, t):
    src(c, 'Fonte: Anscombe, F. J. (1973), The American Statistician')
    b1 = S("B1")
    title(c, t, ["1973 · *Francis Anscombe*"], b1 - 0.05, S("B2") - 0.1, top=280, size=70)
    a, e = vis(t, b1 + 0.3, S("B2") - 0.1, 0.35)
    if a > 0: anscombe_card(c, a, e, t - b1)
    # estatísticas
    b2 = S("B2"); d2 = E("B2") - b2
    for j, (line, f) in enumerate([("média de x = *9*", 0.12), ("média de y = *7,5*", 0.4), ("correlação = *0,82*", 0.7)]):
        a, e = vis(t, b2 + d2 * f - 0.1, S("B3") - 0.1)
        if a > 0: draw_lines(c, [line], 262 + j * 92 + (1 - e) * 20, 66, alpha=a)
    title(c, t, ["Mesma reta:", "*y = 3 + 0,5x*"], S("B3") - 0.05, S("B4") - 0.1, size=78)
    caps = {"B4": ["I · *linear* com ruído"], "B5": ["II · uma *curva*"],
            "B6": ["III · um *outlier*", "entorta a reta"], "B7": ["IV · um ponto só", "*cria* a correlação"]}
    for k, lines in caps.items():
        title(c, t, lines, S(k) - 0.05, NEXT(k) - 0.1 if k != "B7" else None, size=74,
              accent=RED if k in ("B6", "B7") else AMBER)
    focus = None
    for i, k in enumerate(["B4", "B5", "B6", "B7"]):
        if S(k) - 0.1 <= t: focus = i
    for i, key in enumerate(ROM):
        x, y, m = g_map(i)
        ap = ease_out((t - (b1 + 0.2 + i * 0.12)) / 0.35)
        if ap <= 0: continue
        dim = 1.0
        if focus is not None:
            fk = ease_io((t - (S(["B4", "B5", "B6", "B7"][focus]) - 0.1)) / 0.25)
            dim = 1.0 if i == focus else 1 - 0.7 * min(1, fk if focus == 0 or True else 1)
        c.save(); c.translate(x + GW / 2, y + GW / 2); s = 0.94 + 0.06 * ap; c.scale(s, s); c.translate(-x - GW / 2, -y - GW / 2)
        al = ap * dim
        panel(c, x, y, GW, GW, al, grid=3)
        f = font("Black", 34); c.drawString(key, x + 22, y + 48, f, paint(GREY, al))
        # reta de regressão
        kr = ease_io((t - (S("B3") + i * 0.1)) / 0.6)
        if kr > 0:
            x0, x1 = 3, 3 + (20 - 3) * kr
            p0 = m(x0, 3 + 0.5 * x0); p1 = m(x1, 3 + 0.5 * x1)
            c.drawLine(*p0, *p1, paint(AMBER, al * 0.9, stroke=5))
        pts = ANS[key]
        pop = [clamp((t - (b1 + 1.0 + i * 0.25 + j * 0.06)) / 0.25) for j in range(len(pts))]
        dots(c, pts, m, 10, al, pop=pop)
        if key == "II":
            kc = ease_io((t - (S("B5") + 0.2)) / 0.7)
            if kc > 0:
                co = np.polyfit(pts[:, 0], pts[:, 1], 2); xs = np.linspace(4, 4 + 10 * kc, 40)
                path = skia.Path(); first = True
                for xv in xs:
                    sx, sy = m(xv, np.polyval(co, xv))
                    (path.moveTo if first else path.lineTo)(sx, sy); first = False
                c.drawPath(path, paint(GREEN, al, stroke=5))
        if key in OUTL:
            kk = "B6" if key == "III" else "B7"
            ko = ease_out((t - (S(kk) + 0.4)) / 0.4)
            if ko > 0:
                sx, sy = m(*OUTL[key])
                pulse = 0.5 + 0.5 * math.sin((t - S(kk)) * 6)
                c.drawCircle(sx, sy, 24 + 6 * pulse, paint(RED, al * ko, stroke=5))
        c.restore()

def sec_C(c, t):
    src(c, 'Fonte: Matejka & Fitzmaurice (2017), ACM CHI')
    c1 = S("C1")
    title(c, t, ["2017 · *Autodesk Research*"], c1 - 0.05, S("C2") - 0.1, top=280, size=68)
    a, e = vis(t, c1 + 0.5, S("C2") - 0.1, 0.35)
    if a > 0: authors_row(c, a, e)
    title(c, t, ["Milhares de", "*ajustes* minúsculos"], S("C2") - 0.05, S("C3") - 0.1, size=80)
    title(c, t, ["*Datasaurus*:", "13 gráficos, mesmos números"], S("C3") - 0.05, None, size=74)
    ap = ease_out((t - c1) / 0.4)
    # estatísticas: entram com C2, checks durante C2
    sa, _ = vis(t, S("C2") + 0.3, None, 0.3)
    stats_panel(c, sa, checks=(t - (S("C2") + 1.5)))
    panel(c, BX, BY, BW, BH, ap)
    base = ORD[0]
    if t < S("C3"):
        amp = clamp((t - S("C2")) / 1.0) * (1 - clamp((t - (S("C3") - 0.6)) / 0.6)) * 1.8
        ph = np.arange(len(base))
        jit = np.stack([np.sin(t * 7.3 + ph * 1.7) + 0.5 * np.sin(t * 13.1 + ph * 0.9),
                        np.cos(t * 6.1 + ph * 2.3) + 0.5 * np.sin(t * 11.7 + ph * 1.3)], 1) * amp
        pts = base + jit
        dots(c, pts, BM, 8.5, ap)
        a, _ = vis(t, c1 + 0.2, S("C3") + 0.1); tag(c, "dinossauro", a * ap)
        return
    # sequência de formas
    t0 = S("C3") + 1.2; t1 = E("C4") - 0.2
    n = len(CHAIN) - 1; step = (t1 - t0) / n
    md = min(0.55, step * 0.6)
    keys = [(0, 0, 0)] + [(t0 + i * step, i + 1, md) for i in range(n)]
    dots(c, morph_pos(t, keys), BM, 8.5)
    idx = 0
    for i in range(n):
        if t >= t0 + i * step + md * 0.6: idx = i + 1
    a = 1.0 if t > t0 + 0.2 else vis(t, S("C3"), None)[0]
    tag(c, f"{NOME[CHAIN[idx]]}", a)
    f = font("Bold", 28); s = f"{(idx % 13) + 1}/13"
    c.drawString(s, BX + BW - 40 - f.measureText(s), BY + 62, f, paint(GREY, a))

DOZEN = CHAIN[1:13]
def sec_D(c, t):
    src(c, 'Fonte: Matejka & Fitzmaurice (2017), ACM CHI')
    d1 = S("D1")
    title(c, t, ["Resumos *escondem*", "a forma dos dados."], d1 - 0.05, S("D2") - 0.1, size=80)
    title(c, t, ["Antes de calcular,", "*desenhe* seus dados."], S("D2") - 0.05, None, size=80)
    # small multiples
    ga, _ = vis(t, d1, S("D2") - 0.1, 0.3, 0.3)
    if ga > 0:
        cw, ch, gx0, gy0, gap = 266, 186, 131, 640, 16
        for i, name in enumerate(DOZEN):
            k = ease_out((t - (d1 + 0.15 + i * 0.09)) / 0.35)
            if k <= 0: continue
            x = gx0 + (i % 3) * (cw + gap); y = gy0 + (i // 3) * (ch + gap)
            al = ga * k
            r = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, cw, ch), 18, 18)
            c.drawRRect(r, paint(PANEL, al)); c.drawRRect(r, paint(PANEL_LN, al, stroke=2))
            m = mapper(x, y, cw, ch, (10, 102), (-6, 104), pad=16)
            dots(c, ORD[CHAIN.index(name)], m, 2.6, al)
    # dino desenhando de novo + CTA
    da, _ = vis(t, S("D2") + 0.1, None, 0.3)
    if da > 0:
        panel(c, BX, BY, BW, BH, da)
        n = len(ORD[0]); pop = [clamp((t - (S("D2") + 0.3 + j * 0.012)) / 0.2) for j in range(n)]
        dots(c, ORD[0], BM, 8.5, da, pop=pop)
    a, e = vis(t, S("D3") - 0.05, None, 0.3)
    if a > 0:
        pill(c, "Siga para mais curiosidades de dados", W / 2, 600 + (1 - e) * 20, 38, AMBER, BG, a, weight="ExtraBold", h=96)

SEC_FN = [sec_A, sec_B, sec_C, sec_D]

# ---------- fundo / frame ----------
def make_bg():
    s = skia.Surface.MakeRaster(skia.ImageInfo.Make(W, H, skia.kRGBA_8888_ColorType, skia.kPremul_AlphaType))
    c = s.getCanvas(); c.clear(C(BG))
    for yy in range(27, H, 54):
        for xx in range(27, W, 54): c.drawCircle(xx, yy, 2.2, paint(GRIDC))
    sh = skia.GradientShader.MakeRadial((W / 2, H * 0.48), H * 0.75, [C(BG, 0), C(BG, 0), C((4, 7, 14), 0.85)], [0, 0.45, 1])
    c.drawPaint(skia.Paint(Shader=sh))
    return s.makeImageSnapshot()

INFO = skia.ImageInfo.Make(W, H, skia.kRGBA_8888_ColorType, skia.kPremul_AlphaType)
def frame(surf, bg, t):
    c = surf.getCanvas(); c.drawImage(bg, 0, 0)
    for i, (a, b) in enumerate(SECTIONS):
        if a <= t < b or (i == len(SECTIONS) - 1 and t >= b):
            fin = 1.0 if i == 0 else ease_io((t - a) / 0.2)
            fout = 1.0 if i == len(SECTIONS) - 1 else 1 - ease_io((t - (b - 0.2)) / 0.2)
            al = min(fin, fout)
            if al < 0.999: c.saveLayerAlpha(None, int(255 * al))
            SEC_FN[i](c, t)
            if al < 0.999: c.restore()

def preview(ts):
    os.makedirs(os.path.join(HERE, "preview"), exist_ok=True)
    bg = make_bg(); surf = skia.Surface.MakeRaster(INFO)
    for ts_ in ts:
        frame(surf, bg, float(ts_)); p = os.path.join(HERE, "preview", f"t{float(ts_):05.1f}.png")
        surf.makeImageSnapshot().save(p, skia.kPNG); print(p)

def render():
    os.makedirs(OUT, exist_ok=True); bg = make_bg(); surf = skia.Surface.MakeRaster(INFO)
    nframes = round(TOTAL * FPS)
    cuts = [round(a * FPS) for a, _ in SECTIONS] + [nframes]
    names = []
    for k in range(len(SECTIONS)):
        name = f"sec{k}"; tmp = os.path.join(OUT, name + ".part.mp4"); fin = os.path.join(OUT, name + ".mp4")
        p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
                              "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                              "-pix_fmt", "yuv420p", "-r", str(FPS), tmp], stdin=subprocess.PIPE)
        for n in range(cuts[k], cuts[k + 1]):
            frame(surf, bg, n / FPS); p.stdin.write(surf.makeImageSnapshot().tobytes())
        p.stdin.close()
        if p.wait() != 0: sys.exit("falhou " + name)
        os.replace(tmp, fin); names.append(name); print("ok", name, flush=True)
    lst = os.path.join(OUT, "list.txt")
    open(lst, "w").write("".join(f"file '{n}.mp4'\n" for n in names))
    out = os.path.join(OUT, "datasaurus_v2.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
                    "-i", os.path.join(HERE, "narr", "narracao.wav"), "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out], check=True)
    print(out)

if __name__ == "__main__":
    preview(sys.argv[2:]) if sys.argv[1] == "preview" else render()
