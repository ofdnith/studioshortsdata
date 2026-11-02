"""Schema do roteiro para o Claude (ferramenta strict `entregar_roteiro`) e conversão para o motor.

A saída estruturada tem limites (24 campos opcionais, 16 uniões por schema). Por isso este
schema é diferente do `motor.roteiro`: todos os campos são obrigatórios e "ausente" é um valor
vazio ("", [], -1, 0, "nenhum"/"desconhecido"). `para_motor()` converte para o formato do motor.
"""

from motor.cenas.pontos import _embutidos
from motor.ilustracoes.lugares import LUGARES
from motor.ilustracoes.marcos import MARCOS
from motor.ilustracoes.objetos import OBJETOS

CORES = ["", "amarelo", "vermelho", "verde", "ciano", "roxo", "cinza", "branco", "laranja", "rosa"]


def _obj(props: dict, descricao: str = "") -> dict:
    o = {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}
    if descricao:
        o["description"] = descricao
    return o


def _arr(itens: dict, descricao: str = "") -> dict:
    a = {"type": "array", "items": itens}
    if descricao:
        a["description"] = descricao
    return a


def _s(descricao: str = "") -> dict:
    return {"type": "string", "description": descricao} if descricao else {"type": "string"}


def _e(valores: list, descricao: str = "") -> dict:
    d = {"type": "string", "enum": valores}
    if descricao:
        d["description"] = descricao
    return d


NUM = {"type": "number"}
INT = {"type": "integer"}
BOOL = {"type": "boolean"}
COR = _e(CORES, "cor nomeada; \"\" = automática")


def _objeto(opcional=True):
    return _e(([""] if opcional else []) + sorted(OBJETOS), "objeto da biblioteca" + (" ou \"\"" if opcional else ""))


def _tipo(nome):
    return {"type": "string", "const": nome}


def conjuntos_embutidos() -> list[str]:
    return sorted(_embutidos())


