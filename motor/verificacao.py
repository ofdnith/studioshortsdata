"""Prévia por trecho + verificações automáticas (sem API).

Para cada trecho, desenha o quadro do fim do trecho (animações concluídas) e confere:
- texto que precisou encolher muito para caber;
- sobreposição entre título, cena e rodapé (camadas desenhadas separadas);
- conteúdo fora da área segura (y 250–1550) ou na coluna de ícones do Reels;
- número falado que não aparece na tela;
- trecho curto ou longo demais.
E na capa: se há visual de verdade.
"""

import re
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from motor import estilo as E
from motor.estilo import fmt_num
from motor.linha_do_tempo import novas_cenas
from motor.narracao import narrar
from motor.roteiro import Roteiro

# ---------------------------------------------------------------- números por extenso

UNID = {"zero": 0, "um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5, "seis": 6,
        "sete": 7, "oito": 8, "nove": 9, "dez": 10, "onze": 11, "doze": 12, "treze": 13, "catorze": 14,
        "quatorze": 14, "quinze": 15, "dezesseis": 16, "dezessete": 17, "dezoito": 18, "dezenove": 19}
DEZ = {"vinte": 20, "trinta": 30, "quarenta": 40, "cinquenta": 50, "sessenta": 60, "setenta": 70,
       "oitenta": 80, "noventa": 90}
CEM = {"cem": 100, "cento": 100, "duzentos": 200, "duzentas": 200, "trezentos": 300, "trezentas": 300,
       "quatrocentos": 400, "quatrocentas": 400, "quinhentos": 500, "quinhentas": 500, "seiscentos": 600,
       "seiscentas": 600, "setecentos": 700, "setecentas": 700, "oitocentos": 800, "oitocentas": 800,
       "novecentos": 900, "novecentas": 900}
MULT = {"mil": 1_000, "milhao": 1_000_000, "milhoes": 1_000_000, "bilhao": 1_000_000_000,
        "bilhoes": 1_000_000_000}
BASICOS = {**UNID, **DEZ, **CEM}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn")


def _eh_num(tok: str) -> bool:
    return tok in BASICOS or tok in MULT


@dataclass
class Falado:
    valor: float
    texto: str
    porcento: bool = False


def numeros_falados(fala: str) -> list[Falado]:
    """'quarenta e cinco por cento' -> 45 (%); 'mil novecentos e setenta e três' -> 1973;
    'zero vírgula oitenta e dois' -> 0.82; 'sete e meio' -> 7.5."""
    toks = re.findall(r"[a-zà-ú]+", fala.lower())
    toks_n = [_norm(t) for t in toks]
    res, i = [], 0
    def por_cento(k):   # "cento" de "por cento" não é número
        return toks_n[k] == "cento" and k > 0 and toks_n[k - 1] == "por"

    while i < len(toks_n):
        if not _eh_num(toks_n[i]) or por_cento(i):
            i += 1
            continue
        ini = i
        total, atual = 0, 0
        while i < len(toks_n):
            t = toks_n[i]
            if por_cento(i):
                break
            if t in BASICOS:
                atual += BASICOS[t]
            elif t in MULT:
                total += (atual or 1) * MULT[t]
                atual = 0
            elif t == "e" and i + 1 < len(toks_n) and _eh_num(toks_n[i + 1]):
                pass
            else:
                break
            i += 1
        valor = float(total + atual)
        # "e meio"
        if i + 1 < len(toks_n) and toks_n[i] == "e" and toks_n[i + 1] == "meio":
            valor += 0.5
            i += 2
        # "vírgula ..."
        if i < len(toks_n) and toks_n[i] == "virgula":
            j = i + 1
            digitos, acum = [], 0
            while j < len(toks_n) and (toks_n[j] in BASICOS or (toks_n[j] == "e" and j + 1 < len(toks_n)
                                                                and toks_n[j + 1] in BASICOS)):
                if toks_n[j] in BASICOS:
                    v = BASICOS[toks_n[j]]
                    if v < 10 and acum == 0:
                        digitos.append(str(v))
                    else:
                        acum += v
                j += 1
            dec = "".join(digitos) + (str(acum) if acum else "")
            if dec:
                valor = float(f"{int(valor)}.{dec}")
            i = j
        porcento = i + 1 < len(toks_n) and toks_n[i] == "por" and toks_n[i + 1] == "cento"
        res.append(Falado(valor, " ".join(toks[ini:i]), porcento))
    return res


