#!/usr/bin/env python3
"""Viés de sobrevivência — Reels 1080x1920, 30 fps, ~70 s.
uso: python3 make_video.py preview CENA:T [CENA:T ...]   -> PNGs em preview/
     python3 make_video.py render                          -> out/vies_de_sobrevivencia.mp4
"""
import math, os, random, subprocess, sys
import skia

W, H, FPS = 1080, 1920, 30
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
FONT_DIR = "/usr/share/fonts/opentype/inter/"
TF = {w: skia.Typeface.MakeFromFile(FONT_DIR + f"Inter-{w}.otf")
      for w in ["Medium", "SemiBold", "Bold", "ExtraBold", "Black"]}

# ---------- cores ----------
def hx(s): s = s.lstrip("#"); return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))
BG = hx("0B1220"); GRID = hx("1B263C")
WHITE = hx("F4F6FB"); GREY = hx("97A3B8")
PLANE = hx("D3DCEA"); PLANE_DK = hx("56657F"); WINDOW = hx("3F4E6B")
RED = hx("FF4D5E"); RED_DK = hx("5A0E19")
AMBER = hx("FFC145"); GREEN = hx("3DDC97")
CARD = hx("16213A")

def C(rgb, a=1.0):
    a = max(0.0, min(1.0, a))
    return skia.ColorSetARGB(int(round(255 * a)), *rgb)

def lerp(a, b, t): return a + (b - a) * t
def lerpc(c1, c2, t): return tuple(int(lerp(x, y, t)) for x, y in zip(c1, c2))
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease_out(x): x = clamp(x); return 1 - (1 - x) ** 3
def ease_io(x): x = clamp(x); return 3 * x * x - 2 * x * x * x
def back_out(x):
    x = clamp(x); c1 = 1.9; c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2

def paint(rgb, a=1.0, stroke=None, blur=None):
    p = skia.Paint(AntiAlias=True, Color=C(rgb, a))
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style); p.setStrokeWidth(stroke)
        p.setStrokeCap(skia.Paint.kRound_Cap); p.setStrokeJoin(skia.Paint.kRound_Join)
    if blur:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    return p

# ---------- texto ----------
_fonts = {}
def font(weight, size):
    k = (weight, size)
    if k not in _fonts:
        f = skia.Font(TF[weight], size); f.setSubpixel(True)
        f.setEdging(skia.Font.Edging.kAntiAlias); _fonts[k] = f
    return _fonts[k]

def segs(line):
    return [(p, i % 2 == 1) for i, p in enumerate(line.split("*")) if p]

def line_width(line, f):
    return sum(f.measureText(t) for t, _ in segs(line))

def draw_lines(c, lines, top, size, weight="ExtraBold", color=WHITE, accent=AMBER,
               alpha=1.0, lh=1.17, x=W / 2, align="center", maxw=None):
    if maxw:
        while max(line_width(l, font(weight, size)) for l in lines) > maxw and size > 10:
            size -= 1
    f = font(weight, size)
    for i, line in enumerate(lines):
        tw = line_width(line, f)
        xx = x - tw / 2 if align == "center" else x
        base = top + i * size * lh + size * 0.80
        for t, acc in segs(line):
            c.drawString(t, xx, base, f, paint(accent if acc else color, alpha))
            xx += f.measureText(t)
    return top + len(lines) * size * lh

def txt(c, t, lines, top, size, t_in, t_out=None, slide=36, **kw):
    """texto com entrada (fade + sobe) e saída (fade)."""
    e = ease_out((t - t_in) / 0.55)
    a = e
    if t_out is not None:
        a *= 1 - ease_io((t - t_out) / 0.4)
    if a <= 0.001:
        return
    draw_lines(c, lines, top + (1 - e) * slide, size, alpha=a * kw.pop("alpha", 1.0), **kw)

