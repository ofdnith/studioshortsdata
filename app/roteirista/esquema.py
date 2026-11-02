"""Schema do roteiro para o Claude (ferramenta strict `entregar_roteiro`) e conversão para o motor.

A saída estruturada tem limites (24 campos opcionais, 16 uniões por schema). Por isso este
schema é diferente do `motor.roteiro`: todos os campos são obrigatórios e "ausente" é um valor
vazio ("", [], -1, 0, "nenhum"/"desconhecido"). `para_motor()` converte para o formato do motor.
"""

from motor.cenas.pontos import _embutidos
from motor.ilustracoes.lugares import LUGARES

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
              "unidade": _s(), "vencedor": _e(["maior", "menor", "nenhum"]),
              "coluna_total": _obj({"usar": BOOL}, "última coluna é o total")}),
        _obj({"tipo": _tipo("diagrama_causal"),
              "nos": _arr(_obj({"id": _s(), "rotulo": _s("curto"), "cor": COR}), "2 a 4 nós"),
              "setas": _arr(_obj({"de": _s(), "para": _s(), "tracejada": BOOL, "rotulo": _s()})),
              "subtitulo": _s()}),
        _obj({"tipo": _tipo("pessoa"), "pessoa": _s("nome exatamente como em 'pessoas'")}),
        _obj({"tipo": _tipo("lugar"), "lugar": _e(sorted(LUGARES)), "legenda": _s(), "lat": NUM, "lon": NUM}),
        _obj({"tipo": _tipo("mapa"), "lugar": _s("nome do lugar"), "lat": NUM, "lon": NUM, "legenda": _s()}),
        _obj({"tipo": _tipo("texto_grande"), "texto": _s("frase com *destaques*"),
              "estilo": _e(["frase", "carimbo"]), "subtitulo": _s()}),
        _obj({"tipo": _tipo("chamada"), "texto": _s("normalmente: Siga para mais curiosidades de dados")}),
    ]


def schema_roteiro() -> dict:
    trecho = _obj({
        "fala": _s("texto narrado, números por extenso, nomes estrangeiros como se pronunciam"),
        "titulo_tela": _arr(_s("até ~22 caracteres; palavras-chave com *asteriscos*"), "1 ou 2 linhas (0 só na chamada)"),
        "cena": {"anyOf": _cenas()},
        "fonte_id": _s("id em 'fontes', ou \"\" se o trecho não cita fato"),
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
                "vencedor": None if c["vencedor"] == "nenhum" else c["vencedor"],
                "coluna_total": c["coluna_total"]["usar"]}
    if t == "diagrama_causal":
        return {"tipo": t, "subtitulo": c["subtitulo"], "nos": [_limpo(n) for n in c["nos"]],
                "setas": [{"de": s["de"], "para": s["para"], "tracejada": s["tracejada"],
                           "rotulo": s["rotulo"] or None} for s in c["setas"]]}
    if t in ("lugar", "mapa"):
        return {"tipo": t, "lugar": c["lugar"], "legenda": c["legenda"], "lat": c["lat"], "lon": c["lon"]}
    if t == "texto_grande":
        return {"tipo": t, "texto": c["texto"], "estilo": c["estilo"], "subtitulo": c["subtitulo"]}
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
                     "fonte_id": t["fonte_id"] or None} for t in r["trechos"]],
        "fontes": r["fontes"],
        "pessoas": pessoas,
    }
    return roteiro, r.get("notas_para_revisao", "")