def _cenas() -> list[dict]:
    reta = _obj({"a": NUM, "b": NUM}, "y = a + b·x")
    ponto = _obj({"x": NUM, "y": NUM})
    conjunto = _obj({
        "embutido": _e([""] + conjuntos_embutidos(), "conjunto embutido, ou \"\" para usar 'pontos'"),
        "nome": _s("nome curto mostrado na etiqueta"),
        "pontos": _arr(ponto, "pontos reais (vazio se usar 'embutido')"),
    })
    return [
        _obj({"tipo": _tipo("barras"),
              "dados": _arr(_obj({"rotulo": _s(), "valor": NUM, "cor": COR}), "2 a 5 valores"),
              "unidade": _s("ex.: \"%\" ou \"\""), "casas": INT,
              "destaque": _s("rótulo em foco, ou \"\"")}),
        _obj({"tipo": _tipo("barras_pareadas"),
              "series": _arr(_obj({"nome": _s(), "cor": COR}), "2 ou 3 séries"),
              "grupos": _arr(_obj({"rotulo": _s("curto, ex.: A"), "valores": _arr(NUM, "um por série")}),
                             "até 7 grupos"),
              "unidade": _s(), "marcar_vencedor": _s("nome da série a marcar com ✓ onde vence, ou \"\""),
              "destaque": _s("rótulo do grupo em foco, ou \"\"")}),
        _obj({"tipo": _tipo("barra_empilhada"),
              "barras": _arr(_obj({"rotulo": _s(), "cor": COR,
                                   "partes": _arr(_obj({"rotulo": _s("curto"), "valor": NUM, "cor": COR}))}),
                             "1 a 3 barras (100% cada)"),
              "legenda": _arr(_obj({"cor": COR, "texto": _s()})),
              "destaque": _obj({"barra": _s("rótulo da barra, ou \"\" sem destaque"),
                                "partes": _arr(_s()), "texto": _s("pílula, ex.: 52% em A e B")})}),
        _obj({"tipo": _tipo("dispersao"),
              "conjuntos": _arr(conjunto, "mostrados em sequência com morph"),
              "estatisticas": _arr(_obj({"rotulo": _s(), "valor": _s()}), "até 3 cartões"),
              "retas": _arr(reta, "0 ou 1 reta"), "mostrar_nome": BOOL}),
        _obj({"tipo": _tipo("grade_graficos"),
              "graficos": _arr(_obj({"titulo": _s("curto, ex.: I"), "conjunto": conjunto,
                                     "retas": _arr(reta, "0 ou 1"), "curva": BOOL,
                                     "outliers": _arr(ponto, "0 ou 1 ponto a circular quando em foco")}),
                               "2 a 4 gráficos"),
              "foco": {"type": "integer", "description": "índice do gráfico em foco (0..), -1 = nenhum"}}),
        _obj({"tipo": _tipo("tabela"),
              "colunas": _arr(_s(), "até 4"), "linhas": _arr(_obj({"rotulo": _s(), "valores": _arr(NUM)}), "até 4"),
              "unidade": _s(), "unidades": _arr(_s(), "uma unidade por coluna (ex.: [\"\", \"R$\"]) ou []"),
              "vencedor": _e(["maior", "menor", "nenhum"]),
              "coluna_total": _obj({"usar": BOOL}, "última coluna é o total")}),
        _obj({"tipo": _tipo("diagrama_causal"),
              "nos": _arr(_obj({"id": _s(), "rotulo": _s("curto"), "cor": COR}), "2 a 4 nós"),
              "setas": _arr(_obj({"de": _s(), "para": _s(), "tracejada": BOOL, "rotulo": _s()})),
              "subtitulo": _s(), "layout": _e(["auto", "linha", "ciclo"], "ciclo = laço de retroalimentação")}),
        _obj({"tipo": _tipo("pessoa"), "pessoa": _s("nome exatamente como em 'pessoas'")}),
        _obj({"tipo": _tipo("lugar"), "lugar": _s("nome do lugar, como aparece no vídeo"),
              "marco": _e(sorted(LUGARES) + sorted(MARCOS), "ilustração: algo famoso que represente o lugar"),
              "legenda": _s("pílula embaixo; \"\" = usa o nome"), "lat": NUM, "lon": NUM}),
        _obj({"tipo": _tipo("mapa"), "lugar": _s("nome do lugar"), "lat": NUM, "lon": NUM, "legenda": _s()}),
        _obj({"tipo": _tipo("texto_grande"), "texto": _s("frase com *destaques*"),
              "estilo": _e(["frase", "carimbo", "palavra", "caixa"], "palavra = 1–2 palavras gigantes"),
              "subtitulo": _s(), "objeto": _objeto()}),
        # gráficos novos
        _obj({"tipo": _tipo("linha"), "rotulos_x": _arr(_s(), "rótulos do eixo x (ex.: anos)"),
              "series": _arr(_obj({"nome": _s(), "cor": COR, "valores": _arr(NUM, "um por rótulo x")}), "1 a 3"),
              "unidade": _s(), "destaque": _s("rótulo x anotado, ou \"\""), "anotacao": _s(), "ilustrativo": BOOL}),
        _obj({"tipo": _tipo("distribuicao"), "forma": _e(["normal", "assimetrica", "bimodal", "uniforme"]),
              "media": NUM, "desvio": NUM, "sombrear_de": NUM, "sombrear_ate": NUM,
              "rotulo_area": _s("ex.: 95%"), "linhas": _arr(_obj({"x": NUM, "rotulo": _s(), "cor": COR}), "0 a 3"),
              "rotulo_eixo": _s(), "amostras": BOOL, "ilustrativo": BOOL}),
        _obj({"tipo": _tipo("histograma"), "barras": _arr(_obj({"rotulo": _s("faixa"), "valor": NUM}), "3 a 20"),
              "unidade": _s(), "destaque": _arr(_s(), "rótulos destacados"), "rotulo_eixo": _s(), "ilustrativo": BOOL}),
        _obj({"tipo": _tipo("pizza"), "fatias": _arr(_obj({"rotulo": _s(), "valor": NUM, "cor": COR}), "2 a 6"),
              "destaque": _s(), "rosca": BOOL, "centro": _s("texto no meio da rosca"), "ilustrativo": BOOL}),
        _obj({"tipo": _tipo("ranking"), "itens": _arr(_obj({"rotulo": _s(), "valor": NUM, "cor": COR}), "2 a 8"),
              "unidade": _s(), "destaque": _s(), "ilustrativo": BOOL}),
        _obj({"tipo": _tipo("simulacao"), "experimento": _e(["moeda", "dado"]), "lancamentos": INT}),
        _obj({"tipo": _tipo("medidor"), "valor": NUM, "minimo": NUM, "maximo": NUM, "unidade": _s(),
              "rotulo": _s(), "zonas": BOOL, "cor": COR, "ilustrativo": BOOL}),
        _obj({"tipo": _tipo("bolhas"), "itens": _arr(_obj({"rotulo": _s(), "valor": NUM, "cor": COR}), "2 a 5"),
              "unidade": _s(), "destaque": _s(), "ilustrativo": BOOL}),
        _obj({"tipo": _tipo("funil"), "etapas": _arr(_obj({"rotulo": _s(), "valor": NUM, "cor": COR}), "2 a 6"),
              "unidade": _s(), "ilustrativo": BOOL}),
        _obj({"tipo": _tipo("mapa_calor"), "linhas": _arr(_s(), "2 a 7"), "colunas": _arr(_s(), "2 a 7"),
              "valores": _arr(_arr(NUM), "uma lista por linha"), "unidade": _s(), "ilustrativo": BOOL}),
        _obj({"tipo": _tipo("inclinacao"), "rotulo_antes": _s(), "rotulo_depois": _s(),
              "itens": _arr(_obj({"rotulo": _s(), "antes": NUM, "depois": NUM, "cor": COR}), "1 a 6"),
              "unidade": _s(), "destaque": _s(), "ilustrativo": BOOL}),
        _obj({"tipo": _tipo("escala"), "minimo": NUM, "maximo": NUM,
              "marcadores": _arr(_obj({"valor": NUM, "rotulo": _s(), "cor": COR}), "1 a 4"), "unidade": _s(),
              "faixa_de": NUM, "faixa_ate": NUM, "rotulo_faixa": _s(), "ilustrativo": BOOL}),
        _obj({"tipo": _tipo("arvore"), "total": NUM, "rotulo_total": _s(),
              "ramos": _arr(_obj({"rotulo": _s(), "valor": NUM, "cor": COR,
                                  "filhos": _arr(_obj({"rotulo": _s(), "valor": NUM, "cor": COR}), "0 a 3")}), "2 a 3"),
              "unidade": _s(), "destaque": _arr(_s(), "rótulos destacados"), "ilustrativo": BOOL}),
        _obj({"tipo": _tipo("desenho"), "fundo": _e(["nenhum", "painel", "ceu"]),
              "camadas": _arr(_obj({
                  "id": _s("nome curto; a 1ª camada identifica a cena"),
                  "svg": _s("desenho SVG flat, viewBox 0 0 100 100, só formas (sem texto, sem imagens)"),
                  "x": NUM, "y": NUM, "largura": NUM,
                  "entrada": _e(["pop", "fade", "desliza_esquerda", "desliza_direita", "desliza_baixo", "desenhar"]),
                  "na_palavra": _s("palavra da fala em que a camada aparece, ou \"\""),
                  "atraso": NUM, "movimento": _e(["nenhum", "flutuar", "balancar", "pulsar", "girar", "tremer"]),
                  "rotulo": _s("texto curto embaixo, ou \"\"")}), "1 a 8 camadas")}),
        # cenas de apoio
        _obj({"tipo": _tipo("icones"), "total": INT, "destaque": INT, "icone": _e(["pessoa", "circulo"]),
              "rotulo": _s("ex.: *1* em cada 4"), "cor": COR}),
        _obj({"tipo": _tipo("numero_grande"), "valor": NUM, "prefixo": _s(), "sufixo": _s(), "casas": INT,
              "contexto": _s(), "objeto": _objeto()}),
        _obj({"tipo": _tipo("objeto"), "objeto": _objeto(False), "legenda": _s("frase com *destaque*")}),
        _obj({"tipo": _tipo("comparacao"), "estilo": _e(["versus", "mito_fato", "antes_depois"]),
              "esquerda": _obj({"titulo": _s(), "texto": _s(), "objeto": _objeto()}),
              "direita": _obj({"titulo": _s(), "texto": _s(), "objeto": _objeto()}),
              "vencedor": _e(["", "esquerda", "direita"])}),
        _obj({"tipo": _tipo("linha_do_tempo"), "eventos": _arr(_obj({"ano": _s(), "texto": _s()}), "2 a 6"),
              "destaque": {"type": "integer", "description": "índice do evento em destaque, -1 = nenhum"}}),
        _obj({"tipo": _tipo("passos"), "itens": _arr(_s(), "2 a 5"), "marcador": _e(["numero", "check", "x"])}),
        _obj({"tipo": _tipo("citacao"), "texto": _s(), "autor": _s(), "detalhe": _s(),
              "pessoa": _s("nome em 'pessoas' para mostrar retrato, ou \"\"")}),
        _obj({"tipo": _tipo("chamada"), "texto": _s("normalmente: Siga para mais curiosidades de dados")}),
    ]