def pill(c, text, cx, cy, size, bg, fg, alpha=1.0, weight="Bold", padx=None, h=None, maxw=None):
    f = font(weight, size)
    if maxw:
        while f.measureText(text) + 2 * (padx or size * 0.9) > maxw and size > 10:
            size -= 1; f = font(weight, size)
    padx = padx or size * 0.9; h = h or size * 2.0
    tw = f.measureText(text)
    r = skia.Rect.MakeXYWH(cx - tw / 2 - padx, cy - h / 2, tw + 2 * padx, h)
    c.drawRRect(skia.RRect.MakeRectXY(r, h / 2, h / 2), paint(bg, alpha))
    c.drawString(text, cx - tw / 2, cy + size * 0.36, f, paint(fg, alpha))

# ---------- avião (vista de cima, nariz para cima) ----------
def poly(pts):
    p = skia.Path(); p.moveTo(*pts[0])
    for q in pts[1:]: p.lineTo(*q)
    p.close(); return p

def rrect_path(l, t, r, b, rx, ry=None):
    p = skia.Path(); p.addRRect(skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(l, t, r, b), rx, ry or rx)); return p

def circle_path(x, y, r):
    p = skia.Path(); p.addCircle(x, y, r); return p

def op(a, b, kind): return skia.Op(a, b, kind)
def union(ps):
    r = ps[0]
    for q in ps[1:]: r = op(r, q, skia.PathOp.kUnion_PathOp)
    return r

FUS = union([rrect_path(-46, -385, 46, 250, 46, 95),
             poly([(-45, 170), (45, 170), (17, 385), (-17, 385)])])
WING = poly([(-400, -22), (-40, -92), (40, -92), (400, -22), (402, 4), (395, 14),
             (40, 32), (-40, 32), (-395, 14), (-402, 4)])
STAB = poly([(-165, 305), (-20, 268), (20, 268), (165, 305), (165, 326), (20, 334), (-20, 334), (-165, 326)])

def le_y(x):  # bordo de ataque da asa
    return -92 + (abs(x) - 40) / 360 * 70

ENG_X = [-255, -130, 130, 255]
NAC = [(x, le_y(x) - 78, le_y(x) + 56) for x in ENG_X]
NACELLES = union([rrect_path(x - 23, t, x + 23, b, 23, 30) for x, t, b in NAC])
PLANE_PATH = union([FUS, WING, STAB, NACELLES])
COCKPIT = op(circle_path(0, -322, 66), PLANE_PATH, skia.PathOp.kIntersect_PathOp)
FATAL = union([NACELLES, COCKPIT])

nac_big = union([rrect_path(x - 36, t - 12, x + 36, b + 14, 30) for x, t, b in NAC])
WING_HIT = op(WING, union([nac_big, rrect_path(-58, -200, 58, 200, 10)]), skia.PathOp.kDifference_PathOp)
FUS_HIT = rrect_path(-34, -225, 34, 250, 20)
STAB_HIT = op(STAB, rrect_path(-26, 250, 26, 360, 6), skia.PathOp.kDifference_PathOp)
HIT_ZONES = union([WING_HIT, FUS_HIT, STAB_HIT])

def sample(rng, n, path, margin=9, mind=24, pts=None):
    out = []; allp = list(pts or []); b = path.getBounds(); tries = 0
    while len(out) < n and tries < 20000:
        tries += 1
        x = rng.uniform(b.left(), b.right()); y = rng.uniform(b.top(), b.bottom())
        if not all(path.contains(x + dx, y + dy) for dx, dy in
                   [(0, 0), (margin, 0), (-margin, 0), (0, margin), (0, -margin)]):
            continue
        if all((x - a) ** 2 + (y - c) ** 2 > mind ** 2 for a, c in allp):
            out.append((x, y)); allp.append((x, y))
    return out

def gen_hits(seed, nw, nf, ns, mind=24):
    rng = random.Random(seed)
    pts = sample(rng, nw, WING_HIT, mind=mind)
    pts += sample(rng, nf, FUS_HIT, mind=mind, pts=pts)
    pts += sample(rng, ns, STAB_HIT, margin=6, mind=mind, pts=pts)
    rng.shuffle(pts)
    return pts

