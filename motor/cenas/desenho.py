"""Cena `desenho`: ilustrações sob medida em SVG, desenhadas pela IA para cada vídeo.

SVG é desenho (formas), não programa: nada é executado. Mesmo assim, o SVG passa por
uma limpeza (sem <script>, <foreignObject>, <image>, atributos on*, links externos).

Cada camada entra no início do trecho em que aparece pela primeira vez — ou na palavra
`na_palavra` da fala — e sai quando um trecho seguinte da mesma cena não a lista mais.
"""

import hashlib
import math
import re
import unicodedata
from functools import lru_cache

import skia

from motor import estilo as E
from motor.estilo import AMARELO, BRANCO, CINZA, FUNDO, back_out, clamp, ease_io, ease_out, paint

MAX_SVG = 30_000


def limpar_svg(svg: str) -> str:
    s = svg.strip()[:MAX_SVG]
    s = re.sub(r"<\s*(script|foreignObject|iframe|object|embed)\b.*?<\s*/\s*\1\s*>", "", s, flags=re.I | re.S)
    s = re.sub(r"<\s*(script|foreignObject|image|iframe|object|embed)\b[^>]*/?>", "", s, flags=re.I)
    s = re.sub(r"\son\w+\s*=\s*(\"[^\"]*\"|'[^']*')", "", s, flags=re.I)
    s = re.sub(r"(xlink:)?href\s*=\s*(\"(?!#)[^\"]*\"|'(?!#)[^']*')", "", s, flags=re.I)   # só refs internas (#id)
    if not re.match(r"^\s*<svg\b", s, re.I):
        s = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">{s}</svg>'
    elif "xmlns=" not in s[:200]:
        s = re.sub(r"<svg\b", '<svg xmlns="http://www.w3.org/2000/svg"', s, count=1, flags=re.I)
    return s


def _viewbox(s: str) -> tuple[float, float]:
    m = re.search(r'viewBox\s*=\s*["\']\s*[-\d.]+[\s,]+[-\d.]+[\s,]+([\d.]+)[\s,]+([\d.]+)', s, re.I)
    if m:
        return float(m.group(1)) or 100, float(m.group(2)) or 100
    return 100.0, 100.0


@lru_cache(maxsize=256)
def _dom(svg_limpo: str):
    dom = skia.SVGDOM.MakeFromStream(skia.MemoryStream(svg_limpo.encode("utf-8"), True))
    return dom, _viewbox(svg_limpo)


def svg_valido(svg: str) -> bool:
    try:
        return _dom(limpar_svg(svg))[0] is not None
    except Exception:
        return False


def desenhar_svg(c, svg: str, cx: float, cy: float, largura: float, a: float = 1.0):
    dom, (vw, vh) = _dom(limpar_svg(svg))
    if dom is None or a <= 0.002:
        return
    altura = largura * vh / vw
    dom.setContainerSize(skia.Size(largura, altura))
    c.save()
    c.translate(cx - largura / 2, cy - altura / 2)
    if a < 0.999:
        c.saveLayerAlpha(skia.Rect.MakeWH(largura, altura), int(255 * a))
    dom.render(c)
    if a < 0.999:
        c.restore()
    c.restore()


# ---------------------------------------------------------------- tempo da palavra

def _norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn")


def instante_da_palavra(fala: str, palavra: str, inicio: float, fim: float) -> float | None:
    """Estimativa de quando a palavra é dita: proporção de caracteres até ela dentro do trecho."""
    if not palavra:
        return None
    f, p = _norm(fala), _norm(palavra).strip()
    i = f.find(p)
    if i < 0:
        return None
    return inicio + (fim - inicio) * (i / max(1, len(f)))


# ---------------------------------------------------------------- cena

