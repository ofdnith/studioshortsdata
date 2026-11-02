"""Identidade visual: cores, fontes, easing e helpers de desenho (base: referencia/)."""

import math
from functools import lru_cache
from pathlib import Path

import skia

W, H, FPS = 1080, 1920, 30
PASTA = Path(__file__).parent

# Áreas seguras do Reels: conteúdo entre y=250 e y=1550; evitar canto inferior direito.
TOPO_SEGURO, BASE_SEGURA = 250, 1550
Y_TITULO = 270          # topo do título da tela
Y_CENA0, Y_CENA1 = 600, 1450   # faixa onde as cenas desenham
Y_FONTE = 1518          # linha "Fonte: ..." no rodapé


def hx(s: str) -> tuple[int, int, int]:
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


FUNDO = hx("0B1220"); GRADE = hx("1B263C"); BRANCO = hx("F4F6FB"); CINZA = hx("97A3B8")
AMARELO = hx("FFC145"); VERMELHO = hx("FF4D5E"); VERDE = hx("3DDC97"); CIANO = hx("62C7FF")
ROXO = hx("C792FF"); PAINEL = hx("121B2E"); PAINEL_LN = hx("24314C"); PONTO = hx("E9EEF7")
FUNDO_ILUS = hx("1A2540")

# Cores por nome (o roteiro pode pedir "verde", "vermelho"...).
CORES = {"amarelo": AMARELO, "vermelho": VERMELHO, "verde": VERDE, "ciano": CIANO, "azul": CIANO,
         "roxo": ROXO, "cinza": CINZA, "branco": BRANCO, "laranja": hx("FF8A3D"), "rosa": hx("FF7EB6")}
# Paleta para séries sem cor definida (ex.: Homens, Mulheres).
SERIES = [CIANO, ROXO, VERDE, AMARELO, hx("FF8A3D"), hx("FF7EB6")]


def cor(nome: str | None, i: int = 0) -> tuple[int, int, int]:
    if nome:
        if nome.startswith("#"):
            return hx(nome)
        if nome in CORES:
            return CORES[nome]
    return SERIES[i % len(SERIES)]


def misturar(a, b, k):
    return tuple(int(x + (y - x) * k) for x, y in zip(a, b))


def C(rgb, a=1.0):
    return skia.ColorSetARGB(int(round(255 * max(0.0, min(1.0, a)))), *rgb)


