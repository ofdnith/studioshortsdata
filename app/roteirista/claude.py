"""Chamada à API do Claude: pesquisa (web search + web fetch) e entrega estruturada do roteiro."""

import os
from dataclasses import dataclass, field

import anthropic

from app.roteirista.esquema import FERRAMENTA, ferramenta
from app.roteirista.prompt import sistema

from app.roteirista import provedores as pv

MODELO_PADRAO = "claude-fable-5-1"
BETA_FALLBACK = "server-side-fallback-2026-07-01"
# modelos que aceitam o fallback do servidor em recusas
COM_FALLBACK = {"claude-fable-5-1", "claude-opus-5-5", "claude-sonnet-5-5"}
MAX_RETOMADAS = 6


def ferramentas(max_buscas: int = 10, max_paginas: int = 12, entrega: dict = FERRAMENTA) -> list:
    return [
        {"type": "web_search_20260318", "name": "web_search", "max_uses": max_buscas},
        {"type": "web_fetch_20260318", "name": "web_fetch", "max_uses": max_paginas, "max_content_tokens": 30000},
        entrega,
    ]


class ErroRoteiro(Exception):
    pass


@dataclass
class Uso:
    modelo: str = MODELO_PADRAO
    entrada: int = 0
    saida: int = 0
    cache_escrita: int = 0
    cache_leitura: int = 0
    buscas: int = 0
    paginas: int = 0
    chamadas: int = 0
    preco: object = None     # provedores.Modelo (preços); None = só busca

    def somar(self, u):
        self.entrada += u.input_tokens or 0
        self.saida += u.output_tokens or 0
        self.cache_escrita += getattr(u, "cache_creation_input_tokens", 0) or 0
        self.cache_leitura += getattr(u, "cache_read_input_tokens", 0) or 0
        stu = getattr(u, "server_tool_use", None)
        if stu:
            self.buscas += getattr(stu, "web_search_requests", 0) or 0
            self.paginas += getattr(stu, "web_fetch_requests", 0) or 0
        self.chamadas += 1

    @property
    def custo(self) -> float:
        preco = self.preco if self.preco is not None else pv.POR_ID.get(self.modelo)
        return pv.custo(preco, self.entrada, self.saida, self.cache_leitura, self.cache_escrita, self.buscas)

    def para_dict(self) -> dict:
        return {k: getattr(self, k) for k in ("modelo", "entrada", "saida", "cache_escrita", "cache_leitura",
                                               "buscas", "paginas", "chamadas")} | {"custo": self.custo}


@dataclass
class Resultado:
    roteiro: dict                     # saída da ferramenta (schema do Claude)
    uso: Uso
    urls_abertas: list[str] = field(default_factory=list)
    buscas: list[str] = field(default_factory=list)


def modelo() -> str:
    return os.environ.get("CLAUDE_MODEL") or MODELO_PADRAO


def cliente():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise ErroRoteiro("ANTHROPIC_API_KEY não está no .env.")
    return anthropic.Anthropic(timeout=900, max_retries=2)


def gerar(mensagem: str, log=print, client=None, escolha=None, preco=None, so_trecho: bool = False) -> Resultado:
    """Roda a conversa até o Claude chamar `entregar_roteiro`. Trata pause_turn."""
    client = client or cliente()
    m = escolha.modelo if escolha else modelo()
    esforco = escolha.esforco if escolha else "high"
    modo = escolha.modo if escolha else "catalogo"
    entrega = ferramenta(modo, so_trecho)
    tools = ferramentas(escolha.max_buscas, escolha.max_paginas, entrega) if escolha else ferramentas(entrega=entrega)
    uso = Uso(modelo=m, preco=preco)
    extra = {"betas": [BETA_FALLBACK], "fallbacks": "default"} if m in COM_FALLBACK else {}
    urls, buscas = [], []
    mensagens = [{"role": "user", "content": mensagem}]
    pedidos_de_entrega = 0
    for _ in range(MAX_RETOMADAS):
        with client.beta.messages.stream(
            model=m,
            max_tokens=64000,
            system=[{"type": "text", "text": sistema("anthropic", modo), "cache_control": {"type": "ephemeral"}}],
            tools=tools,
            output_config={"effort": esforco},
            messages=mensagens,
            **extra,
        ) as stream:
            for ev in stream:
                if ev.type == "content_block_start":
                    b = ev.content_block
                    if b.type == "web_search_tool_result":
                        log("busca na web concluída")
                    elif b.type == "web_fetch_tool_result":
                        c = getattr(b, "content", None)
                        url = getattr(c, "url", None)
                        if url:
                            log(f"abriu {url}")
                    elif b.type == "tool_use" and b.name == "entregar_roteiro":
                        log("escrevendo o roteiro…")
            msg = stream.get_final_message()
        uso.somar(msg.usage)

        entrega = None
        for b in msg.content:
            if b.type == "server_tool_use":
                entrada = b.input if isinstance(b.input, dict) else {}
                if b.name == "web_search" and entrada.get("query"):
                    buscas.append(entrada["query"])
                    log(f"buscou: {entrada['query']}")
            elif b.type == "web_fetch_tool_result":
                c = getattr(b, "content", None)
                if getattr(c, "type", "") == "web_fetch_result" and getattr(c, "url", None):
                    urls.append(c.url)
            elif b.type == "tool_use" and b.name == "entregar_roteiro":
                entrega = b.input

        if entrega is not None:
            log(f"roteiro entregue · {uso.entrada + uso.cache_leitura + uso.cache_escrita} tokens de entrada, "
                f"{uso.saida} de saída · {uso.buscas} buscas · US$ {uso.custo:.2f}")
            return Resultado(entrega, uso, urls, buscas)
        if msg.stop_reason == "pause_turn":
            log("pesquisa longa: continuando…")
            mensagens.append({"role": "assistant", "content": msg.content})
            continue
        if msg.stop_reason == "refusal":
            det = getattr(msg, "stop_details", None)
            raise ErroRoteiro(f"O modelo recusou o pedido ({getattr(det, 'category', '?')}).")
        if msg.stop_reason == "max_tokens":
            raise ErroRoteiro("A resposta passou do limite de tokens.")
        # terminou sem entregar: pede a entrega (no máximo duas vezes)
        pedidos_de_entrega += 1
        if pedidos_de_entrega > 2:
            break
        log("o modelo terminou sem entregar; pedindo a entrega pela ferramenta")
        mensagens.append({"role": "assistant", "content": msg.content})
        mensagens.append({"role": "user", "content": "Agora entregue o roteiro completo chamando a ferramenta "
                                                     "entregar_roteiro."})
    raise ErroRoteiro("O modelo não entregou o roteiro pela ferramenta.")
