"""Validação do roteiro antes da revisão."""

import re
from concurrent.futures import ThreadPoolExecutor

import httpx
from pydantic import ValidationError

from app.roteirista.prompt import faixa_palavras
from motor.cenas.pontos import _embutidos
from motor.ilustracoes.lugares import LUGARES
from motor.ilustracoes.marcos import MARCOS
from motor.ilustracoes.objetos import OBJETOS
from motor.roteiro import Roteiro
from motor.verificacao import diversidade

NUMEROS_FALADOS = re.compile(
    r"\b(dois|duas|três|quatro|cinco|seis|sete|oito|nove|dez|onze|doze|treze|catorze|quatorze|quinze|"
    r"dezesseis|dezessete|dezoito|dezenove|vinte|trinta|quarenta|cinquenta|sessenta|setenta|oitenta|"
    r"noventa|cem|cento|duzentos|trezentos|quinhentos|mil|milhão|milhões|bilhão|bilhões|por cento|"
    r"metade|terço|dobro|triplo)\b", re.I)
CENAS_COM_DADOS = {"barras", "barras_pareadas", "barra_empilhada", "tabela", "dispersao", "grade_graficos",
                   "linha", "histograma", "pizza", "ranking", "numero_grande", "icones", "distribuicao",
                   "medidor", "bolhas", "funil", "mapa_calor", "inclinacao", "escala", "arvore"}


def ilustrativo(tr) -> bool:
    """Gráfico com dados de exemplo (selo na tela) ou simulação: não exige fonte."""
    return tr.cena.tipo == "simulacao" or bool(getattr(tr.cena, "ilustrativo", False))
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) "
                    "Version/17.0 Safari/605.1.15"}


JARGAO = ["independente", "independentes", "variável", "variáveis", "distribuição", "dispersão", "desvio padrão",
          "teorema", "estimador", "inferência", "hipótese", "significância", "estatisticamente significativ",
          "parâmetro", "algoritmo", "amostragem", "correlação", "regressão", "sob condições", "aproximadamente",
          "tende a", "comportamento", "heterogêne", "homogêne", "multivariad", "intervalo de confiança",
          "valor-p", "p-valor", "viés", "variância"]
# palavra citada na fala -> objeto que deveria aparecer
CITADOS = {r"\bmoedas?\b": "moeda", r"\b(um|o|dois|três|dez|cem|jogue|jogar|joga|lançar|lance) dados?\b": "dado",
           r"\baviã?o|aviões\b": "aviao", r"\bbalança\b": "balanca", r"\balvo\b": "alvo", r"\bcérebro\b": "cerebro",
           r"\bampulheta\b": "ampulheta", r"\btermômetro\b": "termometro", r"\btroféu\b": "trofeu",
           r"\bcadeado\b": "cadeado", r"\blâmpada\b": "lampada", r"\bcomputador\b": "computador",
           r"\brelógio\b": "relogio", r"\bcoração\b": "coracao", r"\blupa\b": "lupa"}


def _jargao(fala: str, tema: str) -> list[str]:
    f, t = fala.lower(), tema.lower()
    return [j for j in JARGAO if j in f and j not in t]


def _objetos_da_cena(c) -> list[str]:
    nomes = [getattr(c, "objeto", None)]
    if c.tipo == "comparacao":
        nomes += [c.esquerda.objeto, c.direita.objeto]
    return [n for n in nomes if n]


def cita_numero(tr) -> bool:
    if any(re.search(r"\d", l) for l in tr.titulo_tela):
        return True
    if tr.cena.tipo in CENAS_COM_DADOS:
        return True
    return bool(NUMEROS_FALADOS.search(tr.fala))


