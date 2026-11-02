"""Em que etapa cada vídeo está e qual é o próximo passo.

Quatro etapas, sempre na mesma ordem: Tema → Roteiro → Vídeo → Publicar.
O estado vem dos dados (roteiros, renders, trabalhos na fila, publicações), não só do status do tema.
"""

from dataclasses import dataclass, field

NOMES = ("Tema", "Roteiro", "Vídeo", "Publicar")


@dataclass
class Etapa:
    nome: str
    estado: str          # "feito", "atual", "rodando", "erro", "futuro"
    url: str | None      # para onde o clique leva (None = ainda não dá para abrir)
    detalhe: str = ""


@dataclass
class Proximo:
    titulo: str
    texto: str
    botao: str = ""
    url: str = ""            # link (GET)
    acao: str = ""           # formulário (POST)
    confirmar: str = ""
    rodando: bool = False
    erro: str = ""
    extra: dict = field(default_factory=dict)


@dataclass
class Estado:
    etapas: list[Etapa]
    proximo: Proximo
    indice: int          # etapa atual (0 a 3)
    rotulo: str          # resumo curto para listas ("Revisar roteiro", "Renderizando 40%")
    cor: str             # classe da pílula: "", "aviso", "azul", "ok", "falha"


def _job(con, tipo, tema_id):
    return con.execute("SELECT * FROM trabalho WHERE tipo = ? AND referencia_id = ? ORDER BY id DESC LIMIT 1",
                       (tipo, tema_id)).fetchone()


