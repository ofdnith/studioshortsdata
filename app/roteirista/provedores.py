"""Provedores de IA (Anthropic e OpenAI), modelos, preços e escolha do modelo.

Preços em US$ por milhão de tokens, conferidos nas páginas oficiais em 2026-11-02.
Ajuste aqui se mudarem (ou sobrescreva pela tela IA, que guarda no banco).
"""

import json
from dataclasses import asdict, dataclass

PRECO_BUSCA = 10.0 / 1000   # US$ por busca na web (os dois provedores)


@dataclass
class Modelo:
    id: str
    nome: str
    provedor: str
    entrada: float
    saida: float
    cache_leitura: float
    cache_escrita: float
    nota: str = ""
    recomendado: bool = False


PROVEDORES = {
    "anthropic": {
        "nome": "Anthropic (Claude)",
        "env": "ANTHROPIC_API_KEY",
        "console": "https://platform.claude.com/settings/keys",
        "cobranca": "https://platform.claude.com/settings/billing",
        "ferramentas": "web search + web fetch (abre as páginas das fontes)",
    },
    "openai": {
        "nome": "OpenAI (GPT)",
        "env": "OPENAI_API_KEY",
        "console": "https://platform.openai.com/api-keys",
        "cobranca": "https://platform.openai.com/settings/organization/billing",
        "ferramentas": "web search (busca e abre páginas)",
    },
}

MODELOS = [
    Modelo("claude-fable-5-1", "Claude Fable 5.1", "anthropic", 10.0, 50.0, 0.25, 12.5,
           "o mais capaz para pesquisa e checagem de fatos", recomendado=True),
    Modelo("claude-opus-5-5", "Claude Opus 5.5", "anthropic", 4.0, 20.0, 0.20, 5.0,
           "muito capaz, menos da metade do preço do Fable"),
    Modelo("claude-sonnet-5-5", "Claude Sonnet 5.5", "anthropic", 2.0, 10.0, 0.20, 2.5,
           "rápido e bom custo-benefício"),
    Modelo("claude-haiku-5-5", "Claude Haiku 5.5", "anthropic", 0.10, 0.50, 0.01, 0.125,
           "o mais barato; checagem de fatos mais fraca"),
    Modelo("gpt-6-astra", "GPT-6 Astra", "openai", 10.0, 50.0, 1.0, 10.0, "o mais capaz da OpenAI"),
    Modelo("gpt-6.1-sol", "GPT-6.1 Sol", "openai", 2.0, 10.0, 0.10, 2.0, "equilíbrio entre qualidade e preço",
           recomendado=True),
    Modelo("gpt-6.1-terra", "GPT-6.1 Terra", "openai", 1.0, 5.0, 0.05, 1.0, "barato, bom para testes"),
    Modelo("gpt-6-luna", "GPT-6 Luna", "openai", 0.10, 0.50, 0.01, 0.10, "o mais barato; qualidade menor"),
    Modelo("gpt-5.5", "GPT-5.5", "openai", 5.0, 30.0, 0.50, 5.0, "recomendado pela OpenAI para pesquisa na web"),
    Modelo("gpt-5-mini", "GPT-5 mini", "openai", 0.25, 2.0, 0.025, 0.25, "geração anterior, barato"),
]
POR_ID = {m.id: m for m in MODELOS}
ESFORCOS = {"low": "Baixo (mais barato)", "medium": "Médio", "high": "Alto (melhor checagem)"}

# Uso típico de um roteiro (para estimar custo antes de gerar). Ajustado com o uso real:
# pesquisa com várias páginas abertas, prompt de sistema em cache, raciocínio + roteiro na saída.
USO_TIPICO = {"entrada": 120_000, "cache_leitura": 30_000, "saida": 18_000, "buscas": 8}

PADROES = {"ia_provedor": "anthropic", "ia_modelo": "claude-fable-5-1", "ia_esforco": "high",
           "ia_max_buscas": "10", "ia_max_paginas": "12"}