def schema_roteiro() -> dict:
    trecho = _obj({
        "fala": _s("texto narrado, números por extenso, nomes estrangeiros como se pronunciam"),
        "titulo_tela": _arr(_s("até ~22 caracteres; palavras-chave com *asteriscos*"), "1 ou 2 linhas (0 só na chamada)"),
        "cena": {"anyOf": _cenas()},
        "fonte_id": _s("id em 'fontes', ou \"\" se o trecho não cita fato"),
        "ilustracao": _objeto(),
        "enfase": {"type": "boolean", "description": "momento-chave: narrado mais devagar, com pausa antes"},
        "legenda": _s("a fala como aparece na legenda: grafia correta (Berkeley, não Bérqueli) e números em "
                      "algarismos (45%, 1973); \"\" se igual à fala"),
    })
    fonte = _obj({
        "id": _s(), "rodape": _s("ex.: Bickel, Hammel & O'Connell (1975), Science"),
        "citacao": _s("referência completa"), "url": _s("URL oficial que você abriu com web_fetch"),
        "trecho_que_comprova": _s("frase copiada da página aberta, no idioma original"),
    })
    pessoa = _obj({
        "nome": _s(), "datas": _s("ex.: 1922–2019"), "descricao": _s("ex.: estatístico britânico"),
        "feito": _s("o que fez, curto"), "genero": _e(["masculino", "feminino", "desconhecido"]),
        "cor_pele": _e(["clara", "media", "morena", "escura", "desconhecida"]),
        "idade_na_epoca": {"type": "integer", "description": "idade na época do fato; 0 = desconhecida"},
        "fonte_id": _s(),
    })
    return _obj({
        "tema": _s(), "titulo_capa": _s("com *destaque*"),
        "legenda": _s("legenda do post, 2 a 4 frases"), "hashtags": _arr(_s("com #")),
        "trechos": _arr(trecho), "fontes": _arr(fonte), "pessoas": _arr(pessoa),
        "notas_para_revisao": _s("dúvidas, números que não conseguiu confirmar, escolhas de arredondamento"),
    })