def estado(con, tema) -> Estado:
    tid = tema["id"]
    base = f"/temas/{tid}"
    roteiro = con.execute("SELECT * FROM roteiro WHERE tema_id = ? ORDER BY versao DESC LIMIT 1", (tid,)).fetchone()
    aprovado = con.execute("SELECT * FROM roteiro WHERE tema_id = ? AND aprovado_em IS NOT NULL"
                           " ORDER BY versao DESC LIMIT 1", (tid,)).fetchone()
    job_rot = _job(con, "roteiro", tid)
    render = con.execute("SELECT render.* FROM render JOIN roteiro ON roteiro.id = render.roteiro_id"
                         " WHERE roteiro.tema_id = ? ORDER BY render.id DESC LIMIT 1", (tid,)).fetchone()
    video = con.execute("SELECT * FROM video WHERE tema_id = ?", (tid,)).fetchone()
    pubs = con.execute("SELECT * FROM publicacao WHERE video_id = ?", (video["id"],)).fetchall() if video else []

    gerando = job_rot is not None and job_rot["status"] in ("na_fila", "rodando")
    erro_rot = (job_rot is not None and job_rot["status"] == "erro"
                and (roteiro is None or job_rot["atualizado_em"] >= roteiro["criado_em"]))
    revisar = roteiro is not None and (aprovado is None or aprovado["id"] != roteiro["id"])
    render_atual = render is not None and aprovado is not None and render["roteiro_id"] == aprovado["id"]
    renderizando = render is not None and render["status"] in ("na_fila", "rodando")
    erro_render = render is not None and render["status"] == "erro"
    video_ok = video is not None and render is not None and video["render_id"] == render["id"]
    publicados = [p for p in pubs if p["status"] == "publicado"]
    agendados = [p for p in pubs if p["status"] in ("agendado", "enviando", "rascunho_enviado")]

    # --- etapa 2: roteiro
    if gerando:
        e_rot = Etapa("Roteiro", "rodando", f"{base}/roteiro" if roteiro else None,
                      "a IA está escrevendo" if not roteiro else "aplicando correção")
    elif erro_rot:
        e_rot = Etapa("Roteiro", "erro", f"{base}/roteiro" if roteiro else None, "a geração falhou")
    elif revisar:
        e_rot = Etapa("Roteiro", "atual", f"{base}/roteiro", f"v{roteiro['versao']} para revisar")
    elif aprovado:
        e_rot = Etapa("Roteiro", "feito", f"{base}/roteiro?v={aprovado['versao']}", f"v{aprovado['versao']} aprovado")
    else:
        e_rot = Etapa("Roteiro", "futuro", None, "")

    # --- etapa 3: vídeo
    if renderizando:
        e_vid = Etapa("Vídeo", "rodando", f"{base}/video", f"renderizando {render['progresso'] or 0}%")
    elif revisar or aprovado is None:
        e_vid = Etapa("Vídeo", "futuro", f"{base}/video" if render else None, "")
    elif not render_atual:
        e_vid = Etapa("Vídeo", "atual", f"{base}/video", "renderizar")
    elif erro_render:
        e_vid = Etapa("Vídeo", "erro", f"{base}/video", "o render falhou")
    elif video_ok:
        e_vid = Etapa("Vídeo", "feito", f"{base}/video", "aprovado")
    elif render["status"] == "ok":
        e_vid = Etapa("Vídeo", "atual", f"{base}/video", "assistir e aprovar")
    else:
        e_vid = Etapa("Vídeo", "futuro", f"{base}/video" if render else None, "")

    # --- etapa 4: publicar
    if video and publicados:
        e_pub = Etapa("Publicar", "feito", f"/videos/{video['id']}", "publicado")
    elif video and agendados:
        e_pub = Etapa("Publicar", "feito", f"/videos/{video['id']}", "agendado")
    elif video_ok:
        e_pub = Etapa("Publicar", "atual", f"/videos/{video['id']}", "agendar")
    else:
        e_pub = Etapa("Publicar", "futuro", f"/videos/{video['id']}" if video else None, "")

    e_tema = Etapa("Tema", "feito" if (roteiro or gerando or erro_rot) else "atual", base,
                   "" if (roteiro or gerando) else "conferir e gerar")
    etapas = [e_tema, e_rot, e_vid, e_pub]

    # --- próximo passo (o que a pessoa deve fazer agora)
    if gerando:
        p = Proximo("A IA está trabalhando", "Pesquisando as fontes, escrevendo o roteiro e desenhando a animação. "
                    "Leva alguns minutos; pode sair desta página.", rodando=True, extra={"job": job_rot})
        rot, cor = ("Na fila" if job_rot["status"] == "na_fila" else "Gerando roteiro"), "azul"
    elif renderizando:
        p = Proximo("Renderizando o vídeo", "Narração, animação e áudio, tudo no seu Mac (sem custo de IA).",
                    url=f"{base}/video", botao="Acompanhar", rodando=True, extra={"render": render})
        rot, cor = f"Renderizando {render['progresso'] or 0}%", "azul"
    elif erro_rot:
        p = Proximo("A geração do roteiro falhou", "", erro=job_rot["erro"] or "",
                    acao=f"/trabalhos/{job_rot['id']}/repetir", botao="Tentar de novo",
                    confirmar="Tentar de novo chama a IA (consome crédito). Continuar?")
        rot, cor = "Erro no roteiro", "falha"
    elif not roteiro:
        p = Proximo("Gerar o roteiro", "A IA pesquisa fontes reais, escreve a narração e desenha a animação. "
                    "Antes, se quiser, ajuste o tema e as opções do vídeo abaixo.",
                    acao=f"{base}/gerar", botao="Gerar roteiro com IA",
                    confirmar="Gerar o roteiro chama a IA e consome crédito. Continuar?")
        rot, cor = ("Ideia" if tema["status"] != "descartado" else "Descartado"), ""
    elif revisar:
        p = Proximo("Revisar o roteiro", "Leia a narração, confira as fontes e a prévia dos quadros. "
                    "Ajuste o que quiser e aprove.", url=f"{base}/roteiro", botao="Revisar roteiro")
        rot, cor = "Revisar roteiro", "aviso"
    elif erro_render and render_atual:
        p = Proximo("O render falhou", "Veja o log na página do vídeo.", url=f"{base}/video", botao="Ver o erro",
                    erro=(render["log"] or "").strip().split("\n")[-1][:300])
        rot, cor = "Erro no render", "falha"
    elif not render_atual:
        p = Proximo("Renderizar o vídeo", f"O roteiro v{aprovado['versao']} está aprovado. O render roda no seu Mac "
                    "e leva poucos minutos.", acao=f"/roteiros/{aprovado['id']}/renderizar", botao="Renderizar vídeo")
        rot, cor = "Pronto para renderizar", "aviso"
    elif not video_ok:
        p = Proximo("Assistir e aprovar", "Confira o vídeo pronto. Se gostar, aprove para ir à biblioteca.",
                    url=f"{base}/video", botao="Assistir vídeo")
        rot, cor = "Aprovar vídeo", "aviso"
    elif publicados:
        p = Proximo("Publicado", "Este vídeo já está no ar.", url=f"/videos/{video['id']}", botao="Ver publicação")
        rot, cor = "Publicado", "ok"
    elif agendados:
        p = Proximo("Agendado", "A publicação sai sozinha no horário marcado.", url=f"/videos/{video['id']}",
                    botao="Ver agendamento")
        rot, cor = "Agendado", "ok"
    else:
        p = Proximo("Agendar a publicação", "Revise a legenda e escolha quando postar.",
                    url=f"/videos/{video['id']}", botao="Legenda e agendamento")
        rot, cor = "Agendar", "aviso"

    if tema["status"] == "descartado" and not roteiro:
        rot, cor = "Descartado", "falha"
    indice = next((i for i, e in enumerate(etapas) if e.estado in ("atual", "rodando", "erro")), 3)
    return Estado(etapas, p, indice, rot, cor)
