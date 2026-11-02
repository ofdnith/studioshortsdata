"""Modo livre: a IA escreve o código da animação (como nos vídeos feitos no chat).

O código define `def quadro(c, t, v)`: desenha o quadro do instante t (s) no canvas skia `c`.
`v` dá os tempos da narração (v.S(i), v.E(i), v.palavra(i, "texto")...).

Segurança (o código vem de um modelo de IA):
1. Análise estática (AST): sem import, sem nomes/atributos com "_" no início, sem open/exec/eval
   etc.; só as funções de desenho injetadas e builtins seguros.
2. O render roda num processo separado dentro da caixa de areia do macOS (sem rede e sem
   escrita fora da pasta do vídeo) — ver `motor/sandbox.py`.
"""

import ast
import math
import random
import traceback

import numpy as np
import skia

from motor import estilo as E
from motor.cenas.desenho import desenhar_svg, instante_da_palavra
from motor.ilustracoes.marcos import MARCOS
from motor.ilustracoes.objetos import desenhar_objeto
from motor.ilustracoes.pessoas import caricatura, retrato, silhueta

NOMES_PROIBIDOS = {"open", "exec", "eval", "compile", "__import__", "globals", "locals", "vars", "getattr",
                   "setattr", "delattr", "input", "breakpoint", "help", "memoryview", "type", "object", "super",
                   "classmethod", "staticmethod", "property", "dir", "id", "hash", "exit", "quit"}
# atributos que dariam acesso a arquivos, processos ou introspecção dentro das bibliotecas permitidas
NP_PROIBIDOS = {"load", "save", "savez", "savez_compressed", "savetxt", "loadtxt", "genfromtxt", "fromfile",
                "memmap", "ctypeslib", "lib", "DataSource", "fromregex"}
ATRIBUTOS_PROIBIDOS = {"loads", "tofile", "os", "sys", "format", "format_map",
                       "MakeFromFileName", "MakeFromFile", "open", "Open", "system", "popen", "subprocess",
                       "f_globals", "gi_frame", "co_code", "mro", "builtins", "importlib", "ctypes"}
BUILTINS_SEGUROS = {n: __builtins__[n] if isinstance(__builtins__, dict) else getattr(__builtins__, n) for n in (
    "abs", "min", "max", "range", "len", "enumerate", "zip", "round", "int", "float", "str", "list", "dict",
    "tuple", "set", "sorted", "reversed", "sum", "any", "all", "map", "filter", "isinstance", "pow", "divmod",
    "bool", "True", "False", "None", "ValueError", "ZeroDivisionError", "Exception", "frozenset", "slice",
) if (isinstance(__builtins__, dict) and n in __builtins__) or hasattr(__builtins__, n)}


def validar_codigo(src: str) -> list[str]:
    """Erros de segurança/estrutura; lista vazia = código aceito."""
    try:
        arvore = ast.parse(src)
    except SyntaxError as e:
        return [f"erro de sintaxe na linha {e.lineno}: {e.msg}"]
    erros = []
    for no in ast.walk(arvore):
        if isinstance(no, (ast.Import, ast.ImportFrom)):
            erros.append(f"linha {no.lineno}: import não é permitido (as funções já estão disponíveis)")
        elif isinstance(no, ast.Name) and ((no.id.startswith("_") and no.id != "_") or no.id in NOMES_PROIBIDOS):
            erros.append(f"linha {no.lineno}: nome não permitido: {no.id}")
        elif isinstance(no, ast.Attribute) and (no.attr.startswith("_") or no.attr in ATRIBUTOS_PROIBIDOS
                                                 or "File" in no.attr):
            erros.append(f"linha {no.lineno}: atributo não permitido: {no.attr}")
        elif isinstance(no, ast.Attribute) and isinstance(no.value, ast.Name) and no.value.id == "np" and \
                no.attr in NP_PROIBIDOS:
            erros.append(f"linha {no.lineno}: np.{no.attr} não é permitido")
        elif isinstance(no, (ast.Global, ast.Nonlocal, ast.AsyncFunctionDef, ast.Await, ast.ClassDef)):
            erros.append(f"linha {no.lineno}: construção não permitida ({type(no).__name__})")
        elif isinstance(no, (ast.While,)):
            erros.append(f"linha {no.lineno}: while não é permitido (use for com range)")
        elif isinstance(no, ast.Constant) and isinstance(no.value, str) and len(no.value) > 40_000:
            erros.append(f"linha {no.lineno}: texto grande demais")
    if not any(isinstance(n, ast.FunctionDef) and n.name == "quadro" for n in arvore.body):
        erros.append("falta a função def quadro(c, t, v)")
    return erros


