"""Dados fictícios da Fase 1 (somem quando o SQLite entrar, na Fase 2)."""

ROTULO_STATUS = {
    "ideia": "Ideia",
    "em_roteiro": "Em roteiro",
    "roteiro_pronto": "Roteiro pronto",
    "roteiro_aprovado": "Roteiro aprovado",
    "renderizando": "Renderizando",
    "pronto_para_revisao": "Pronto p/ revisão",
    "aprovado": "Aprovado",
    "agendado": "Agendado",
    "publicado": "Publicado",
    "descartado": "Descartado",
}

TEMAS = [
    {"id": 1, "titulo": "Viés de sobrevivência: os aviões da 2ª Guerra", "categoria": "Vieses e armadilhas",
     "prioridade": "alta", "status": "publicado", "criado_em": "2026-10-20"},
    {"id": 2, "titulo": "Paradoxo de Simpson: Berkeley 1973", "categoria": "Vieses e armadilhas",
     "prioridade": "media", "status": "agendado", "criado_em": "2026-10-20"},
    {"id": 3, "titulo": "Datasaurus e o Quarteto de Anscombe", "categoria": "Visualização",
     "prioridade": "alta", "status": "aprovado", "criado_em": "2026-10-21"},
    {"id": 4, "titulo": "Viés de seleção: Literary Digest 1936", "categoria": "Vieses e armadilhas",
     "prioridade": "media", "status": "renderizando", "criado_em": "2026-10-22"},
    {"id": 5, "titulo": "Regressão à média: a maldição da capa", "categoria": "Vieses e armadilhas",
     "prioridade": "media", "status": "roteiro_pronto", "criado_em": "2026-10-23"},
    {"id": 6, "titulo": "O mapa do cólera de John Snow", "categoria": "História dos dados",
     "prioridade": "alta", "status": "em_roteiro", "criado_em": "2026-10-24"},
    {"id": 7, "titulo": "Florence Nightingale e o diagrama de rosa", "categoria": "História dos dados",
     "prioridade": "alta", "status": "ideia", "criado_em": "2026-10-25"},
    {"id": 8, "titulo": "Correlação espúria: queijo e lençóis", "categoria": "Vieses e armadilhas",
     "prioridade": "baixa", "status": "ideia", "criado_em": "2026-10-26"},
    {"id": 9, "titulo": "Lei de Benford e fraudes contábeis", "categoria": "Estatística curiosa",
     "prioridade": "media", "status": "descartado", "criado_em": "2026-10-27"},
]

FILA_PRODUCAO = [
    {"tema": "Viés de seleção: Literary Digest 1936", "etapa": "Renderizando", "progresso": 62,
     "detalhe": "Cena 7 de 11"},
    {"tema": "Regressão à média: a maldição da capa", "etapa": "Roteiro pronto", "progresso": 100,
     "detalhe": "Aguardando sua revisão"},
    {"tema": "O mapa do cólera de John Snow", "etapa": "Gerando roteiro", "progresso": 30,
     "detalhe": "Buscando fontes oficiais"},
]

BIBLIOTECA = [
    {"titulo": "Viés de sobrevivência", "duracao": "1:10",
     "instagram": "publicado", "tiktok": "rascunho_enviado"},
    {"titulo": "Paradoxo de Simpson", "duracao": "1:09",
     "instagram": "agendado", "tiktok": "agendado"},
    {"titulo": "Datasaurus e Anscombe", "duracao": "1:10",
     "instagram": "pendente", "tiktok": "pendente"},
]

AGENDADOS = [
    {"quando": "ter 04/11 · 12:00", "titulo": "Paradoxo de Simpson", "plataforma": "Instagram"},
    {"quando": "ter 04/11 · 18:30", "titulo": "Paradoxo de Simpson", "plataforma": "TikTok"},
]

CONTAS = [
    {"plataforma": "Instagram", "conectada": False, "validade": None},
    {"plataforma": "TikTok", "conectada": False, "validade": None},
]


def categorias() -> list[str]:
    return sorted({t["categoria"] for t in TEMAS})


def filtrar_temas(q: str, categoria: str, status: str) -> list[dict]:
    q = q.strip().lower()
    return [
        t for t in TEMAS
        if (not q or q in t["titulo"].lower())
        and (not categoria or t["categoria"] == categoria)
        and (not status or t["status"] == status)
    ]