def checar_url(url: str) -> dict:
    """{'status': int|None, 'ok': bool, 'nota': str}"""
    try:
        with httpx.Client(follow_redirects=True, timeout=12, headers=UA) as c:
            r = c.get(url)
        st = r.status_code
        if st < 400:
            return {"status": st, "ok": True, "nota": "responde"}
        if st in (401, 403, 429):
            return {"status": st, "ok": False, "nota": "bloqueia acesso automático: abra e confira"}
        return {"status": st, "ok": False, "nota": f"erro {st}"}
    except httpx.HTTPError as e:
        return {"status": None, "ok": False, "nota": f"não respondeu ({type(e).__name__})"}


def checar_urls(urls: list[str], cache: dict | None = None) -> dict[str, dict]:
    cache = cache or {}
    faltam = [u for u in dict.fromkeys(urls) if u not in cache]
    res = {u: cache[u] for u in urls if u in cache}
    if faltam:
        with ThreadPoolExecutor(max_workers=6) as ex:
            for u, r in zip(faltam, ex.map(checar_url, faltam)):
                res[u] = r
    return res


def validar(roteiro_json: dict, duracao_alvo_s: float, urls_abertas: list[str] | None = None,
            cache_urls: dict | None = None, checar_links: bool = True) -> dict:
    """Devolve {'problemas': [{'nivel', 'texto', 'trecho'}], 'palavras', 'faixa', 'urls': {...}}."""
    problemas = []

    def p(nivel, texto, trecho=None):
        problemas.append({"nivel": nivel, "texto": texto, "trecho": trecho})

    try:
        r = Roteiro.model_validate(roteiro_json)
    except ValidationError as e:
        for err in e.errors()[:10]:
            p("erro", f"Formato inválido em {'.'.join(str(x) for x in err['loc'])}: {err['msg']}")
        return {"problemas": problemas, "palavras": 0, "faixa": faixa_palavras(duracao_alvo_s), "urls": {}}

    ids = {f.id for f in r.fontes}
    ids_desenho, ancora_desenho = set(), None
    for i, tr in enumerate(r.trechos):
        if tr.fonte_id and tr.fonte_id not in ids:
            p("erro", f"fonte_id “{tr.fonte_id}” não existe em fontes", i)
        elif not tr.fonte_id and cita_numero(tr) and tr.cena.tipo != "chamada" and not ilustrativo(tr):
            p("erro", "trecho com número/dado sem fonte_id", i)
        if tr.cena.tipo == "pessoa" and not r.pessoa(tr.cena.pessoa):
            p("erro", f"pessoa “{tr.cena.pessoa}” não está em pessoas", i)
        for ref in getattr(tr.cena, "conjuntos", []) or []:
            if isinstance(ref, str) and ref not in _embutidos():
                p("erro", f"conjunto de pontos desconhecido: {ref}", i)
        if tr.cena.tipo == "lugar" and tr.cena.marco and tr.cena.marco not in MARCOS and \
                tr.cena.marco not in LUGARES:
            p("erro", f"marco desconhecido: “{tr.cena.marco}”", i)
        termos = _jargao(tr.fala, r.tema)
        if termos:
            p("aviso", f"palavra técnica na fala: {', '.join(termos)} — troque por palavras do dia a dia", i)
        for frase in re.split(r"[.!?;:]", tr.fala):
            if len(frase.split()) > 16:
                p("aviso", f"frase longa ({len(frase.split())} palavras): divida em duas", i)
                break
            if len(frase.split()) > 10 and "," not in frase and "…" not in frase:
                p("aviso", "frase de mais de 10 palavras sem vírgula: a voz fica sem respiro", i)
                break
        mostrados = set(_objetos_da_cena(tr.cena)) | ({tr.ilustracao} if tr.ilustracao else set())
        if tr.cena.tipo == "desenho":   # desenho sob medida conta como "mostrado"
            mostrados |= set(CITADOS.values())
        if tr.cena.tipo == "simulacao":
            mostrados.add(tr.cena.experimento)
        for padrao, obj in CITADOS.items():
            if re.search(padrao, tr.fala.lower()) and obj not in mostrados:
                p("aviso", f"a fala cita “{obj}”, mas ele não aparece na tela (use ilustracao: {obj})", i)
        if tr.cena.tipo == "desenho":
            from motor.cenas.desenho import instante_da_palavra, svg_valido
            ancora = tr.cena.camadas[0].id
            if ancora != ancora_desenho:
                ids_desenho, ancora_desenho = set(), ancora
            for cam in tr.cena.camadas:
                if not svg_valido(cam.svg):
                    p("erro", f"desenho “{cam.id}”: SVG inválido", i)
                # a palavra só vale na fala em que a camada aparece pela primeira vez
                if cam.id not in ids_desenho and cam.na_palavra and \
                        instante_da_palavra(tr.fala, cam.na_palavra, 0, 1) is None:
                    p("aviso", f"desenho “{cam.id}”: a palavra “{cam.na_palavra}” não está na fala", i)
                ids_desenho.add(cam.id)
        else:
            ids_desenho, ancora_desenho = set(), None
        if tr.ilustracao and tr.ilustracao not in OBJETOS:
            p("erro", f"ilustração desconhecida: “{tr.ilustracao}”", i)
        for nome_obj in _objetos_da_cena(tr.cena):
            if nome_obj not in OBJETOS:
                p("erro", f"objeto desconhecido: “{nome_obj}” (disponíveis: {', '.join(sorted(OBJETOS))})", i)
        if len(tr.titulo_tela) > 2:
            p("aviso", "título com mais de 2 linhas", i)
        for linha in tr.titulo_tela:
            if len(linha.replace("*", "")) > 26:
                p("aviso", f"linha de título longa ({len(linha.replace('*', ''))} caracteres): pode diminuir a fonte", i)
    if r.trechos[0].cena.tipo in ("texto_grande", "chamada"):
        p("aviso", "o primeiro trecho vira a capa e não tem cena visual", 0)
    if r.trechos[-1].cena.tipo != "chamada":
        p("aviso", "o último trecho não é a cena chamada")
    for f in r.fontes:
        if not f.trecho_que_comprova.strip():
            p("aviso", f"fonte “{f.id}” sem trecho que comprova")
        if urls_abertas is not None and f.url not in urls_abertas:
            p("aviso", f"fonte “{f.id}”: a URL não aparece entre as páginas abertas com web fetch")
    com_cena = {tr.cena.pessoa.lower() for tr in r.trechos if tr.cena.tipo == "pessoa"}
    for pe in r.pessoas:
        if pe.nome.lower() not in com_cena:
            p("aviso", f"{pe.nome} é citada mas não aparece com a cena pessoa (ilustração)")
        if pe.cor_pele is None or pe.idade_na_epoca is None:
            p("info", f"{pe.nome}: sem cor de pele ou idade com fonte, o vídeo usa silhueta neutra")

    for a in diversidade(r):
        p(a.nivel, a.texto)
    if len(r.trechos) > 6 and not any(t.enfase for t in r.trechos):
        p("aviso", "nenhum trecho com ênfase: marque 2 a 4 momentos-chave (a virada, a revelação, a lição)")

    palavras = r.contar_palavras()
    mn, alvo, mx = faixa_palavras(duracao_alvo_s)
    if not mn <= palavras <= mx:
        p("aviso", f"{palavras} palavras: fora da faixa {mn}–{mx} para {duracao_alvo_s:g} s")

    urls = checar_urls([f.url for f in r.fontes], cache_urls) if checar_links else (cache_urls or {})
    for f in r.fontes:
        st = urls.get(f.url)
        if st and not st["ok"]:
            p("erro" if st["status"] not in (401, 403, 429) else "aviso",
              f"fonte “{f.id}”: URL {st['nota']}")
    return {"problemas": problemas, "palavras": palavras, "faixa": [mn, alvo, mx], "urls": urls}