# ---------- easing ----------
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_io(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def back_out(x):
    x = clamp(x)
    c1 = 1.9
    return 1 + (c1 + 1) * (x - 1) ** 3 + c1 * (x - 1) ** 2


def vis(t, t0, t1, fin=0.22, fout=0.2):
    """Visibilidade 0..1 com entrada em t0 e saída em t1. Devolve (alpha, e_entrada)."""
    e = ease_out((t - t0) / fin)
    a = e * (1 - ease_io((t - t1) / fout)) if t1 is not None else e
    return a, e


# ---------- tinta e fontes ----------
def paint(rgb, a=1.0, stroke=None, blur=None):
    p = skia.Paint(AntiAlias=True, Color=C(rgb, a))
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(stroke)
        p.setStrokeCap(skia.Paint.kRound_Cap)
    if blur:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    return p


PESOS = ["Regular", "Medium", "SemiBold", "Bold", "ExtraBold", "Black"]
_TF = {w: skia.Typeface.MakeFromFile(str(PASTA / "fontes" / f"Inter-{w}.otf")) for w in PESOS}


@lru_cache(maxsize=512)
def font(peso: str, tamanho: float) -> skia.Font:
    f = skia.Font(_TF[peso], tamanho)
    f.setSubpixel(True)
    f.setEdging(skia.Font.Edging.kAntiAlias)
    return f


def partes(linha: str):
    """'Berkeley *discriminava*' -> [('Berkeley ', False), ('discriminava', True)]"""
    return [(p, i % 2 == 1) for i, p in enumerate(linha.split("*")) if p]


def sem_marcas(linha: str) -> str:
    return linha.replace("*", "")


def largura(linha: str, f: skia.Font) -> float:
    return sum(f.measureText(t) for t, _ in partes(linha))


# Verificação: textos que precisaram encolher muito para caber (lido pela prévia).
ENCOLHIDOS: list[tuple[str, float, float]] = []
LIMIAR_ENCOLHER = 0.72


def _encolheu(s: str, pedido: float, final: float):
    if final < pedido * LIMIAR_ENCOLHER:
        ENCOLHIDOS.append((sem_marcas(s), pedido, final))


def ajustar_tamanho(linhas, tamanho, peso, maxw):
    pedido = tamanho
    while linhas and max(largura(l, font(peso, tamanho)) for l in linhas) > maxw and tamanho > 10:
        tamanho -= 1
    if linhas:
        _encolheu(" / ".join(linhas), pedido, tamanho)
    return tamanho


def quebrar_marcado(s: str, tamanho: float, peso: str, maxw: float) -> list[str]:
    """Quebra um texto com *destaques* em linhas que cabem em maxw, mantendo os destaques."""
    palavras, dentro = [], False
    for w in s.split():
        abre = w.startswith("*")
        fecha = w.endswith("*") and (len(w) > 1 or not abre)
        nucleo = w.strip("*")
        palavras.append(f"*{nucleo}*" if (dentro or abre) else nucleo)
        if abre and not fecha:
            dentro = True
        elif fecha and not abre:
            dentro = False
    f = font(peso, tamanho)
    res, atual = [], ""
    for p in palavras:
        teste = (atual + " " + p).strip()
        if largura(teste, f) <= maxw or not atual:
            atual = teste
        else:
            res.append(atual)
            atual = p
    if atual:
        res.append(atual)
    return [ln.replace("* *", " ") for ln in res]


def linhas(c, ls, topo, tamanho, peso="ExtraBold", cor_=BRANCO, destaque=AMARELO, alpha=1.0,
           lh=1.17, x=W / 2, align="center", maxw=920):
    """Desenha linhas com *destaques*; reduz a fonte até caber em maxw. Devolve a altura."""
    if alpha <= 0.002 or not ls:
        return 0
    tamanho = ajustar_tamanho(ls, tamanho, peso, maxw)
    f = font(peso, tamanho)
    for i, linha in enumerate(ls):
        tw = largura(linha, f)
        xx = x - tw / 2 if align == "center" else (x - tw if align == "right" else x)
        base = topo + i * tamanho * lh + tamanho * 0.80
        for t, acc in partes(linha):
            c.drawString(t, xx, base, f, paint(destaque if acc else cor_, alpha))
            xx += f.measureText(t)
    return len(ls) * tamanho * lh


def texto(c, s, x, y, tamanho, cor_=BRANCO, a=1.0, peso="ExtraBold", align="left", maxw=None):
    """Uma linha de texto com a linha de base em y."""
    if a <= 0.002 or not s:
        return
    f = font(peso, tamanho)
    if maxw:
        pedido = tamanho
        while f.measureText(s) > maxw and tamanho > 10:
            tamanho -= 1
            f = font(peso, tamanho)
        _encolheu(s, pedido, tamanho)
    tw = f.measureText(s)
    xx = x - tw / 2 if align == "center" else (x - tw if align == "right" else x)
    c.drawString(s, xx, y, f, paint(cor_, a))


def pilula(c, s, cx, cy, tamanho, fundo, frente, alpha=1.0, peso="Bold", h=None, maxw=900):
    if alpha <= 0.002:
        return
    f = font(peso, tamanho)
    pedido = tamanho
    while f.measureText(s) > maxw - tamanho * 1.8 and tamanho > 10:
        tamanho -= 1
        f = font(peso, tamanho)
    _encolheu(s, pedido, tamanho)
    tw = f.measureText(s)
    h = h or tamanho * 2.0
    px = tamanho * 0.9
    r = skia.Rect.MakeXYWH(cx - tw / 2 - px, cy - h / 2, tw + 2 * px, h)
    c.drawRRect(skia.RRect.MakeRectXY(r, h / 2, h / 2), paint(fundo, alpha))
    c.drawString(s, cx - tw / 2, cy + tamanho * 0.36, f, paint(frente, alpha))


def barra(c, x, y, w, h, cor_, a, r=12):
    if w <= 0.5 or h <= 0.5 or a <= 0.002:
        return
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), min(r, w / 2), min(r, h / 2)),
                paint(cor_, a))


def painel(c, x, y, w, h, alpha=1.0, grade=0, raio=26, borda=PAINEL_LN):
    if alpha <= 0.002:
        return
    r = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), raio, raio)
    c.drawRRect(r, paint(PAINEL, alpha))
    c.drawRRect(r, paint(borda, alpha, stroke=2))
    for i in range(1, grade):
        gx, gy = x + w * i / grade, y + h * i / grade
        c.drawLine(gx, y + 14, gx, y + h - 14, paint(GRADE, alpha * 0.8, stroke=1.5))
        c.drawLine(x + 14, gy, x + w - 14, gy, paint(GRADE, alpha * 0.8, stroke=1.5))