def gen_fatal(seed):
    rng = random.Random(seed)
    pts = []
    for x, t, b in rng.sample(NAC, 2):
        pts.append((x + rng.uniform(-6, 6), rng.uniform(t + 25, b - 20)))
    pts.append((rng.uniform(-14, 14), rng.uniform(-345, -300)))
    return pts

MAIN_HITS = gen_hits(7, 34, 17, 12)

def draw_hole(c, x, y, r, k=1.0, a=1.0):
    if k <= 0: return
    rr = r * k
    c.drawCircle(x, y, rr * 1.9, paint(RED, 0.30 * a, blur=rr * 0.7))
    c.drawCircle(x, y, rr, paint(RED, a))
    c.drawCircle(x, y, rr * 0.42, paint(RED_DK, a))

def draw_plane(c, cx, cy, s, alpha=1.0, hits=(), hit_k=None, hole_r=8.0, rot=0.0,
               fill=PLANE, after=None):
    if alpha <= 0.001: return
    c.save(); c.translate(cx, cy); c.rotate(rot); c.scale(s, s)
    if alpha < 0.999: c.saveLayerAlpha(None, int(255 * alpha))
    c.drawPath(PLANE_PATH, paint(fill))
    dk = lerpc(fill, PLANE_DK, 0.75)
    for x, t, b in NAC:   # hélices
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(x - 40, t - 9, x + 40, t - 3), 3, 3), paint(dk))
        c.drawCircle(x, t + 4, 9, paint(dk))
    c.drawPath(poly([(-28, -335), (28, -335), (24, -305), (-24, -305)]), paint(lerpc(fill, WINDOW, 0.85)))
    c.drawPath(poly([(0, 180), (0, 380)]), paint(dk, 0.0))
    if after: after(c)
    for i, (x, y) in enumerate(hits):
        k = 1.0 if hit_k is None else hit_k[i]
        draw_hole(c, x, y, hole_r, back_out(k) if k < 1 else 1.0)
    if alpha < 0.999: c.restore()
    c.restore()

def draw_ghost(c, cx, cy, s, alpha):
    if alpha <= 0.001: return
    c.save(); c.translate(cx, cy); c.scale(s, s)
    p = paint(GREY, 0.55 * alpha, stroke=3.2 / s)
    p.setPathEffect(skia.DashPathEffect.Make([10 / s, 9 / s], 0))
    c.drawPath(PLANE_PATH, p)
    c.restore()
    d = 22 * s / 0.26
    pr = paint(RED, alpha, stroke=7 * s / 0.26)
    c.drawLine(cx - d, cy - d, cx + d, cy + d, pr); c.drawLine(cx - d, cy + d, cx + d, cy - d, pr)

# ---------- fundo ----------
def make_bg():
    s = skia.Surface.MakeRaster(skia.ImageInfo.Make(W, H, skia.kRGBA_8888_ColorType, skia.kPremul_AlphaType))
    c = s.getCanvas(); c.clear(C(BG))
    g = paint(GRID)
    for yy in range(27, H, 54):
        for xx in range(27, W, 54):
            c.drawCircle(xx, yy, 2.2, g)
    sh = skia.GradientShader.MakeRadial((W / 2, H * 0.48), H * 0.75,
                                       [C(BG, 0.0), C(BG, 0.0), C((4, 7, 14), 0.85)], [0.0, 0.45, 1.0])
    c.drawPaint(skia.Paint(Shader=sh))
    return s.makeImageSnapshot()

# ---------- cenas (t = segundos locais) ----------
PCX, PCY = W / 2, 1090   # posição do avião grande

def sc_hook(c, t):
    pill(c, "CURIOSIDADE  •  CIÊNCIA DE DADOS", W / 2, 350, 30, (30, 42, 66), AMBER, weight="Bold")
    k = 0.965 + 0.035 * ease_out(t / 0.35)
    c.save(); c.translate(W / 2, 700); c.scale(k, k); c.translate(-W / 2, -700)
    draw_lines(c, ["Na 2ª Guerra,", "quase blindaram", "os aviões no", "*lugar errado*."], 470, 98)
    c.restore()
    hits = MAIN_HITS[:14]
    draw_plane(c, W / 2, 1310 - 18 * t, 0.56, alpha=ease_out(t / 0.6), hits=hits, hole_r=11)