FERRAMENTA = {
    "name": "entregar_roteiro",
    "description": "Entrega o roteiro final do vídeo. Chame uma única vez, no fim, depois de pesquisar e "
                   "abrir as fontes oficiais.",
    "strict": True,
    "input_schema": schema_roteiro(),
}


# ---------------------------------------------------------------- conversão

def _limpo(d: dict) -> dict:
    return {k: v for k, v in d.items() if v not in ("", None, [])}


def _cor(c):
    return c or None


def _conj(c: dict):
    if c.get("embutido"):
        return c["embutido"]
    return {"nome": c.get("nome") or "dados", "pontos": c.get("pontos", [])}


def _cena(c: dict) -> dict:
    t = c["tipo"]
    if t == "barras":
        return {"tipo": t, "unidade": c["unidade"], "casas": max(0, c["casas"]),
                "destaque": c["destaque"] or None,
                "dados": [_limpo(d) | {"valor": d["valor"]} for d in c["dados"]]}
    if t == "barras_pareadas":
        return {"tipo": t, "unidade": c["unidade"], "marcar_vencedor": c["marcar_vencedor"] or None,
                "destaque": c["destaque"] or None, "series": [_limpo(s) for s in c["series"]],
                "grupos": c["grupos"]}
    if t == "barra_empilhada":
        d = c["destaque"]
        return {"tipo": t, "legenda": [lg for lg in c["legenda"] if lg["texto"]],
                "destaque": d if d.get("barra") else None,
                "barras": [_limpo(b) | {"partes": [_limpo(p) | {"valor": p["valor"]} for p in b["partes"]]}
                           for b in c["barras"]]}
    if t == "dispersao":
        return {"tipo": t, "conjuntos": [_conj(x) for x in c["conjuntos"]], "estatisticas": c["estatisticas"],
                "reta": c["retas"][0] if c["retas"] else None, "mostrar_nome": c["mostrar_nome"]}
    if t == "grade_graficos":
        return {"tipo": t, "foco": c["foco"] if c["foco"] >= 0 else None,
                "graficos": [{"titulo": g["titulo"], "conjunto": _conj(g["conjunto"]),
                              "reta": g["retas"][0] if g["retas"] else None, "curva": g["curva"],
                              "outlier": g["outliers"][0] if g["outliers"] else None} for g in c["graficos"]]}
    if t == "tabela":
        return {"tipo": t, "colunas": c["colunas"], "linhas": c["linhas"], "unidade": c["unidade"],
                "unidades": c.get("unidades", []),
                "vencedor": None if c["vencedor"] == "nenhum" else c["vencedor"],
                "coluna_total": c["coluna_total"]["usar"]}
    if t == "diagrama_causal":
        return {"tipo": t, "subtitulo": c["subtitulo"], "layout": c.get("layout", "auto"),
                "nos": [_limpo(n) for n in c["nos"]],
                "setas": [{"de": s["de"], "para": s["para"], "tracejada": s["tracejada"],
                           "rotulo": s["rotulo"] or None} for s in c["setas"]]}
    if t == "lugar":
        return {"tipo": t, "lugar": c["lugar"], "marco": c.get("marco") or None, "legenda": c["legenda"],
                "lat": c["lat"], "lon": c["lon"]}
    if t == "mapa":
        return {"tipo": t, "lugar": c["lugar"], "legenda": c["legenda"], "lat": c["lat"], "lon": c["lon"]}
    if t == "texto_grande":
        return {"tipo": t, "texto": c["texto"], "estilo": c["estilo"], "subtitulo": c["subtitulo"],
                "objeto": c.get("objeto") or None}
    if t in ("linha", "pizza", "ranking"):
        d = dict(c)
        d["destaque"] = c.get("destaque") or None
        for chave in ("series", "fatias", "itens"):
            if chave in d:
                d[chave] = [_limpo(x) | ({"valor": x["valor"]} if "valor" in x else {}) |
                            ({"valores": x["valores"]} if "valores" in x else {}) for x in d[chave]]
        return d
    if t == "distribuicao":
        return dict(c) | {"linhas": [_limpo(l) | {"x": l["x"]} for l in c["linhas"]]}
    if t == "icones":
        return dict(c) | {"cor": c.get("cor") or None}
    if t == "numero_grande":
        return dict(c) | {"objeto": c.get("objeto") or None}
    if t == "comparacao":
        lado = lambda x: {"titulo": x["titulo"], "texto": x["texto"], "objeto": x.get("objeto") or None}  # noqa: E731
        return {"tipo": t, "estilo": c["estilo"], "esquerda": lado(c["esquerda"]), "direita": lado(c["direita"]),
                "vencedor": c.get("vencedor") or None}
    if t == "desenho":
        return dict(c)
    if t in ("histograma", "simulacao", "objeto", "linha_do_tempo", "passos", "citacao", "mapa_calor", "funil"):
        d = dict(c)
        if t == "funil":
            d["etapas"] = [_limpo(e) | {"valor": e["valor"]} for e in c["etapas"]]
        return d
    if t in ("medidor", "bolhas", "inclinacao", "escala", "arvore"):
        d = dict(c)
        if "cor" in d:
            d["cor"] = d["cor"] or None
        if "destaque" in d and isinstance(d["destaque"], str):
            d["destaque"] = d["destaque"] or None
        lim = lambda x: _limpo(x) | {k: x[k] for k in ("valor", "antes", "depois") if k in x}  # noqa: E731
        for chave in ("itens", "marcadores"):
            if chave in d:
                d[chave] = [lim(x) for x in d[chave]]
        if t == "arvore":
            d["ramos"] = [lim(r) | {"filhos": [lim(f) for f in r["filhos"]]} for r in c["ramos"]]
        return d
    if t == "chamada":
        return {"tipo": t, **({"texto": c["texto"]} if c.get("texto") else {})}
    return dict(c)   # pessoa


