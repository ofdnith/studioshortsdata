# Estúdio

Plataforma local para produzir e agendar vídeos curtos de curiosidades de dados.
Especificação completa em [PROMPT.md](PROMPT.md).

## Como rodar

Pré-requisitos: [uv](https://docs.astral.sh/uv/) (`brew install uv`).

```sh
make instalar   # cria o .venv com Python 3.12 e instala as dependências
cp .env.example .env   # e preencha as chaves (quando chegar a fase delas)
make dev        # sobe o servidor (http://localhost:8000) e o worker
```

Em `make dev`, qualquer mudança em `app/` (.py, .html, .css, .js) reinicia o servidor e a
página aberta no navegador recarrega sozinha.

## Estrutura

- `app/` — servidor FastAPI, templates Jinja2, CSS, worker
- `referencia/` — código dos três vídeos feitos à mão (base do futuro `motor/`)
- `temas_iniciais.csv` — temas para importar na Fase 2
- `data/`, `storage/`, `models/` — gerados localmente, fora do Git
