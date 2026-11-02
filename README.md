# Estúdio

Plataforma local para produzir e agendar vídeos curtos de curiosidades de dados.
Especificação completa em [PROMPT.md](PROMPT.md).

## Como rodar

Pré-requisitos: [uv](https://docs.astral.sh/uv/) e FFmpeg (`brew install uv ffmpeg`).

```sh
make instalar   # cria o .venv com Python 3.12 e instala as dependências
./scripts/baixar_modelos.sh   # modelos de voz do Kokoro (~340 MB) em models/
make dev        # sobe o servidor (http://localhost:8000) e o worker
```

Em `make dev`, qualquer mudança em `app/` (.py, .html, .css, .js) reinicia o servidor e a
página aberta no navegador recarrega sozinha.

## IA dos roteiros

Na aba **IA** do app: cole a chave da Anthropic e/ou da OpenAI (fica só no `.env`, fora do
Git), teste a conexão (lista os modelos, não consome crédito), registre o saldo de crédito e
escolha o modelo padrão. Cada vídeo pode usar outro modelo em **Personalização do vídeo**.
O custo estimado de cada roteiro fica registrado no vídeo.

## Modo livre (padrão)

A IA escreve a animação inteira de cada vídeo, sob medida, como nos vídeos feitos no chat:
desenha o que a história cita e sincroniza tudo com a fala (`v.palavra(i, "avião")`). O fluxo:
pesquisa (com web) → roteiro → **diretor de arte** (sem web) escreve `def quadro(c, t, v)` →
análise estática (sem import, arquivos, rede, introspecção) → teste rápido → render.
O código da IA sempre roda **na caixa de areia do macOS** (`motor/sandbox.py`): sem rede e sem
escrita fora da pasta do vídeo. Na revisão dá para ler e editar o código, ou pedir
"Só a animação" como correção. Na aba IA dá para voltar ao modo catálogo.
Exemplo escrito à mão: `exemplos/livre_sobrevivencia.json`.

## Agenda e contas

- **Agenda:** painel (agendados, publicados, rascunhos do TikTok com tempo para expirar, erros),
  próximos 7 dias, "Preencher a semana" (com desfazer), horários por dia (horário de Brasília) e a
  biblioteca. Cada vídeo tem um editor de legendas (base + variação por plataforma, contadores) e
  ações de agendar / publicar agora.
- **Modo simulação** (padrão): o worker executa os horários vencidos mas não envia nada. A
  publicação real só liga digitando PUBLICAR na Agenda.
- **Contas:** passo a passo do app na Meta, credenciais no `.env`, conexão OAuth colando a URL de
  retorno, validade e renovação automática do token. Para publicar, o Instagram baixa o vídeo de
  uma URL pública: o app abre um túnel temporário do `cloudflared` só para aquele arquivo.
- `/termos` e `/privacidade`: páginas públicas exigidas na revisão dos apps.

## Motor de renderização

```sh
uv run python -m motor validar exemplos/paradoxo_simpson.json
uv run python -m motor previa  exemplos/paradoxo_simpson.json 0 12.5 40 --pasta storage/previa
uv run python -m motor render  exemplos/paradoxo_simpson.json --saida storage/exemplos/paradoxo_simpson.mp4 \
    [--voz pm_alex|pm_santa|pf_dora] [--velocidade 1.2]
uv run python -m motor amostra --voz pf_dora --saida storage/amostra.mp3
```

O render gera o MP4 (1080x1920, 30 fps, H.264 + AAC, ~-15 LUFS), a capa (primeiro quadro),
4 prévias em PNG e uma pasta `<nome>_trabalho/` com a narração, o cronograma e os parâmetros.
Os áudios de cada trecho ficam em cache (`storage/cache_voz/`): editar um trecho só regenera
aquela fala.

- `motor/roteiro.py`: formato do roteiro e parâmetros de cada tipo de cena (validação pydantic)
- `motor/narracao.py`: Kokoro, corte de silêncio, cronograma, normalização
- `motor/linha_do_tempo.py`: trechos seguidos com a mesma cena formam uma "corrida" (a cena
  continua e só anima o que muda); `texto_grande` com estilo `carimbo` entra por cima da anterior
- `motor/cenas/`: as 32 cenas do catálogo (gráficos: barras, barras_pareadas, barra_empilhada,
  ranking, pizza, bolhas, medidor, funil, inclinacao, escala, arvore, mapa_calor, linha, histograma,
  distribuicao, simulacao, icones, dispersao, grade_graficos, tabela;
  apoio: numero_grande, comparacao, objeto, passos, linha_do_tempo, citacao, diagrama_causal,
  texto_grande, pessoa, lugar, mapa, chamada). `exemplos/vitrine_cenas.json` e `vitrine_cenas_2.json` mostram as novas
- `motor/ilustracoes/`: caricatura/silhueta, lugares (`LUGARES`), marcos famosos para a cena `lugar`
  (`MARCOS`: torre Eiffel, Big Ben, Liberdade, Cristo, Golden Gate, Coliseu, templo, pirâmides, cúpula,
  universidade, arranha-céus, farol, hospital, montanhas) e objetos (`OBJETOS`)
- `motor/trilha.py`: trilha ambiente e whoosh gerados por código, com ducking sob a voz
- `exemplos/`: roteiro do Paradoxo de Simpson e um teste das demais cenas

## Estrutura

- `app/` — servidor FastAPI, templates Jinja2, CSS, worker
- `motor/` — renderização (cenas, voz, FFmpeg) e CLI
- `exemplos/` — roteiros de exemplo em JSON
- `referencia/` — código dos três vídeos feitos à mão (base do `motor/`)
- `temas_ciencia_de_dados.csv` — lista de temas importada pelo botão da aba Temas (106 temas, 11 categorias)
- `temas_iniciais.csv` — primeira lista (histórico)
- `data/`, `storage/`, `models/` — gerados localmente, fora do Git

## Versão de teste para amigos (`lite/`)

Uma página só: a pessoa digita um tema e recebe o vídeo pronto (MP4). Roda separada do estúdio
(porta 8100, banco `data/lite.db`, arquivos em `storage/lite/`) e reaproveita o roteirista e o motor.

- `make lite`: site + fila + link público temporário (túnel do Cloudflare, precisa do `cloudflared`).
- `make lite-local`: igual, sem link público.
- `make lite-teste`: sem link público e sem IA (usa o roteiro de exemplo; não gasta crédito).

Administração em http://localhost:8100/admin (só abre no próprio Mac, nunca pelo túnel): crie um convite
por amigo, com limite de vídeos, e defina o teto de gasto da OpenAI. Cada convite vira um link
`<link público>/c/<código>`. O link público muda a cada vez que o túnel abre.
Usa a `OPENAI_API_KEY` do `.env`; vídeos que falham não contam no limite do convite.