def para_motor(r: dict) -> tuple[dict, str]:
    """Converte a saída do Claude para o formato do motor. Devolve (roteiro, notas_para_revisao)."""
    pessoas = []
    for p in r.get("pessoas", []):
        pessoas.append({
            "nome": p["nome"], "datas": p["datas"], "descricao": p["descricao"], "feito": p["feito"],
            "genero": None if p["genero"] == "desconhecido" else p["genero"],
            "cor_pele": None if p["cor_pele"] == "desconhecida" else p["cor_pele"],
            "idade_na_epoca": p["idade_na_epoca"] or None,
            "fonte_id": p["fonte_id"] or None,
        })
    roteiro = {
        "tema": r["tema"], "titulo_capa": r["titulo_capa"], "legenda": r["legenda"],
        "hashtags": r["hashtags"],
        "trechos": [{"fala": t["fala"], "titulo_tela": t["titulo_tela"][:3], "cena": _cena(t["cena"]),
                     "fonte_id": t["fonte_id"] or None, "ilustracao": t.get("ilustracao") or None,
                     "enfase": bool(t.get("enfase")), "legenda": t.get("legenda") or ""}
                    for t in r["trechos"]],
        "fontes": r["fontes"],
        "pessoas": pessoas,
    }
    return roteiro, r.get("notas_para_revisao", "")
