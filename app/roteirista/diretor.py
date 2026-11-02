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
MAX_IMAGENS = 8   # revisão visual: quadros com problema primeiro, depois amostra

FERRAMENTA = {
    "name": "entregar_codigo",
    "description": "Entrega o código Python da animação (def quadro(c, t, v)).",
    "input_schema": {"type": "object", "additionalProperties": False, "required": ["codigo", "notas"],
                     "properties": {"codigo": {"type": "string"},
                                    "notas": {"type": "string", "description": "o que você desenhou, em 2 frases"}}},
}

FERRAMENTA_EDICAO = {
    "name": "entregar_codigo",
    "description": "Entrega AJUSTES no código atual: trocas exatas (procurar → substituir). Use codigo_completo só "
                   "se precisar reescrever quase tudo.",
    "input_schema": {"type": "object", "additionalProperties": False,
                     "required": ["edicoes", "codigo_completo", "notas"],
                     "properties": {
                         "edicoes": {"type": "array", "items": {
                             "type": "object", "additionalProperties": False, "required": ["procurar", "substituir"],
                             "properties": {"procurar": {"type": "string", "description": "trecho EXATO do código atual "
                                                                                          "(copie literalmente; curto, mas único)"},
                                            "substituir": {"type": "string"}}}},
                         "codigo_completo": {"type": "string", "description": "\"\" quando usar edicoes"},
                         "notas": {"type": "string"}}},
}
CACHE_OPENAI = {"prompt_cache_options": {"ttl": "12h"}}


def aplicar_edicoes(codigo: str, edicoes: list[dict]) -> tuple[str, list[str]]:
    """Aplica as trocas na ordem; devolve (código novo, trechos 'procurar' que não foram encontrados)."""
    falhas = []
    for e in edicoes:
        alvo = e.get("procurar", "")
        if alvo and alvo in codigo:
            codigo = codigo.replace(alvo, e.get("substituir", ""), 1)
        else:
            falhas.append(alvo[:80])
    return codigo, falhas


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

# Layout e proporções (o que mais importa depois da história)
- Tela 1080×1920. Faixas: y 250–560 títulos dos trechos (o motor desenha) · y 580–1350 SUA área · y 1370–1490 legenda da fala (o motor desenha) · y≈1518 fonte · abaixo de 1550 fica a interface do app. NADA seu abaixo de y=1350.
- Mais liberdade: se quiser usar a tela inteira (título em outro lugar, cena maior), defina `TITULOS_PELO_CODIGO = True` no módulo e desenhe você os títulos — `titulo(c, t, v, i, topo=..., tamanho=...)` desenha o título do trecho i no estilo do canal, onde você quiser. Aí sua área vai de y=250 a 1350.
- Pense em CAIXAS, não em coordenadas soltas. Caixa = (x, y, w, h). Comece de `AREA_SEM_TITULO` (x 60, y 580, w 960, h 770) ou `AREA` (y 250–1350) e divida: `dividir(caixa, [2, 1], "v")` (empilha com pesos), `dividir(caixa, 3, "h")` (lado a lado), `grade(caixa, colunas, linhas)`, `margem(caixa, 20)`, `centro(caixa)`.
- Encaixe automático (mantém proporção, nunca vaza): `svg_em(c, svg, caixa, alpha)`, `objeto_em(c, nome, caixa, alpha, lt)`, `marco_em(c, nome, caixa, lt)` (recorta dentro da caixa), `texto_em(c, "texto *destaque*", caixa, cor, alpha, peso, alinhar, tamanho_max)` (escolhe o maior tamanho que cabe e quebra linhas). `encaixar(w, h, caixa)` → (x, y, escala) para encaixar seus próprios desenhos; `medir(texto, tamanho, peso)` e `caber(texto, largura, tamanho_max, peso)` para texto.
- A cena deve OCUPAR a área: o elemento principal grande (pelo menos ~70% da largura e da altura da área), centralizado. Nada de desenho pequeno no meio de um vazio, nem sobra grande embaixo.
- Nada se sobrepõe a não ser de propósito (um ponto sobre o gráfico); nada encosta nas bordas (margem ≥ 40 px); textos nunca uns sobre os outros.