def sc_plane(c, t):   # 16 s: buracos + ideia óbvia
    e = ease_out(t / 0.7)
    n = len(MAIN_HITS)
    hk = [clamp((t - (1.3 + i * 5.0 / n)) / 0.28) for i in range(n)]
    def overlay(cc):
        a = clamp((t - 9.0) / 0.8)
        if a > 0:
            pulse = 0.5 + 0.5 * math.sin((t - 9.0) * 4.2)
            cc.drawPath(HIT_ZONES, paint(AMBER, a * (0.22 + 0.16 * pulse)))
            cc.drawPath(HIT_ZONES, paint(AMBER, a * 0.9, stroke=4))
    draw_plane(c, PCX, PCY + (1 - e) * 60, 1.0, alpha=e, hits=MAIN_HITS, hit_k=hk, after=overlay)
    txt(c, t, ["Os aviões voltavam das", "missões *cheios de", "*buracos* de bala."], 300, 70, 0.3, 7.6, accent=RED)
    cnt = sum(1 for k in hk if k > 0)
    a = ease_out((t - 1.2) / 0.5) * (1 - ease_io((t - 7.6) / 0.4))
    if a > 0:
        draw_lines(c, [f"buracos mapeados: {cnt}"], 585, 38, weight="SemiBold", color=GREY, alpha=a)
    txt(c, t, ["A ideia óbvia:", "reforçar onde tem", "*mais buracos*."], 300, 76, 8.0)
    a = clamp((t - 9.6) / 0.5)
    if a > 0:
        for (lx, ly) in [(-235, 78), (235, 78), (0, 425)]:
            pill(c, "+ BLINDAGEM?", PCX + lx, PCY + ly + (1 - ease_out(a)) * 20, 30, (25, 18, 4), AMBER, alpha=a)

def sc_wald(c, t):   # 10 s
    draw_plane(c, PCX, PCY, 1.0, alpha=0.13, hits=MAIN_HITS)
    txt(c, t, ["Mas o estatístico", "*Abraham Wald* disse:"], 330, 70, 0.2)
    e = ease_out((t - 2.0) / 0.45)
    if e > 0:
        k = 1.25 - 0.25 * back_out((t - 2.0) / 0.45)
        c.save(); c.translate(W / 2, 830); c.scale(k, k); c.translate(-W / 2, -830)
        draw_lines(c, ["“Esperem.”"], 750, 132, weight="Black", alpha=e)
        c.restore()
    txt(c, t, ["Onde estão os buracos", "dos aviões que", "*não voltaram*?"], 1080, 66, 4.3, accent=RED)

