"""Geração do roteiro pela OpenAI (Responses API): busca na web + função strict `entregar_roteiro`."""

import copy
import json
import os

from app.roteirista.claude import ErroRoteiro, Resultado, Uso
from app.roteirista.esquema import FERRAMENTA, ferramenta
from app.roteirista.prompt import sistema

MAX_PEDIDOS = 2


def _sem_const(sch):
    """A OpenAI não aceita `const`: troca por enum de um valor."""
    if isinstance(sch, dict):
        out = {}
        for k, v in sch.items():
            if k == "const":
                out["enum"] = [v]
            else:
                out[k] = _sem_const(v)
        return out
    if isinstance(sch, list):
        return [_sem_const(x) for x in sch]
    return sch


def schema_openai(entrega: dict = FERRAMENTA) -> dict:
    return _sem_const(copy.deepcopy(entrega["input_schema"]))


def ferramentas(entrega: dict = FERRAMENTA) -> list:
    return [
        # "low": cada busca devolve menos texto das páginas (era o que mais pesava na entrada).
        {"type": "web_search", "search_context_size": "low"},
        {"type": "function", "name": entrega["name"], "description": entrega["description"],
         "parameters": schema_openai(entrega), "strict": True},
    ]


# Cache de prompt: no GPT-5.6+ dura 30 min por padrão; 12 h aproveita o prompt fixo entre vídeos.
CACHE = {"prompt_cache_options": {"ttl": "12h"}}


def cliente():
    if not os.environ.get("OPENAI_API_KEY"):
        raise ErroRoteiro("OPENAI_API_KEY não está configurada (tela IA).")
    from openai import OpenAI
    return OpenAI(timeout=900, max_retries=2)


def _somar(uso: Uso, u):
    if u is None:
        return
    cache = getattr(getattr(u, "input_tokens_details", None), "cached_tokens", 0) or 0
    uso.entrada += (u.input_tokens or 0) - cache
    uso.cache_leitura += cache
    uso.saida += u.output_tokens or 0
    uso.chamadas += 1


def gerar(mensagem: str, log=print, client=None, escolha=None, preco=None, so_trecho: bool = False) -> Resultado:
    client = client or cliente()
    m = escolha.modelo if escolha else "gpt-6.1-sol"
    esforco = escolha.esforco if escolha else "high"
    modo = escolha.modo if escolha else "catalogo"
    uso = Uso(modelo=m, preco=preco)
    urls, buscas = [], []
    tools = ferramentas(ferramenta(modo, so_trecho))

    log(f"gerando com {m} (OpenAI, esforço {esforco})")
    kwargs = dict(model=m, instructions=sistema("openai", modo), tools=tools, reasoning={"effort": esforco},
                  include=["web_search_call.action.sources"], max_output_tokens=64000,
                  max_tool_calls=escolha.max_buscas if escolha else 5, **CACHE)
    resp = client.responses.create(input=mensagem, **kwargs)
    for tentativa in range(MAX_PEDIDOS + 1):
        _somar(uso, getattr(resp, "usage", None))
        entrega = None
        for item in resp.output or []:
            if item.type == "web_search_call":
                acao = getattr(item, "action", None)
                tipo = getattr(acao, "type", "")
                if tipo == "search":
                    uso.buscas += 1
                    q = getattr(acao, "query", None)
                    if q:
                        buscas.append(q)
                        log(f"buscou: {q}")
                elif tipo == "open_page":
                    url = getattr(acao, "url", None)
                    if url:
                        urls.append(url)
                        uso.paginas += 1
                        log(f"abriu {url}")
            elif item.type == "function_call" and item.name == FERRAMENTA["name"]:
                try:
                    entrega = json.loads(item.arguments)
                except json.JSONDecodeError as e:
                    raise ErroRoteiro(f"JSON da entrega inválido: {e}") from None
        if entrega is not None:
            log(f"roteiro entregue · {uso.entrada + uso.cache_leitura} tokens de entrada, {uso.saida} de saída · "
                f"{uso.buscas} buscas · US$ {uso.custo:.2f}")
            return Resultado(entrega, uso, urls, buscas)
        if getattr(resp, "status", "") == "incomplete":
            motivo = getattr(getattr(resp, "incomplete_details", None), "reason", "?")
            raise ErroRoteiro(f"Resposta incompleta ({motivo}).")
        if tentativa == MAX_PEDIDOS:
            break
        log("o modelo terminou sem entregar; pedindo a entrega pela função")
        resp = client.responses.create(
            input="Agora entregue o roteiro completo chamando a função entregar_roteiro.",
            previous_response_id=resp.id, tool_choice={"type": "function", "name": FERRAMENTA["name"]}, **kwargs)
    raise ErroRoteiro("O modelo não entregou o roteiro pela função.")
