"""Versão simplificada do estúdio para amigos testarem: tema → vídeo, por convite.

Roda separada do estúdio (porta 8100, banco data/lite.db, arquivos em storage/lite/) e reaproveita
o roteirista (OpenAI) e o motor de vídeo. Usa a chave da OpenAI do dono, com limite por convite e
um teto de gasto total.
"""
