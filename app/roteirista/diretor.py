"""Diretor de arte: a IA escreve o código da animação (modo livre), SEM acesso à web.

Recebe o roteiro já pesquisado (falas, títulos, sugestões de cena, pessoas) e devolve
`def quadro(c, t, v)`. O código passa pela análise estática e por um teste rápido dentro da
caixa de areia; se falhar, o erro volta para a IA corrigir (até 3 tentativas).
"""

import json
import os
import tempfile
from pathlib import Path

from app.roteirista.claude import ErroRoteiro, Uso
from motor.ilustracoes.marcos import MARCOS
from motor.ilustracoes.objetos import OBJETOS

RAIZ = Path(__file__).resolve().parent.parent.parent
EXEMPLO = json.loads((RAIZ / "exemplos" / "livre_sobrevivencia.json").read_text(encoding="utf-8"))
TENTATIVAS = 3

FERRAMENTA = {
    "name": "entregar_codigo",
    "description": "Entrega o código Python da animação (def quadro(c, t, v)).",
    "input_schema": {"type": "object", "additionalProperties": False, "required": ["codigo", "notas"],
                     "properties": {"codigo": {"type": "string"},
                                    "notas": {"type": "string", "description": "o que você desenhou, em 2 frases"}}},
}

SISTEMA = f"""Você é o diretor de arte e animador de um canal de vídeos curtos (Reels/TikTok, 1080×1920, 30 fps) de curiosidades de ciência de dados, para leigos. Você recebe um roteiro já escrito e checado e escreve, em Python, o código que desenha CADA QUADRO do vídeo — como um motion designer. Liberdade total de criação: desenhe o que a história pede (o avião com buracos, o dinossauro, a fila do banco, o bilionário no bar), invente gráficos sob medida, coreografe tudo com a fala.

# Contrato
Escreva `def quadro(c, t, v):` que desenha o instante `t` (segundos) no canvas skia `c`. O fundo (azul-escuro com pontinhos), os títulos de cada trecho (`titulo_tela`), a linha de fonte no rodapé e a narração já são feitos pelo motor. Você desenha o resto.
- Sem `import` (tudo abaixo já está disponível), sem nomes começando com `_`, sem `while`, sem classes, sem `open`/`exec`/`eval`/`getattr`. O código roda numa caixa de areia; qualquer coisa fora disso é recusada.
- Pode definir funções auxiliares e constantes no nível do módulo. Precisa ser rápido: cada quadro é chamado ~2.000 vezes (nada de laços enormes por quadro).

# Tempos da fala (o coração da coreografia)
`v.S(i)` início do trecho i (0 = primeiro) · `v.E(i)` fim da fala dele · `v.prox(i)` início do próximo · `v.total` duração · `v.n` número de trechos · `v.palavra(i, "texto")` instante em que a voz diz aquela palavra no trecho i · `v.trecho_em(t)` qual trecho está sendo falado · `v.fala(i)` o texto.
Regra de ouro: o que a fala cita aparece NA HORA em que é dito (use v.palavra). Tudo entra e sai suavemente.

# Ferramentas disponíveis
- skia (canvas `c`: drawCircle, drawRRect, drawPath, drawLine, drawOval, save/restore, translate, rotate, scale, clipRect; skia.Path, skia.Rect, skia.RRect, skia.Paint), math, np (numpy), random (já semeado).
- Cores (tuplas RGB): FUNDO, BRANCO, CINZA, AMARELO (destaque), VERMELHO, VERDE, CIANO, ROXO, PAINEL, PAINEL_LN, GRADE; `hx("FF8FB1")` cria outra; `misturar(c1, c2, k)`.
- `paint(cor, alpha=1, stroke=None, blur=None)` → skia.Paint.
- Animação: `vis(t, t0, t1, fin=0.22, fout=0.2)` → (alpha, entrada 0..1) para algo que aparece em t0 e some em t1 (None = fica); `ease_out(x)`, `ease_io(x)`, `back_out(x)` (efeito pop), `clamp(x, a, b)`. Ex.: `a, e = vis(t, v.S(2), v.prox(3))`.
- Texto: `texto(c, s, x, y, tamanho, cor, alpha, peso, align, maxw)` (y = linha de base; peso: "Regular", "Medium", "SemiBold", "Bold", "ExtraBold", "Black"; align: "left", "center", "right"); `linhas(c, ["linha com *destaque*"], topo, tamanho, peso=, cor_=, destaque=, alpha=, x=, align=, maxw=)`; `quebrar(texto, tamanho, peso, largura_max)` → lista de linhas; `fmt_num(v, casas)`, `com_unidade(v, "R$")`.
- Formas prontas: `barra(c, x, y, w, h, cor, alpha, r)`, `painel(c, x, y, w, h, alpha)`, `pilula(c, texto, cx, cy, tamanho, cor_fundo, cor_texto, alpha, peso=)`, `check(c, x, y, r, alpha)`, `seta(c, x0, y0, x1, y1, cor, alpha, k=progresso 0..1, tracejada=False, w=6)`, `seta_curva(c, x0, y0, cx, cy, x1, y1, cor, alpha, k)`.
- Ilustrações: `objeto(c, nome, cx, cy, tamanho_px, alpha, lt)` com nome em: {", ".join(sorted(OBJETOS))}; `svg(c, "<svg viewBox='0 0 100 100'>…</svg>", cx, cy, largura, alpha)` para desenhar qualquer coisa em SVG; `retrato(c, cx, cy, raio, alpha, lt, None)` (silhueta de pessoa) ou `caricatura(c, cx, cy, alpha, lt, cor_pele, idade, genero)`; `marco(c, nome, X, Y, largura, altura, lt)` com lugares: {", ".join(sorted(MARCOS))}; `chamada(c, alpha, lt)` desenha o fechamento padrão do canal.
- Constantes: W=1080, H=1920.

# Layout e estilo
- Área sua: y de 580 a 1480 (acima ficam os títulos; em y≈1518 a fonte). Não ponha nada importante no canto inferior direito (x>940, y>1150): ícones do app.
- Estilo flat, cores da identidade, fundo escuro. Texto na tela grande e curto (≥ 30 px; números de destaque 80–200 px). Nada de parágrafos na tela.
- O quadro t=0 vira a capa: já precisa ter um visual bonito (use vis com t0 negativo no primeiro elemento).
- Algo sempre se movendo (um balanço, um pulso, um gráfico crescendo) — mas sem pressa: cada elemento fica na tela o suficiente para ser lido.
- Gráficos desenhados à mão quando a fala fala de números (barras que crescem, pontos, linhas) — os números do roteiro são os que valem. Gráfico com números de exemplo leva a pílula "dados ilustrativos".
- O último trecho é o fechamento: use `chamada(c, alpha, t - v.S(último))`.

# Exemplo completo (viés de sobrevivência) — siga este nível de cuidado e coreografia
Falas: {json.dumps([t["fala"] for t in EXEMPLO["trechos"]], ensure_ascii=False)}
```python
{EXEMPLO["codigo"].strip()}
```
Entregue SEMPRE chamando a ferramenta `entregar_codigo`.
"""


