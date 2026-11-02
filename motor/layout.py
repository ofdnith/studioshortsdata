"""Layout para o modo livre: caixas, encaixe automático e medição de proporções.

A IA pensa em retângulos (x, y, w, h): divide a área útil em zonas/grade e encaixa desenhos e
textos neles com as funções *_em, que mantêm a proporção e nunca vazam da caixa.
Enquanto o código desenha, os textos são registrados para medir: tamanho mínimo e sobreposição.
"""

import math

import numpy as np
import skia

from motor import estilo as E

# Área útil do vídeo (tudo que importa fica aqui): abaixo do topo seguro e acima do rodapé da fonte.
# Embaixo: legenda da fala (faixa y 1510–1610) e fonte (y≈1660); abaixo de 1700 fica a interface do app.
AREA = (60.0, 250.0, 960.0, 1230.0)            # x, y, w, h  (y de 250 a 1480)
AREA_SEM_TITULO = (60.0, 580.0, 960.0, 900.0)  # quando o motor desenha os títulos (y de 580 a 1480)
TEXTO_MIN, FRASE_MIN = 30, 40

# Versões do layout. Cada roteiro guarda a sua: os antigos (1) foram desenhados para a área menor
# e continuam iguais se forem renderizados de novo.
LAYOUTS = {
    1: {"area": (60.0, 250.0, 960.0, 1100.0), "sem_titulo": (60.0, 580.0, 960.0, 770.0),
        "limite": 1350, "legenda": 1428, "fonte": 1518},
    2: {"area": (60.0, 250.0, 960.0, 1230.0), "sem_titulo": (60.0, 580.0, 960.0, 900.0),
        "limite": 1480, "legenda": 1560, "fonte": 1660},
}
LAYOUT_ATUAL = 2


def usar_layout(versao: int):
    """Ajusta a área útil, a legenda e a fonte para a versão de layout do roteiro."""
    global AREA, AREA_SEM_TITULO, LIMITE
    from motor import legendas
    cfg = LAYOUTS.get(versao, LAYOUTS[LAYOUT_ATUAL])
    AREA, AREA_SEM_TITULO, LIMITE = cfg["area"], cfg["sem_titulo"], cfg["limite"]
    legendas.LIMITE_CENA, legendas.Y_LEGENDA = cfg["limite"], cfg["legenda"]
    E.Y_FONTE = cfg["fonte"]


LIMITE = 1480

# ---------------------------------------------------------------- caixas

def caixa(x, y, w, h):
    return (float(x), float(y), float(w), float(h))


def centro(r):
    return r[0] + r[2] / 2, r[1] + r[3] / 2


def margem(r, m):
    return (r[0] + m, r[1] + m, max(1.0, r[2] - 2 * m), max(1.0, r[3] - 2 * m))


def dividir(r, partes, eixo="v", espaco=24.0):
    """Divide a caixa em pedaços proporcionais. partes: int ou lista de pesos; eixo 'v' (empilha) ou 'h'."""
    pesos = [1.0] * partes if isinstance(partes, int) else [float(p) for p in partes]
    total = sum(pesos)
    x, y, w, h = r
    livre = (h if eixo == "v" else w) - espaco * (len(pesos) - 1)
    res, pos = [], (y if eixo == "v" else x)
    for p in pesos:
        tam = livre * p / total
        res.append((x, pos, w, tam) if eixo == "v" else (pos, y, tam, h))
        pos += tam + espaco
    return res


def grade(r, colunas, linhas, espaco=20.0):
    x, y, w, h = r
    cw = (w - espaco * (colunas - 1)) / colunas
    ch = (h - espaco * (linhas - 1)) / linhas
    return [(x + c * (cw + espaco), y + l * (ch + espaco), cw, ch) for l in range(linhas) for c in range(colunas)]


def encaixar(w, h, r, alinhar="centro"):
    """Escala (w, h) para caber em r sem distorcer. Devolve (x, y, escala)."""
    rx, ry, rw, rh = r
    s = min(rw / max(w, 1e-6), rh / max(h, 1e-6))
    x = rx + (rw - w * s) / 2
    y = ry + (rh - h * s) / 2 if alinhar == "centro" else (ry if alinhar == "topo" else ry + rh - h * s)
    return x, y, s


# ---------------------------------------------------------------- texto

def medir(s, tamanho, peso="Bold"):
    return E.largura(s, E.font(peso, tamanho))


def caber(s, largura_max, tamanho_max, peso="Bold", tamanho_min=TEXTO_MIN):
    """Maior tamanho (até tamanho_max) em que o texto cabe em uma linha na largura dada."""
    t = tamanho_max
    while t > tamanho_min and medir(s, t, peso) > largura_max:
        t -= 1
    return t