# ---------------------------------------------------------------- números na tela

NUM_TEXTO = re.compile(r"(?<![\w])\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?")


def _nums_texto(s: str) -> set[float]:
    out = set()
    for m in NUM_TEXTO.findall(s or ""):
        out.add(float(m.replace(".", "").replace(",", ".")))
    return out


def numeros_tela(tr, roteiro: Roteiro) -> set[float]:
    c = tr.cena
    nums = set()
    for l in tr.titulo_tela:
        nums |= _nums_texto(l.replace("*", ""))

    def add_valor(v, casas=0):
        nums.add(float(v))
        nums.add(float(fmt_num(v, casas).replace(".", "").replace(",", ".")))

    t = c.tipo
    if t == "barras":
        for d in c.dados:
            add_valor(d.valor, c.casas)
    elif t == "barras_pareadas":
        for g in c.grupos:
            for v in g.valores:
                add_valor(v, 0)
    elif t == "tabela":
        for l in c.linhas:
            for v in l.valores:
                add_valor(v)
    elif t == "barra_empilhada":
        for b in c.barras:
            for p in b.partes:
                nums |= _nums_texto(p.rotulo)
        for lg in c.legenda:
            nums |= _nums_texto(lg.texto)
        if c.destaque:
            nums |= _nums_texto(c.destaque.texto)
    elif t == "dispersao":
        for st in c.estatisticas:
            nums |= _nums_texto(st.valor)
    elif t == "texto_grande":
        nums |= _nums_texto(c.texto) | _nums_texto(c.subtitulo)
    elif t in ("lugar", "mapa"):
        nums |= _nums_texto(c.legenda)
    elif t == "pessoa":
        p = roteiro.pessoa(c.pessoa)
        if p:
            nums |= _nums_texto(p.datas) | _nums_texto(p.feito) | _nums_texto(p.descricao)
    elif t == "diagrama_causal":
        for n in c.nos:
            nums |= _nums_texto(n.rotulo)
    elif t == "linha":
        for se in c.series:
            for v in se.valores:
                add_valor(v, None)
        for r in c.rotulos_x:
            nums |= _nums_texto(r)
        nums |= _nums_texto(c.anotacao)
    elif t == "distribuicao":
        for k in (-2, -1, 0, 1, 2):
            add_valor(round(c.media + k * c.desvio, 2), None)
        for l in c.linhas:
            add_valor(l.x, None)
            nums |= _nums_texto(l.rotulo)
        nums |= _nums_texto(c.rotulo_area) | {c.sombrear_de, c.sombrear_ate}
    elif t in ("histograma", "ranking"):
        for b in (c.barras if t == "histograma" else c.itens):
            add_valor(b.valor, None)
            nums |= _nums_texto(b.rotulo)
    elif t == "pizza":
        total = sum(f.valor for f in c.fatias) or 1
        for f in c.fatias:
            add_valor(f.valor, None)
            add_valor(100 * f.valor / total, 0)
        nums |= _nums_texto(c.centro)
    elif t == "simulacao":
        nums |= {50.0, 3.5, float(c.lancamentos), 10.0, 100.0, 1000.0, 10000.0}
    elif t == "icones":
        nums |= {float(c.total), float(c.destaque)} | _nums_texto(c.rotulo)
    elif t == "numero_grande":
        add_valor(c.valor, c.casas)
        nums |= _nums_texto(c.contexto)
    elif t == "comparacao":
        for lado in (c.esquerda, c.direita):
            nums |= _nums_texto(lado.titulo) | _nums_texto(lado.texto)
    elif t == "linha_do_tempo":
        for e in c.eventos:
            nums |= _nums_texto(e.ano) | _nums_texto(e.texto)
    elif t == "passos":
        for it in c.itens:
            nums |= _nums_texto(it)
    elif t == "citacao":
        nums |= _nums_texto(c.texto) | _nums_texto(c.detalhe)
    elif t == "medidor":
        add_valor(c.valor, None)
        nums |= {c.minimo, c.maximo} | _nums_texto(c.rotulo)
    elif t in ("bolhas", "funil"):
        lst = c.itens if t == "bolhas" else c.etapas
        for x in lst:
            add_valor(x.valor, None)
            nums |= _nums_texto(x.rotulo)
        if t == "funil":
            for a_, b_ in zip(lst, lst[1:]):
                add_valor(100 * b_.valor / (a_.valor or 1), 0)
    elif t == "mapa_calor":
        for linha in c.valores:
            for v in linha:
                add_valor(v, None)
    elif t == "inclinacao":
        for x in c.itens:
            add_valor(x.antes, None)
            add_valor(x.depois, None)
    elif t == "escala":
        for m in c.marcadores:
            add_valor(m.valor, None)
        nums |= {c.minimo, c.maximo, c.faixa_de, c.faixa_ate} | _nums_texto(c.rotulo_faixa)
    elif t == "arvore":
        add_valor(c.total, None)
        for r in c.ramos:
            add_valor(r.valor, None)
            for f in r.filhos:
                add_valor(f.valor, None)
    return nums