def mensagem(roteiro: dict, instrucao: str = "", codigo_atual: str = "", erro: str = "") -> str:
    trechos = [{"i": i, "fala": t["fala"], "titulo_tela": t.get("titulo_tela", []),
                "sugestao_de_cena": t.get("cena", {}), "enfase": t.get("enfase", False),
                "ilustracao_sugerida": t.get("ilustracao")} for i, t in enumerate(roteiro["trechos"])]
    partes = [f"Tema: {roteiro.get('tema')}",
              "Roteiro (a sugestão de cena é só inspiração — você é livre para desenhar melhor):",
              json.dumps(trechos, ensure_ascii=False, indent=0)]
    if roteiro.get("pessoas"):
        partes.append("Pessoas citadas (para caricatura): " + json.dumps(roteiro["pessoas"], ensure_ascii=False))
    if codigo_atual:
        partes.append(f"Código atual da animação:\n```python\n{codigo_atual}\n```")
    if instrucao:
        partes.append(f"Pedido do editor: {instrucao}")
    if erro:
        partes.append(f"O código anterior falhou: {erro}\nCorrija e entregue o código completo.")
    partes.append("Escreva a animação completa e entregue com entregar_codigo.")
    return "\n\n".join(partes)


def _chamar(msg: str, escolha, preco, uso: Uso, log) -> dict:
    if escolha.provedor == "openai":
        from openai import OpenAI
        cli = OpenAI(timeout=900, max_retries=2)
        resp = cli.responses.create(
            model=escolha.modelo, instructions=SISTEMA, input=msg, reasoning={"effort": escolha.esforco},
            tools=[{"type": "function", "name": FERRAMENTA["name"], "description": FERRAMENTA["description"],
                    "parameters": FERRAMENTA["input_schema"], "strict": True}],
            tool_choice={"type": "function", "name": FERRAMENTA["name"]}, max_output_tokens=64000)
        u = resp.usage
        cache = getattr(getattr(u, "input_tokens_details", None), "cached_tokens", 0) or 0
        uso.entrada += (u.input_tokens or 0) - cache
        uso.cache_leitura += cache
        uso.saida += u.output_tokens or 0
        uso.chamadas += 1
        for item in resp.output or []:
            if item.type == "function_call" and item.name == FERRAMENTA["name"]:
                return json.loads(item.arguments)
        raise ErroRoteiro("O diretor não entregou o código.")
    import anthropic
    cli = anthropic.Anthropic(timeout=900, max_retries=2)
    with cli.messages.stream(model=escolha.modelo, max_tokens=64000,
                             system=[{"type": "text", "text": SISTEMA, "cache_control": {"type": "ephemeral"}}],
                             tools=[FERRAMENTA | {"strict": True}], output_config={"effort": escolha.esforco},
                             messages=[{"role": "user", "content": msg}]) as st:
        m = st.get_final_message()
    uso.somar(m.usage)
    for b in m.content:
        if b.type == "tool_use" and b.name == FERRAMENTA["name"]:
            return b.input
    raise ErroRoteiro("O diretor não entregou o código.")


