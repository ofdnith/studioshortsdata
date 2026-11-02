dev:
	ESTUDIO_DEV=1 PYTHONUNBUFFERED=1 uv run honcho start

instalar:
	uv sync

.PHONY: dev instalar
