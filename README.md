# Estúdio

Plataforma local para produzir e agendar vídeos curtos de curiosidades de dados.
Especificação completa em [PROMPT.md](PROMPT.md).

## Como rodar

Pré-requisitos: [uv](https://docs.astral.sh/uv/) e FFmpeg (`brew install uv ffmpeg`).

```sh
make instalar   # cria o .venv com Python 3.12 e instala as dependências
./scripts/baixar_modelos.sh   # modelos de voz do Kokoro (~340 MB) em models/
cp .env.example .env   # e preencha as chaves (quando chegar a fase delas)
make dev        # sobe o servidor (http://localhost:8000) e o worker
```

Em `make dev`, qualquer mudança em `app/` (.py, .html, .css, .js) reinicia o servidor e a
página aberta no navegador recarrega sozinha.

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
- `motor/cenas/`: as 12 cenas do catálogo
- `motor/ilustracoes/`: caricatura/silhueta e a biblioteca de lugares (`LUGARES`)
- `exemplos/`: roteiro do Paradoxo de Simpson e um teste das demais cenas

## Estrutura

- `app/` — servidor FastAPI, templates Jinja2, CSS, worker
- `motor/` — renderização (cenas, voz, FFmpeg) e CLI
- `exemplos/` — roteiros de exemplo em JSON
- `referencia/` — código dos três vídeos feitos à mão (base do `motor/`)
- `temas_iniciais.csv` — temas para importar na Fase 2
- `data/`, `storage/`, `models/` — gerados localmente, fora do Git
