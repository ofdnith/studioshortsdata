"""Constantes e valores padrão do estúdio."""

STATUS_TEMA = {
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

PRIORIDADES = {"alta": "Alta", "media": "Média", "baixa": "Baixa"}

# Vozes pt-br do Kokoro v1.0.
VOZES = {
    "pf_dora": "Dora (feminina)",
    "pm_alex": "Alex (masculina)",
    "pm_santa": "Santa (masculina, grave)",
}

TONS = {
    "curioso": "Curioso (padrão)",
    "dramatico": "Dramático",
    "bem_humorado": "Bem-humorado",
    "didatico": "Didático",
}

# Personalização padrão de cada vídeo. O tema guarda só o que for diferente disto.
CONFIG_PADRAO = {
    "voz": "pf_dora",
    "velocidade": 1.2,
    "duracao_alvo_s": 70,
    "tom": "curioso",
    "instrucoes": "",
    "modelo": "",        # "" = modelo padrão da tela IA
    "trilha": "ambiente",
}

TRILHAS = {"ambiente": "Ambiente suave + efeitos de transição", "nenhuma": "Sem trilha (só a voz)"}


def config_efetiva(config_tema: dict) -> dict:
    """Padrão + o que o tema sobrescreve (ignora valores vazios)."""
    efetiva = dict(CONFIG_PADRAO)
    efetiva.update({k: v for k, v in config_tema.items() if v not in (None, "")})
    return efetiva
