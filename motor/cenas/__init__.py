"""Catálogo de cenas: tipo -> função desenhar(canvas, contexto)."""

from motor.cenas.graficos import barra_empilhada, barras, barras_pareadas, tabela
from motor.cenas.outras import chamada, diagrama_causal, lugar, mapa, pessoa, texto_grande
from motor.cenas.pontos import dispersao, grade_graficos

CENAS = {
    "barras": barras,
    "barras_pareadas": barras_pareadas,
    "barra_empilhada": barra_empilhada,
    "dispersao": dispersao,
    "grade_graficos": grade_graficos,
    "tabela": tabela,
    "diagrama_causal": diagrama_causal,
    "pessoa": pessoa,
    "lugar": lugar,
    "mapa": mapa,
    "texto_grande": texto_grande,
    "chamada": chamada,
}