def diversidade(roteiro: Roteiro) -> list["Aviso"]:
    """Variedade visual: tipos diferentes, poucos texto_grande, gráficos na maioria, sem repetição longa."""
    from motor.linha_do_tempo import chave_continuidade
    from motor.roteiro import TIPOS_GRAFICO

    trs = [t for t in roteiro.trechos if t.cena.tipo != "chamada"]
    if len(trs) < 6:
        return []
    av = []
    tipos = {t.cena.tipo for t in trs}
    if len(tipos) < 5:
        av.append(Aviso("aviso", f"pouca variedade visual: só {len(tipos)} tipos de cena ({', '.join(sorted(tipos))})"))
    from motor.linha_do_tempo import eh_carimbo
    cenas, ant = 0, None
    for t in trs:
        if eh_carimbo(t.cena):
            continue
        ch = chave_continuidade(t.cena)
        if ch != ant:
            cenas += 1
        ant = ch
    if cenas > max(8, 0.6 * len(trs)):
        av.append(Aviso("aviso", f"{cenas} trocas de cena em {len(trs)} trechos: mantenha cada gráfico por 2–4 "
                                 f"trechos, evoluindo (destaque, nova série, anotação)"))
    n_txt = sum(1 for t in trs if t.cena.tipo == "texto_grande" and t.cena.estilo != "carimbo")
    if n_txt > 2:
        av.append(Aviso("aviso", f"texto_grande em {n_txt} trechos: troque alguns por gráficos ou cenas de apoio"))
    n_graf = sum(1 for t in trs if t.cena.tipo in TIPOS_GRAFICO)
    if n_graf < len(trs) * 0.4:
        av.append(Aviso("aviso", f"poucos gráficos: {n_graf} de {len(trs)} trechos (o ideal é pelo menos 40%)"))
    from motor.linha_do_tempo import chave_continuidade  # noqa: F811
    seq, ant_tipo, ant_chave = 0, None, None
    for t in trs:
        ch = chave_continuidade(t.cena)
        if t.cena.tipo == ant_tipo and ch != ant_chave:
            seq += 1
            if seq == 3:
                av.append(Aviso("aviso", f"“{t.cena.tipo}” em mais de 3 trechos seguidos (cenas diferentes)"))
        else:
            seq = 0 if t.cena.tipo != ant_tipo else seq
        ant_tipo, ant_chave = t.cena.tipo, ch
    return av


def _bate(n: float, tela: set[float]) -> bool:
    for m in tela:
        if abs(n - m) <= max(0.51 if n >= 1 else 0.005, abs(n) * 0.01):
            return True
    return False


# ---------------------------------------------------------------- prévia + checagens

@dataclass
class Aviso:
    nivel: str      # erro | aviso | info
    texto: str


@dataclass
class PreviaTrecho:
    indice: int
    png: str
    inicio: float
    fim: float
    t_quadro: float
    avisos: list[Aviso] = field(default_factory=list)


MIN_TRECHO_S, MAX_TRECHO_S = 1.4, 6.5
ALFA = 60


def _instante(tt) -> float:
    return round(max(tt.inicio + 0.5, min(tt.fim - 0.25, tt.prox - 0.45)), 2)