def desenho(c, ctx):
    t = ctx.t
    cena0 = ctx.trechos[0].cena
    if cena0.fundo == "painel":
        E.painel(c, 90, 600, 860, 860, ease_out((t - ctx.entrada) / 0.4))
    elif cena0.fundo == "ceu":
        a = ease_out((t - ctx.entrada) / 0.4)
        rr = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(90, 600, 860, 860), 34, 34)
        sky = skia.GradientShader.MakeLinear([(0, 600), (0, 1460)], [E.C(E.hx("16264A"), a), E.C(E.hx("3A5A8A"), a)],
                                             [0, 1])
        c.drawRRect(rr, skia.Paint(Shader=sky, AntiAlias=True))

    # em que trecho cada camada (por id) aparece e some, dentro desta cena
    vistas: dict[str, dict] = {}
    for k in range(ctx.n):
        tr = ctx.trecho(k)
        fala = ctx.roteiro.trechos[tr.indice].fala
        ids_k = set()
        for cam in tr.cena.camadas:
            ids_k.add(cam.id)
            if cam.id not in vistas:
                base = ctx.inicio(k)
                na = instante_da_palavra(fala, cam.na_palavra, tr.inicio, tr.fim) if cam.na_palavra else None
                t_in = (na if na is not None else base + (0.15 if k else 0.3)) + cam.atraso
                vistas[cam.id] = {"t_in": t_in, "t_out": None, "cam": cam}
            else:
                vistas[cam.id]["cam"] = cam     # versão mais recente (posição/rotulo podem mudar)
        for cid, v in vistas.items():
            if v["t_out"] is None and cid not in ids_k and k > 0 and v["t_in"] < ctx.inicio(k):
                v["t_out"] = ctx.inicio(k)

    for cid, v in vistas.items():
        if t < v["t_in"] - 0.01 or ctx.atual < 0:
            continue
        cam = v["cam"]
        lt = t - v["t_in"]
        a = ease_out(lt / 0.35)
        if v["t_out"] is not None:
            a *= 1 - ease_io((t - v["t_out"]) / 0.3)
        if a <= 0.002:
            continue
        x, y, larg = cam.x, cam.y, cam.largura
        escala = 1.0
        if cam.entrada == "pop":
            escala = back_out(lt / 0.45)
        elif cam.entrada == "desliza_esquerda":
            x -= (1 - ease_out(lt / 0.5)) * 260
        elif cam.entrada == "desliza_direita":
            x += (1 - ease_out(lt / 0.5)) * 260
        elif cam.entrada == "desliza_baixo":
            y += (1 - ease_out(lt / 0.5)) * 220
        mov = cam.movimento
        ang = 0.0
        if mov == "flutuar":
            y += math.sin(lt * 2.2) * 10
        elif mov == "balancar":
            ang = math.sin(lt * 2.6) * 6
        elif mov == "pulsar":
            escala *= 1 + 0.05 * math.sin(lt * 5)
        elif mov == "girar":
            ang = lt * 60
        elif mov == "tremer":
            x += math.sin(lt * 40) * 3
            y += math.cos(lt * 37) * 3
        c.save()
        c.translate(x, y)
        if ang:
            c.rotate(ang)
        if escala != 1.0:
            c.scale(max(0.01, escala), max(0.01, escala))
        if cam.entrada == "desenhar":
            k = ease_io(lt / 0.9)
            c.clipRect(skia.Rect.MakeLTRB(-larg / 2 - 5, -2000, -larg / 2 + (larg + 10) * k, 2000))
        try:
            desenhar_svg(c, cam.svg, 0, 0, larg, a)
        except Exception:
            E.texto(c, "?", 0, 20, 60, CINZA, a, "Black", "center")
        c.restore()
        if cam.rotulo:
            _, (vw, vh) = _dom(limpar_svg(cam.svg))
            E.texto(c, cam.rotulo, cam.x, cam.y + larg * vh / vw / 2 + 46, 34, BRANCO, a, "Bold", "center",
                    maxw=min(900, larg + 300))