def check(c, x, y, r, a, cor_=VERDE):
    if a <= 0.002:
        return
    c.drawCircle(x, y, r, paint(cor_, a))
    p = paint(FUNDO, a, stroke=r * 0.26)
    c.drawLine(x - r * 0.45, y, x - r * 0.12, y + r * 0.33, p)
    c.drawLine(x - r * 0.12, y + r * 0.33, x + r * 0.45, y - r * 0.35, p)


def seta(c, x0, y0, x1, y1, cor_, a, k=1.0, tracejada=False, w=6):
    if a <= 0.002 or k <= 0:
        return
    x1 = x0 + (x1 - x0) * k
    y1 = y0 + (y1 - y0) * k
    p = paint(cor_, a, stroke=w)
    if tracejada:
        p.setPathEffect(skia.DashPathEffect.Make([18, 14], 0))
    c.drawLine(x0, y0, x1, y1, p)
    ang = math.atan2(y1 - y0, x1 - x0)
    L = 24
    path = skia.Path()
    path.moveTo(x1, y1)
    path.lineTo(x1 - L * math.cos(ang - 0.45), y1 - L * math.sin(ang - 0.45))
    path.lineTo(x1 - L * math.cos(ang + 0.45), y1 - L * math.sin(ang + 0.45))
    path.close()
    c.drawPath(path, paint(cor_, a))


def seta_curva(c, x0, y0, cx, cy, x1, y1, cor_, a, k=1.0, tracejada=False, w=6):
    """Seta em curva (quadrática) com ponta na direção da curva; desenha até a fração k."""
    if a <= 0.002 or k <= 0:
        return
    path = skia.Path()
    path.moveTo(x0, y0)
    path.quadTo(cx, cy, x1, y1)
    med = skia.PathMeasure(path, False)
    comp = med.getLength() * min(1.0, k)
    seg = skia.Path()
    med.getSegment(0, comp, seg, True)
    p = paint(cor_, a, stroke=w)
    if tracejada:
        p.setPathEffect(skia.DashPathEffect.Make([18, 14], 0))
    c.drawPath(seg, p)
    res = med.getPosTan(comp)
    pos, tan = (res[1], res[2]) if len(res) == 3 else res
    if pos is not None and tan is not None:
        ang = math.atan2(tan.y(), tan.x())
        L = 24
        ponta = skia.Path()
        ponta.moveTo(pos.x(), pos.y())
        ponta.lineTo(pos.x() - L * math.cos(ang - 0.45), pos.y() - L * math.sin(ang - 0.45))
        ponta.lineTo(pos.x() - L * math.cos(ang + 0.45), pos.y() - L * math.sin(ang + 0.45))
        ponta.close()
        c.drawPath(ponta, paint(cor_, a))


def fmt_num(v: float, casas: int | None = None) -> str:
    """Número no formato brasileiro: 4.526 · 44,5"""
    from decimal import ROUND_HALF_UP, Decimal
    if casas is None:
        casas = 0 if float(v).is_integer() else 1
    # arredondamento "escolar" (44,5 -> 45), igual ao número falado
    d = Decimal(str(v)).quantize(Decimal(1).scaleb(-casas), rounding=ROUND_HALF_UP)
    s = f"{d:,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


MOEDAS = ("R$", "US$", "$", "€", "£")


def com_unidade(v: float, unidade: str = "", casas: int | None = None) -> str:
    """Número formatado + unidade no lugar certo: R$ 101.800 · 45% · 3 pts · 2,5×"""
    s = fmt_num(v, casas)
    u = (unidade or "").strip()
    if not u:
        return s
    if u in MOEDAS:
        return f"{u} {s}"
    if u in ("%", "×", "x", "º", "°"):
        return f"{s}{u}"
    return f"{s} {u}"


# ---------- fundo ----------
INFO = skia.ImageInfo.Make(W, H, skia.kRGBA_8888_ColorType, skia.kPremul_AlphaType)


def fazer_fundo() -> skia.Image:
    """Azul-escuro com grade de pontos sutil e vinheta."""
    s = skia.Surface.MakeRaster(INFO)
    c = s.getCanvas()
    c.clear(C(FUNDO))
    p = paint(GRADE)
    for yy in range(27, H, 54):
        for xx in range(27, W, 54):
            c.drawCircle(xx, yy, 2.2, p)
    sh = skia.GradientShader.MakeRadial((W / 2, H * 0.48), H * 0.75,
                                        [C(FUNDO, 0), C(FUNDO, 0), C((4, 7, 14), 0.85)], [0, 0.45, 1])
    c.drawPaint(skia.Paint(Shader=sh))
    return s.makeImageSnapshot()