def testar_no_sandbox(roteiro: dict, codigo: str) -> str | None:
    """Análise estática + teste rápido na caixa de areia. Devolve o erro ou None."""
    from motor.livre import validar_codigo
    from motor.sandbox import rodar

    erros = validar_codigo(codigo)
    if erros:
        return "; ".join(erros[:6])
    pasta = Path(tempfile.mkdtemp(prefix="diretor_"))
    arq = pasta / "roteiro.json"
    arq.write_text(json.dumps(roteiro | {"codigo": codigo}, ensure_ascii=False), encoding="utf-8")
    cod, saida = rodar(["testar-codigo", str(arq)], [pasta], timeout=180)
    for linha in saida.splitlines():
        if linha.startswith("RESULTADO "):
            r = json.loads(linha[len("RESULTADO "):])
            return None if r["ok"] else r["erro"]
    return f"o teste não terminou (código {cod}): {saida[-300:]}"


def gerar_codigo(roteiro: dict, escolha, preco, log=print, instrucao: str = "", codigo_atual: str = "") -> tuple[str, Uso, str]:
    """Devolve (código aprovado nos testes, uso, notas). Levanta ErroRoteiro se não conseguir."""
    env = "OPENAI_API_KEY" if escolha.provedor == "openai" else "ANTHROPIC_API_KEY"
    if not os.environ.get(env):
        raise ErroRoteiro(f"{env} não configurada.")
    uso = Uso(modelo=escolha.modelo, preco=preco)
    erro, codigo = "", codigo_atual
    for tentativa in range(1, TENTATIVAS + 1):
        log(f"diretor de arte: escrevendo a animação (tentativa {tentativa})…")
        r = _chamar(mensagem(roteiro, instrucao, codigo, erro), escolha, preco, uso, log)
        codigo = r["codigo"]
        erro = testar_no_sandbox(roteiro, codigo)
        if erro is None:
            log(f"animação pronta e testada · US$ {uso.custo:.2f}")
            return codigo, uso, r.get("notas", "")
        log(f"o código falhou no teste: {erro[:200]}")
    raise ErroRoteiro(f"O diretor não conseguiu um código que passe nos testes: {erro[:300]}")