def provedor_de(modelo_id: str) -> str:
    m = POR_ID.get(modelo_id)
    if m:
        return m.provedor
    return "openai" if modelo_id.startswith(("gpt", "o")) else "anthropic"


def precos(con, modelo_id: str) -> Modelo | None:
    """Modelo com os preços, aplicando o que foi sobrescrito na tela IA."""
    base = POR_ID.get(modelo_id)
    sobre = json.loads(ajuste(con, "ia_precos", "{}")).get(modelo_id) if con is not None else None
    if base is None and not sobre:
        return None
    d = asdict(base) if base else {"id": modelo_id, "nome": modelo_id, "provedor": provedor_de(modelo_id),
                                   "entrada": 0, "saida": 0, "cache_leitura": 0, "cache_escrita": 0}
    if sobre:
        d.update({k: float(v) for k, v in sobre.items() if k in ("entrada", "saida", "cache_leitura", "cache_escrita")})
    return Modelo(**d)


def custo(m: Modelo | None, entrada=0, saida=0, cache_leitura=0, cache_escrita=0, buscas=0) -> float:
    if m is None:
        return round(buscas * PRECO_BUSCA, 4)
    return round((entrada * m.entrada + saida * m.saida + cache_leitura * m.cache_leitura
                  + cache_escrita * m.cache_escrita) / 1e6 + buscas * PRECO_BUSCA, 4)


def estimativa(m: Modelo, esforco: str = "high") -> float:
    fator = {"low": 0.6, "medium": 0.8, "high": 1.0}.get(esforco, 1.0)
    u = USO_TIPICO
    return custo(m, u["entrada"] * fator, u["saida"] * fator, u["cache_leitura"], 0, round(u["buscas"] * fator))


# ---------------------------------------------------------------- ajustes no banco

def ajuste(con, chave: str, padrao: str | None = None) -> str | None:
    r = con.execute("SELECT valor FROM ajuste WHERE chave = ?", (chave,)).fetchone()
    return r[0] if r else (PADROES.get(chave) if padrao is None else padrao)


def definir(con, chave: str, valor: str):
    con.execute("INSERT INTO ajuste (chave, valor) VALUES (?, ?) ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor",
                (chave, valor))


@dataclass
class Escolha:
    provedor: str
    modelo: str
    esforco: str
    max_buscas: int
    max_paginas: int
    origem: str     # "padrão" ou "personalizado no tema"


def escolha(con, config_tema: dict | None = None) -> Escolha:
    """Modelo usado para um vídeo: o do tema (se personalizado) ou o padrão da tela IA."""
    modelo = ajuste(con, "ia_modelo")
    origem = "padrão"
    if config_tema and config_tema.get("modelo"):
        modelo, origem = config_tema["modelo"], "personalizado no tema"
    return Escolha(provedor_de(modelo), modelo, ajuste(con, "ia_esforco"),
                   int(ajuste(con, "ia_max_buscas")), int(ajuste(con, "ia_max_paginas")), origem)


def gasto_por_modelo(con) -> dict[str, dict]:
    res = {}
    for r in con.execute("SELECT modelo, count(*) n, sum(custo_estimado) c, sum(tokens_entrada + tokens_cache_leitura"
                         " + tokens_cache_escrita) te, sum(tokens_saida) ts, sum(buscas_web) b, max(criado_em) ult"
                         " FROM roteiro WHERE custo_estimado > 0 GROUP BY modelo"):
        res[r["modelo"]] = dict(r)
    return res


def gasto_desde(con, provedor: str, data: str) -> float:
    total = 0.0
    for r in con.execute("SELECT modelo, custo_estimado FROM roteiro WHERE custo_estimado > 0 AND date(criado_em) >= ?",
                         (data,)):
        if provedor_de(r["modelo"]) == provedor:
            total += r["custo_estimado"]
    return round(total, 4)
