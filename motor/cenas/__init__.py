"""Catálogo de cenas: tipo -> função desenhar(canvas, contexto)."""

from motor.cenas.graficos import barra_empilhada, barras, barras_pareadas, tabela
from motor.cenas.outras import chamada, diagrama_causal, lugar, mapa, pessoa, texto_grande
from motor.cenas.conceituais import citacao, comparacao, icones, linha_do_tempo, numero_grande, objeto, passos
from motor.cenas.graficos2 import distribuicao, histograma, linha, pizza, ranking, simulacao
from motor.cenas.graficos3 import arvore, bolhas, escala, funil, inclinacao, mapa_calor, medidor
from motor.cenas.desenho import desenho
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
    "linha": linha,
    "distribuicao": distribuicao,
    "histograma": histograma,
    "pizza": pizza,
    "ranking": ranking,
    "simulacao": simulacao,
    "icones": icones,
    "numero_grande": numero_grande,
    "objeto": objeto,
    "comparacao": comparacao,
    "linha_do_tempo": linha_do_tempo,
    "passos": passos,
    "citacao": citacao,
    "medidor": medidor,
    "bolhas": bolhas,
    "funil": funil,
    "mapa_calor": mapa_calor,
    "inclinacao": inclinacao,
    "escala": escala,
    "arvore": arvore,
    "desenho": desenho,
}