class Tempos:
    """Tempos da narração para o código da IA."""

    def __init__(self, roteiro, cron):
        self.roteiro = roteiro
        self.marcas = cron.trechos
        self.total = cron.total
        self.n = len(self.marcas)

    def S(self, i):
        """Início do trecho i (0 = primeiro)."""
        return self.marcas[i].inicio

    def E(self, i):
        """Fim da fala do trecho i."""
        return self.marcas[i].fim

    def prox(self, i):
        """Início do trecho seguinte (ou o fim do vídeo)."""
        return self.marcas[i + 1].inicio if i + 1 < self.n else self.total

    def palavra(self, i, texto):
        """Instante (estimado) em que a palavra é dita no trecho i; se não achar, o início do trecho."""
        t = instante_da_palavra(self.roteiro.trechos[i].fala, texto, self.S(i), self.E(i))
        return t if t is not None else self.S(i)

    def trecho_em(self, t):
        """Índice do trecho que está sendo falado (ou o último que começou) em t."""
        k = 0
        for i, m in enumerate(self.marcas):
            if t >= m.inicio - 0.05:
                k = i
        return k

    def fala(self, i):
        return self.roteiro.trechos[i].fala


def _chamada(c, a, lt=1.0, texto_="Siga para mais curiosidades de dados"):
    """Fechamento padrão do canal (mini gráfico + pílula)."""
    for i, h in enumerate([0.45, 0.7, 0.55, 0.9, 1.0]):
        k = E.ease_out((lt - i * 0.08) / 0.4)
        hh = 220 * h * k
        E.barra(c, 380 + i * 66, 900 - hh, 48, hh, E.AMARELO if i == 4 else E.CIANO, a * (1 if i == 4 else 0.6), r=10)
    E.pilula(c, texto_, E.W / 2, 1040, 38, E.AMARELO, E.FUNDO, a, peso="ExtraBold", h=96)


def _ambiente() -> dict:
    """Tudo o que o código da IA pode usar (sem precisar de import)."""
    amb = {
        "math": math, "np": np, "skia": skia, "random": random.Random(7),
        "W": E.W, "H": E.H,
        # cores
        "FUNDO": E.FUNDO, "BRANCO": E.BRANCO, "CINZA": E.CINZA, "AMARELO": E.AMARELO, "VERMELHO": E.VERMELHO,
        "VERDE": E.VERDE, "CIANO": E.CIANO, "ROXO": E.ROXO, "PAINEL": E.PAINEL, "PAINEL_LN": E.PAINEL_LN,
        "GRADE": E.GRADE, "hx": E.hx, "misturar": E.misturar, "C": E.C, "cor": E.cor,
        # animação
        "clamp": E.clamp, "ease_out": E.ease_out, "ease_io": E.ease_io, "back_out": E.back_out, "vis": E.vis,
        # desenho
        "paint": E.paint, "font": E.font, "texto": E.texto, "linhas": E.linhas, "barra": E.barra,
        "painel": E.painel, "pilula": E.pilula, "check": E.check, "seta": E.seta, "seta_curva": E.seta_curva,
        "fmt_num": E.fmt_num, "com_unidade": E.com_unidade, "quebrar": E.quebrar_marcado,
        "objeto": desenhar_objeto, "svg": desenhar_svg, "retrato": retrato, "caricatura": caricatura,
        "silhueta": silhueta, "chamada": _chamada,
        "marco": lambda c, nome, X, Y, PW, PH, lt: MARCOS[nome][1](c, X, Y, PW, PH, lt),
    }
    return amb


def compilar(src: str):
    """Compila o código validado e devolve a função quadro."""
    erros = validar_codigo(src)
    if erros:
        raise ValueError("; ".join(erros[:5]))
    ns = _ambiente()
    ns["__builtins__"] = BUILTINS_SEGUROS
    exec(compile(src, "<roteiro>", "exec"), ns)   # noqa: S102 — código validado acima, roda na caixa de areia
    return ns["quadro"]


class Livre:
    """Desenha os quadros do modo livre; guarda o primeiro erro de execução para mostrar na revisão."""

    def __init__(self, roteiro, cron):
        self.tempos = Tempos(roteiro, cron)
        self.quadro = compilar(roteiro.codigo)
        self.erro: str | None = None

    def desenhar(self, c, t):
        c.save()
        try:
            self.quadro(c, t, self.tempos)
        except Exception as e:
            if self.erro is None:
                linha = traceback.extract_tb(e.__traceback__)[-1]
                self.erro = f"t={t:.2f}s, linha {linha.lineno}: {type(e).__name__}: {e}"
            E.texto(c, "⚠ erro na animação", E.W / 2, 1000, 40, E.VERMELHO, 1, "Bold", "center")
        finally:
            c.restore()


def testar_codigo(roteiro, quadros: int = 30) -> dict:
    """Desenha alguns quadros com tempos estimados (sem narrar) para achar erros rápido."""
    from motor.narracao import Cronograma, Marca

    t, marcas = 0.1, []
    for tr in roteiro.trechos:
        d = max(1.0, len(tr.fala.split()) / 2.9)
        marcas.append(Marca(round(t, 2), round(t + d, 2), tr.fala))
        t += d + 0.25
    cron = Cronograma(round(t + 1.5, 2), marcas)
    try:
        lv = Livre(roteiro, cron)
    except Exception as e:
        return {"ok": False, "erro": f"{type(e).__name__}: {e}"}
    surf = skia.Surface.MakeRaster(E.INFO)
    for k in range(quadros):
        lv.desenhar(surf.getCanvas(), cron.total * k / (quadros - 1))
        if lv.erro:
            return {"ok": False, "erro": lv.erro}
    return {"ok": True, "erro": None}