GRID_POS = [(250 + 290 * (i % 3), 830 + 285 * (i // 3)) for i in range(9)]
DOWN = {1, 3, 5, 8}
SMALL_HITS = [gen_hits(100 + i, 6, 2, 2, mind=44) for i in range(9)]
SMALL_FATAL = {i: gen_fatal(200 + i) for i in DOWN}

def sc_fleet(c, t):   # 12 s
    S = 0.26
    for i, (x, y) in enumerate(GRID_POS):
        appear = ease_out((t - (0.5 + i * 0.12)) / 0.5)
        hits = SMALL_HITS[i]; hk = [clamp((t - (1.6 + j * 0.17 + i * 0.03)) / 0.25) for j in range(len(hits))]
        if i in DOWN:
            f = SMALL_FATAL[i]
            hits = hits + f; hk = hk + [clamp((t - (3.5 + j * 0.13)) / 0.25) for j in range(len(f))]
            tint = ease_io((t - 3.9) / 0.4); fall = ease_io((t - 4.2) / 1.1)
            fill = lerpc(PLANE, hx("7A2C38"), tint)
            draw_ghost(c, x, y, S, ease_out((t - 5.0) / 0.6))
            if fall < 1:
                draw_plane(c, x, y + 110 * fall ** 1.6, S * (1 - 0.15 * fall), alpha=appear * (1 - fall),
                           hits=hits, hit_k=hk, hole_r=20, rot=16 * fall, fill=fill)
        else:
            draw_plane(c, x, y, S, alpha=appear, hits=hits, hit_k=hk, hole_r=20)
    txt(c, t, ["Agora pense em *todos*", "os aviões que", "partiram."], 300, 70, 0.2, 3.3)
    txt(c, t, ["Os que levaram tiro no", "*motor* ou na *cabine*…", "nunca voltaram."], 300, 70, 3.8, 8.6, accent=RED)
    txt(c, t, ["Os dados só mostravam", "quem *sobreviveu*."], 330, 72, 9.0)

def sc_fix(c, t):   # 8 s
    def overlay(cc):
        a = clamp((t - 0.9) / 0.6)
        if a > 0:
            pulse = 0.5 + 0.5 * math.sin((t - 0.9) * 4.5)
            cc.drawPath(FATAL, paint(GREEN, a * 0.55, blur=18))
            cc.drawPath(FATAL, paint(GREEN, a * (0.55 + 0.35 * pulse)))
            for x, tt, b in NAC + [(0, -350, -294)]:
                cy = (tt + b) / 2
                for ph in (0.0, 0.5):
                    k = ((t - 0.9) / 1.6 + ph) % 1.0
                    cc.drawCircle(x, cy, 40 + 70 * k, paint(GREEN, a * 0.7 * (1 - k), stroke=4))
    draw_plane(c, PCX, PCY, 1.0, alpha=ease_out(t / 0.5), hits=MAIN_HITS, after=overlay)
    txt(c, t, ["Então: reforce onde", "*NÃO* há buracos."], 330, 80, 0.2, accent=GREEN)
    a = clamp((t - 2.0) / 0.5)
    if a > 0:
        dy = (1 - ease_out(a)) * 20
        pill(c, "CABINE", PCX + 175, PCY - 335 + dy, 32, (6, 34, 24), GREEN, alpha=a)
        pill(c, "MOTORES", PCX - 255, PCY - 245 + dy, 32, (6, 34, 24), GREEN, alpha=a)
    txt(c, t, ["Um tiro ali derrubava o avião."], 545, 42, 3.8, weight="SemiBold", color=GREY)

CARDS = [("Só os clientes que *ficaram*", "e não os que cancelaram"),
         ("Só as startups que *deram certo*", "e não as milhares que quebraram"),
         ("Só quem *respondeu* a pesquisa", "quem desistiu nem abriu o e-mail")]

def sc_bias(c, t):   # 12 s
    txt(c, t, ["Isso é o", "*viés de sobrevivência*"], 290, 92, 0.2)
    txt(c, t, ["Concluir algo olhando só para", "quem passou pelo filtro."], 540, 44,
        1.2, weight="SemiBold", color=GREY)
    for i, (main, sub) in enumerate(CARDS):
        t0 = [5.4, 8.1, 10.1][i]
        e = ease_out((t - t0) / 0.55)
        if e <= 0: continue
        y = 790 + i * 230 + (1 - e) * 40
        r = skia.Rect.MakeXYWH(90, y, 860, 200)
        c.drawRRect(skia.RRect.MakeRectXY(r, 30, 30), paint(CARD, e))
        c.drawRRect(skia.RRect.MakeRectXY(r, 30, 30), paint((40, 54, 84), e, stroke=2))
        c.drawCircle(170, y + 100, 38, paint(AMBER, e))
        f = font("Black", 40); n = str(i + 1)
        c.drawString(n, 170 - f.measureText(n) / 2, y + 114, f, paint(BG, e))
        draw_lines(c, [main], y + 42, 44, weight="ExtraBold", alpha=e, x=236, align="left", maxw=690)
        draw_lines(c, [sub], y + 112, 34, weight="Medium", color=GREY, alpha=e, x=236, align="left", maxw=690)

def sc_outro(c, t):   # 8 s
    txt(c, t, ["Antes de olhar os dados,", "pergunte:"], 360, 64, 0.2, weight="Bold")
    e = ease_out((t - 2.3) / 0.5)
    if e > 0:
        k = 1.15 - 0.15 * back_out((t - 2.3) / 0.5)
        c.save(); c.translate(W / 2, 760); c.scale(k, k); c.translate(-W / 2, -760)
        draw_lines(c, ["Quem ficou", "*de fora*?"], 590, 140, weight="Black", alpha=e)
        c.restore()
    for j, x in enumerate([210, 375, 540, 705, 870]):
        a = ease_out((t - (3.0 + j * 0.12)) / 0.5)
        if j in (1, 3):
            draw_ghost(c, x, 1150, 0.17, a)
        else:
            draw_plane(c, x, 1150 + (1 - a) * 20, 0.17, alpha=a, hits=SMALL_HITS[j][:6], hole_r=22)
    a = ease_out((t - 4.0) / 0.5)
    if a > 0:
        pill(c, "Siga para mais curiosidades de dados", W / 2, 1375 + (1 - a) * 24, 40, AMBER, BG,
             alpha=a, weight="ExtraBold", h=100, maxw=880)

SCENES = [("01_hook", 4, sc_hook), ("02_plane", 16, sc_plane), ("03_wald", 10, sc_wald),
          ("04_fleet", 12, sc_fleet), ("05_fix", 8, sc_fix), ("06_bias", 12, sc_bias),
          ("07_outro", 8, sc_outro)]

# ---------- render ----------
INFO = skia.ImageInfo.Make(W, H, skia.kRGBA_8888_ColorType, skia.kPremul_AlphaType)

def frame(surf, bg, fn, t, dur, idx):
    c = surf.getCanvas(); c.drawImage(bg, 0, 0)
    fin = 1.0 if idx == 0 else ease_io(t / 0.3)
    fout = 1.0 if idx == len(SCENES) - 1 else 1 - ease_io((t - (dur - 0.3)) / 0.3)
    a = min(fin, fout)
    if a <= 0.001: return
    if a < 0.999: c.saveLayerAlpha(None, int(255 * a))
    fn(c, t)
    if a < 0.999: c.restore()

def preview(specs):
    os.makedirs(os.path.join(HERE, "preview"), exist_ok=True)
    bg = make_bg(); surf = skia.Surface.MakeRaster(INFO)
    names = {n: (i, d, f) for i, (n, d, f) in enumerate(SCENES)}
    for spec in specs:
        name, ts = spec.split(":"); idx, dur, fn = names[name]
        frame(surf, bg, fn, float(ts), dur, idx)
        p = os.path.join(HERE, "preview", f"{name}_{ts}.png")
        surf.makeImageSnapshot().save(p, skia.kPNG); print(p)

def render_scene(idx, name, dur, fn, bg):
    final = os.path.join(OUT, f"{name}.mp4"); tmp = os.path.join(OUT, f"{name}.part.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast",
           "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS), tmp]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    surf = skia.Surface.MakeRaster(INFO)
    for n in range(round(dur * FPS)):
        frame(surf, bg, fn, n / FPS, dur, idx)
        p.stdin.write(surf.makeImageSnapshot().tobytes())
    p.stdin.close()
    if p.wait() == 0: os.replace(tmp, final)
    else: sys.exit(f"falhou: {name}")
    print("ok", name, flush=True)

def render(only=None):
    os.makedirs(OUT, exist_ok=True); bg = make_bg()
    for i, (n, d, f) in enumerate(SCENES):
        if only and n not in only: continue
        render_scene(i, n, d, f, bg)
    lst = os.path.join(OUT, "list.txt")
    with open(lst, "w") as fh:
        for n, _, _ in SCENES: fh.write(f"file '{n}.mp4'\n")
    out = os.path.join(OUT, "vies_de_sobrevivencia.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
                    "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-shortest",
                    "-movflags", "+faststart", out], check=True)
    print(out)

if __name__ == "__main__":
    if sys.argv[1] == "preview": preview(sys.argv[2:])
    else: render(sys.argv[2:] or None)