# Texto (regra do canal)
Texto na tela só em: título do trecho, informações de GRÁFICO (eixos, valores, nomes de séries, pílula "dados ilustrativos") — e a legenda e a fonte, que o motor desenha. NUNCA escreva rótulos dentro de ilustrações (nada de "SORVETE", "Vendas", "Parece uma ligação..."): a ilustração fala por si e a legenda já diz as palavras. Texto de gráfico com tamanho ≥ 30 px; números de destaque 80–200 px.

# Estilo
- Flat, cores da identidade, fundo escuro, formas grandes e reconhecíveis.
- O quadro t=0 vira a capa: já precisa ter um visual bonito (use vis com t0 negativo no primeiro elemento).
- Algo sempre se movendo (um balanço, um pulso, um gráfico crescendo) — mas sem pressa: cada elemento fica na tela o suficiente para ser lido.
- Gráficos desenhados à mão quando a fala fala de números (barras que crescem, pontos, linhas) — os números do roteiro são os que valem. Gráfico com números de exemplo leva a pílula "dados ilustrativos". Gráfico grande: use quase toda a largura da área.
- O último trecho é o fechamento: use `chamada(c, alpha, t - v.S(último))`.

# Exemplo (viés de sobrevivência) — siga o nível de cuidado e de coreografia; nos rótulos de ilustração ele é antigo: NÃO coloque texto em ilustrações
Falas: {json.dumps([t["fala"] for t in EXEMPLO["trechos"]], ensure_ascii=False)}
```python
{EXEMPLO["codigo"].strip()}
```
Entregue SEMPRE chamando a ferramenta `entregar_codigo`.
"""


def mensagem(roteiro: dict, instrucao: str = "", codigo_atual: str = "", erro: str = "") -> str:
    trechos = []
    for i, t in enumerate(roteiro["trechos"]):
        item = {"i": i, "fala": t["fala"], "titulo_tela": t.get("titulo_tela", [])}
        if t.get("ideia_visual"):
            item["ideia_visual"] = t["ideia_visual"]
        elif t.get("cena", {}).get("tipo") not in (None, "livre"):
            item["sugestao_de_cena"] = t["cena"]
        if t.get("enfase"):
            item["enfase"] = True
        trechos.append(item)
    partes = [f"Tema: {roteiro.get('tema')}",
              "Roteiro (a ideia visual é só inspiração — você é livre para desenhar melhor):",
              json.dumps(trechos, ensure_ascii=False, separators=(",", ":"))]
    if roteiro.get("pessoas"):
        partes.append("Pessoas citadas (para caricatura): " + json.dumps(roteiro["pessoas"], ensure_ascii=False,
                                                                           separators=(",", ":")))
    if codigo_atual:
        partes.append(f"Código atual da animação:\n```python\n{codigo_atual}\n```")
    if instrucao:
        partes.append(f"Pedido do editor: {instrucao}")
    if erro:
        partes.append(f"O código anterior falhou: {erro}\nCorrija e entregue o código completo.")
    partes.append("Escreva a animação completa e entregue com entregar_codigo.")
    return "\n\n".join(partes)


def _chamar(msg: str, escolha, preco, uso: Uso, log, imagens: list[bytes] | None = None,
            ferramenta: dict = FERRAMENTA, esforco: str | None = None) -> dict:
    import base64
    imagens = imagens or []
    esforco = esforco or escolha.esforco
    if escolha.provedor == "openai":
        from openai import OpenAI
        cli = OpenAI(timeout=900, max_retries=2)
        entrada = msg if not imagens else [{"role": "user", "content": [{"type": "input_text", "text": msg}] + [
            {"type": "input_image", "image_url": "data:image/jpeg;base64," + base64.b64encode(b).decode(),
             "detail": "low"} for b in imagens]}]
        resp = cli.responses.create(
            model=escolha.modelo, instructions=SISTEMA, input=entrada, reasoning={"effort": esforco},
            tools=[{"type": "function", "name": ferramenta["name"], "description": ferramenta["description"],
                    "parameters": ferramenta["input_schema"], "strict": True}],
            tool_choice={"type": "function", "name": ferramenta["name"]}, max_output_tokens=64000, **CACHE_OPENAI)
        u = resp.usage
        cache = getattr(getattr(u, "input_tokens_details", None), "cached_tokens", 0) or 0
        uso.entrada += (u.input_tokens or 0) - cache
        uso.cache_leitura += cache
        uso.saida += u.output_tokens or 0
        uso.chamadas += 1
        for item in resp.output or []:
            if item.type == "function_call" and item.name == ferramenta["name"]:
                return json.loads(item.arguments)
        raise ErroRoteiro("O diretor não entregou o código.")
    import anthropic
    cli = anthropic.Anthropic(timeout=900, max_retries=2)
    with cli.messages.stream(model=escolha.modelo, max_tokens=64000,
                             system=[{"type": "text", "text": SISTEMA, "cache_control": {"type": "ephemeral"}}],
                             tools=[ferramenta | {"strict": True}], output_config={"effort": esforco},
                             messages=[{"role": "user", "content": [{"type": "text", "text": msg}] + [
                                 {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                                              "data": base64.b64encode(b).decode()}}
                                 for b in imagens]}]) as st:
        m = st.get_final_message()
    uso.somar(m.usage)
    for b in m.content:
        if b.type == "tool_use" and b.name == ferramenta["name"]:
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


def medir_no_sandbox(roteiro: dict, codigo: str) -> tuple[list[dict], list[bytes]]:
    """Quadros (um por trecho) + problemas de proporção medidos, rodando na caixa de areia."""
    from motor.sandbox import rodar

    pasta = Path(tempfile.mkdtemp(prefix="medir_"))
    arq = pasta / "roteiro.json"
    arq.write_text(json.dumps(roteiro | {"codigo": codigo}, ensure_ascii=False), encoding="utf-8")
    _, saida = rodar(["medir", str(arq), "--pasta", str(pasta)], [pasta], timeout=300)
    for linha in saida.splitlines():
        if linha.startswith("RESULTADO "):
            r = json.loads(linha[len("RESULTADO "):])
            imgs = [(pasta / t["img"]).read_bytes() for t in r["trechos"] if (pasta / t["img"]).exists()]
            return r["trechos"], imgs
    return [], []


def _escolher_quadros(trechos: list[dict], imgs: list[bytes]) -> tuple[list[int], list[bytes]]:
    com_problema = [k for k, t in enumerate(trechos) if t["problemas"]]
    resto = [k for k in range(len(trechos)) if k not in com_problema]
    vagas = max(0, MAX_IMAGENS - len(com_problema))
    passo = max(1, len(resto) // max(1, vagas)) if vagas else len(resto) + 1
    escolhidos = sorted((com_problema[:MAX_IMAGENS] + resto[::passo][:vagas]))
    return escolhidos, [imgs[k] for k in escolhidos if k < len(imgs)]


def _resposta_em_codigo(r: dict, codigo: str) -> tuple[str, str]:
    """Resposta da ferramenta de edição -> (código novo, erro de aplicação ou '')."""
    if r.get("codigo_completo", "").strip():
        return r["codigo_completo"], ""
    novo, falhas = aplicar_edicoes(codigo, r.get("edicoes", []))
    if falhas:
        return novo, "estes trechos 'procurar' não existem no código atual: " + " | ".join(falhas[:3])
    return novo, ""


def revisao_visual(roteiro: dict, codigo: str, escolha, preco, uso: Uso, log) -> tuple[str, str]:
    """A IA vê os próprios quadros + os problemas medidos e ajusta as proporções. Devolve (código, notas)."""
    trechos, imgs = medir_no_sandbox(roteiro, codigo)
    if not imgs:
        return codigo, ""
    escolhidos, imgs_env = _escolher_quadros(trechos, imgs)
    probs = [f"trecho {t['i']}: " + "; ".join(t["problemas"]) for t in trechos if t["problemas"]]
    log(f"revisão visual: {len(imgs_env)} quadros, {len(probs)} trecho(s) com problema de proporção")
    msg = mensagem(roteiro, codigo_atual=codigo) + (
        f"\n\nREVISÃO VISUAL. As imagens anexadas são os quadros do fim dos trechos {escolhidos} (nesta ordem), "
        "em tamanho reduzido. Olhe como um diretor de arte: proporções, espaço ocupado, sobreposições, coisas "
        "pequenas demais, vazias ou cortadas, texto dentro de ilustração (não pode), algo que não ficou claro. "
        "Problemas medidos automaticamente:\n" + ("\n".join(probs) if probs else "(nenhum)") +
        "\n\nCorrija com EDIÇÕES pequenas (procurar → substituir) no código atual.")
    r = _chamar(msg, escolha, preco, uso, log, imagens=imgs_env, ferramenta=FERRAMENTA_EDICAO, esforco="low")
    novo, erro = _resposta_em_codigo(r, codigo)
    if erro:
        log(f"revisão: {erro[:150]}")
    return novo, r.get("notas", "")


def gerar_codigo(roteiro: dict, escolha, preco, log=print, instrucao: str = "", codigo_atual: str = "",
                 revisar: bool = True) -> tuple[str, Uso, str]:
    """Devolve (código aprovado nos testes, uso, notas). Levanta ErroRoteiro se não conseguir."""
    env = "OPENAI_API_KEY" if escolha.provedor == "openai" else "ANTHROPIC_API_KEY"
    if not os.environ.get(env):
        raise ErroRoteiro(f"{env} não configurada.")
    uso = Uso(modelo=escolha.modelo, preco=preco)
    erro, codigo = "", codigo_atual
    for tentativa in range(1, TENTATIVAS + 1):
        log(f"diretor de arte: {'ajustando' if codigo else 'escrevendo'} a animação (tentativa {tentativa})…")
        if codigo:   # já existe código (correção ou erro anterior): pede só as trocas
            r = _chamar(mensagem(roteiro, instrucao, codigo, erro), escolha, preco, uso, log,
                        ferramenta=FERRAMENTA_EDICAO)
            codigo, erro_aplicar = _resposta_em_codigo(r, codigo)
        else:
            r = _chamar(mensagem(roteiro, instrucao, "", erro), escolha, preco, uso, log)
            codigo, erro_aplicar = r["codigo"], ""
        erro = erro_aplicar or testar_no_sandbox(roteiro, codigo)
        if erro is None or erro == "":
            notas = r.get("notas", "")
            if revisar:
                try:
                    novo, notas_rev = revisao_visual(roteiro, codigo, escolha, preco, uso, log)
                    erro_rev = testar_no_sandbox(roteiro, novo) if novo != codigo else None
                    if erro_rev is None:
                        if novo != codigo:
                            codigo, notas = novo, notas_rev or notas
                            log("revisão visual aplicada")
                    else:
                        log(f"a revisão visual quebrou o código ({erro_rev[:120]}); mantendo a versão anterior")
                except Exception as e:
                    log(f"revisão visual não rodou: {e}")
            log(f"animação pronta e testada · US$ {uso.custo:.2f}")
            return codigo, uso, notas
        log(f"o código falhou no teste: {erro[:200]}")
    raise ErroRoteiro(f"O diretor não conseguiu um código que passe nos testes: {erro[:300]}")