def texto_em(c, s, r, cor=E.BRANCO, a=1.0, peso="Bold", alinhar="center", tamanho_max=120, destaque=E.AMARELO):
    """Escreve o texto (com *destaques*) ocupando bem a caixa: escolhe tamanho e quebra linhas."""
    x, y, w, h = r
    melhor = None
    for t in range(int(tamanho_max), TEXTO_MIN - 1, -2):
        ls = E.quebrar_marcado(s, t, peso, w)
        alt = len(ls) * t * 1.17
        if alt <= h and max(E.largura(l, E.font(peso, t)) for l in ls) <= w:
            melhor = (t, ls, alt)
            break
    if melhor is None:
        t = TEXTO_MIN
        ls = E.quebrar_marcado(s, t, peso, w)
        melhor = (t, ls, len(ls) * t * 1.17)
    t, ls, alt = melhor
    xx = x + w / 2 if alinhar == "center" else (x if alinhar == "left" else x + w)
    E.linhas(c, ls, y + (h - alt) / 2, t, peso=peso, cor_=cor, destaque=destaque, alpha=a, x=xx, align=alinhar,
             maxw=w)
    return t


# ---------------------------------------------------------------- desenhos encaixados

def svg_em(c, svg, r, a=1.0, alinhar="centro"):
    """Desenha o SVG encaixado na caixa, mantendo a proporção do viewBox."""
    from motor.cenas.desenho import _dom, desenhar_svg, limpar_svg
    _, (vw, vh) = _dom(limpar_svg(svg))
    x, y, s = encaixar(vw, vh, r, alinhar)
    desenhar_svg(c, svg, x + vw * s / 2, y + vh * s / 2, vw * s, a)


def objeto_em(c, nome, r, a=1.0, lt=1.0):
    from motor.ilustracoes.objetos import desenhar_objeto
    cx, cy = centro(r)
    desenhar_objeto(c, nome, cx, cy, min(r[2], r[3]) * 0.95, a, lt)


def marco_em(c, nome, r, lt=1.0, raio=30):
    """Lugar famoso desenhado DENTRO da caixa (recortado: nada vaza)."""
    from motor.ilustracoes.marcos import MARCOS
    x, y, w, h = r
    rr = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), raio, raio)
    c.save()
    c.clipRRect(rr, doAntiAlias=True)
    MARCOS[nome][1](c, x, y, w, h, lt)
    c.restore()
    c.drawRRect(rr, E.paint(E.PAINEL_LN, 1, stroke=2))


# ---------------------------------------------------------------- medição (para o diretor ajustar)

class Registro:
    """Guarda os textos desenhados num quadro: tamanho e caixa aproximada."""

    def __init__(self):
        self.textos: list[tuple[str, float, tuple]] = []

    def limpar(self):
        self.textos.clear()

    def anotar(self, s, tamanho, x, y_base, largura, align="left"):
        if not s or not str(s).strip():
            return
        x0 = x - largura / 2 if align == "center" else (x - largura if align == "right" else x)
        self.textos.append((str(s)[:40], float(tamanho), (x0, y_base - tamanho * 0.8, largura, tamanho)))


REGISTRO = Registro()


def _sobrepoe(a, b, folga=4):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax + folga < bx + bw and bx + folga < ax + aw and ay + folga < by + bh and by + folga < ay + ah


def problemas_do_quadro(alfa_cena: np.ndarray, area=AREA) -> list[str]:
    """Mede um quadro já desenhado: textos pequenos/sobrepostos, ocupação e bordas."""
    probs = []
    pequenos = sorted({f"“{s}” ({t:.0f}px)" for s, t, _ in REGISTRO.textos if t < TEXTO_MIN})
    if pequenos:
        probs.append(f"texto pequeno demais (mínimo {TEXTO_MIN}px): " + ", ".join(pequenos[:4]))
    vistos = set()
    for i, (s1, _, b1) in enumerate(REGISTRO.textos):
        for s2, _, b2 in REGISTRO.textos[i + 1:]:
            if s1 != s2 and _sobrepoe(b1, b2) and (s2, s1) not in vistos:
                vistos.add((s1, s2))
                probs.append(f"textos sobrepostos: “{s1}” e “{s2}”")
                if len(vistos) >= 3:
                    break
    m = alfa_cena > 40
    if m.any():
        ys, xs = np.nonzero(m)
        x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
        ax, ay, aw, ah = area
        ocup_h = (y1 - y0) / ah
        ocup_w = (x1 - x0) / aw
        if ocup_h < 0.5 or ocup_w < 0.6:
            probs.append(f"a cena ocupa pouco da tela ({ocup_w:.0%} da largura e {ocup_h:.0%} da altura da área "
                         f"útil; conteúdo de y={y0} a y={y1}): aumente os elementos e use a área de y={ay:.0f} a "
                         f"{ay + ah:.0f}")
        sobra = (ay + ah) - y1
        if sobra > 220:
            probs.append(f"sobra espaço vazio embaixo da cena ({sobra:.0f}px entre y={y1} e y={ay + ah:.0f}): desça ou "
                         f"aumente os elementos")
        if x0 < 12 or x1 > E.W - 12:
            probs.append("algo encosta/corta na borda lateral da tela")
        if y1 > LIMITE + 10:
            probs.append(f"desenho abaixo de y={LIMITE} (até y={y1}): invade a faixa da legenda da fala")
    else:
        probs.append("quadro sem conteúdo desenhado")
    return probs