def _checar_camadas(cam: dict) -> list[Aviso]:
    av = []
    cena, tit, fon = (cam[k] > ALFA for k in ("cena", "titulo", "fonte"))
    if (cena & tit).sum() > 400:
        av.append(Aviso("aviso", "o título encosta/sobrepõe a cena"))
    if (cena & fon).sum() > 150:
        av.append(Aviso("aviso", "a linha de fonte (rodapé) encosta na cena"))
    if "legenda" in cam and (cena & (cam["legenda"] > ALFA)).sum() > 600:
        av.append(Aviso("aviso", "o desenho invade a faixa da legenda (embaixo)"))
    tudo = cena | tit
    fora = tudo[:E.TOPO_SEGURO].sum() + tudo[E.BASE_SEGURA:].sum()
    if fora > 600:
        av.append(Aviso("aviso", "conteúdo fora da área segura do Reels (acima de y=250 ou abaixo de y=1550)"))
    if tudo[1150:E.BASE_SEGURA, 960:].sum() > 2500:
        av.append(Aviso("info", "há conteúdo na coluna de ícones do Reels (canto inferior direito)"))
    return av


def previa(roteiro: Roteiro, pasta: Path, voz: str = "pf_dora", velocidade: float = 1.2,
           duracao_alvo_s: float | None = None, log=print) -> dict:
    """Gera capa + 1 PNG por trecho em `pasta` e devolve os avisos (dict serializável)."""
    from motor.render import Quadros

    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    cron, _ = narrar([t.fala for t in roteiro.trechos], novas_cenas(roteiro), voz, velocidade, pasta,
                     log=lambda m: log(m) if m.endswith("1") else None, trilha="nenhuma", efeitos=False,
                     enfases=[t.enfase for t in roteiro.trechos])
    q = Quadros(roteiro, cron)
    trechos = []
    for tt in q.tts:
        tr = roteiro.trechos[tt.indice]
        t = _instante(tt)
        E.ENCOLHIDOS.clear()
        png = pasta / f"trecho_{tt.indice + 1:02d}.png"
        q.png(t, png)
        avisos = []
        vistos = set()
        for s, pedido, final in E.ENCOLHIDOS:
            if s not in vistos:
                vistos.add(s)
                avisos.append(Aviso("aviso", f"“{s[:50]}” encolheu de {pedido:.0f} para {final:.0f} px para caber: encurte"))
        avisos += _checar_camadas(q.camadas(t))
        dur = tt.fim - tt.inicio
        if dur < MIN_TRECHO_S and tr.cena.tipo != "chamada":
            avisos.append(Aviso("aviso", f"trecho curto ({dur:.1f} s): o texto da tela troca rápido demais"))
        elif dur > MAX_TRECHO_S:
            avisos.append(Aviso("aviso", f"trecho longo ({dur:.1f} s): considere dividir em dois"))
        tela = numeros_tela(tr, roteiro) if roteiro.codigo is None else set()
        if tela:
            for f in numeros_falados(tr.fala):
                relevante = f.valor >= 10 or f.porcento or not float(f.valor).is_integer()
                if relevante and not _bate(f.valor, tela):
                    avisos.append(Aviso("erro", f"a fala diz “{f.texto}” ({fmt_num(f.valor, None)}"
                                                f"{'%' if f.porcento else ''}), mas esse número não aparece na tela"))
        trechos.append(PreviaTrecho(tt.indice, png.name, tt.inicio, tt.fim, t, avisos))

    # capa
    capa = pasta / "capa.png"
    erro_livre = q.livre.erro if q.livre is not None else None
    q.png(0.0, capa, capa=True)
    gerais = []
    cam = q.camadas(0.0, capa=True)
    cobertura = (cam["cena"][E.Y_CENA0:E.Y_CENA1] > 30).mean()
    if cobertura < 0.04:
        gerais.append(Aviso("aviso", f"a capa quase não tem visual ({cobertura:.0%} da área da cena)"))
    if erro_livre:
        gerais.insert(0, Aviso("erro", f"erro na animação: {erro_livre}"))
    if roteiro.codigo is None:
        gerais += diversidade(roteiro)
    if not roteiro.titulo_capa.strip():
        gerais.append(Aviso("aviso", "sem titulo_capa: a capa usa o título do primeiro trecho"))
    if duracao_alvo_s and abs(cron.total - duracao_alvo_s) > duracao_alvo_s * 0.08:
        gerais.append(Aviso("aviso", f"duração real {cron.total:.1f} s, alvo {duracao_alvo_s:g} s"))
    total_avisos = sum(len(t.avisos) for t in trechos) + len(gerais)
    log(f"prévia: {len(trechos)} trechos, {cron.total:.1f} s, {total_avisos} aviso(s)")
    return {"duracao_s": cron.total, "capa": capa.name, "gerais": [asdict(a) for a in gerais],
            "trechos": [asdict(t) for t in trechos], "voz": voz, "velocidade": velocidade}
