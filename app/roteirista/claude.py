"""Chamada à API do Claude: pesquisa (web search + web fetch) e entrega estruturada do roteiro."""

import os
from dataclasses import dataclass, field

import anthropic

from app.roteirista.esquema import FERRAMENTA
from app.roteirista.prompt import SISTEMA

MODELO_PADRAO = "claude-fable-5-1"
BETA_FALLBACK = "server-side-fallback-2026-07-01"

# US$ por milhão de tokens (Claude Fable 5.1) e por busca. Ajuste aqui se os preços mudarem.
PRECOS = {
    "claude-fable-5-1": {"entrada": 10.0, "saida": 50.0, "cache_escrita": 12.5, "cache_leitura": 0.25},
}
PRECO_BUSCA = 10.0 / 1000

FERRAMENTAS = [
    {"type": "web_search_20260318", "name": "web_search", "max_uses": 12},
    {"type": "web_fetch_20260318", "name": "web_fetch", "max_uses": 15, "max_content_tokens": 30000},
    FERRAMENTA,
]
MAX_RETOMADAS = 6


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
        p = PRECOS.get(self.modelo, PRECOS[MODELO_PADRAO])
        return round((self.entrada * p["entrada"] + self.saida * p["saida"]
                      + self.cache_escrita * p["cache_escrita"] + self.cache_leitura * p["cache_leitura"]) / 1e6
                     + self.buscas * PRECO_BUSCA, 4)


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


def gerar(mensagem: str, log=print, client=None) -> Resultado:
    """Roda a conversa até o Claude chamar `entregar_roteiro`. Trata pause_turn."""
    client = client or cliente()
    m = modelo()
    uso = Uso(modelo=m)
    urls, buscas = [], []
    mensagens = [{"role": "user", "content": mensagem}]
    pedidos_de_entrega = 0
    for _ in range(MAX_RETOMADAS):
        with client.beta.messages.stream(
            model=m,
            max_tokens=64000,
            betas=[BETA_FALLBACK],
            fallbacks="default",
            system=[{"type": "text", "text": SISTEMA, "cache_control": {"type": "ephemeral"}}],
            tools=FERRAMENTAS,
            output_config={"effort": "high"},
            messages=mensagens,
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
