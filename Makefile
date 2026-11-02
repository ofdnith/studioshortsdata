dev:
	ESTUDIO_DEV=1 PYTHONUNBUFFERED=1 uv run honcho start

# Versão de teste para amigos (porta 8100): site + fila + link público (túnel do Cloudflare)
lite:
	PYTHONUNBUFFERED=1 uv run honcho -f Procfile.lite start

# Mesma coisa, sem link público (só no seu Mac)
lite-local:
	PYTHONUNBUFFERED=1 uv run honcho -f Procfile.lite-local start

# Sem link público e sem IA: usa o roteiro de exemplo (não gasta crédito)
lite-teste:
	LITE_FALSO=1 PYTHONUNBUFFERED=1 uv run honcho -f Procfile.lite-local start

instalar:
	uv sync

.PHONY: dev instalar lite lite-local lite-teste
