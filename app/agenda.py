"""Agenda: publicações por vídeo e plataforma, horários (America/Sao_Paulo), 'preencher a semana', painel."""

import json
import secrets
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.db import transacao

TZ = ZoneInfo("America/Sao_Paulo")
PLATAFORMAS = {"instagram": "Instagram", "tiktok": "TikTok"}
LIMITE_LEGENDA = {"instagram": 2200, "tiktok": 2200}
LIMITE_HASHTAGS = {"instagram": 30, "tiktok": 30}
DIAS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
STATUS = {"pendente": "pendente", "agendado": "agendado", "enviando": "enviando…", "publicado": "publicado",
          "rascunho_enviado": "rascunho no TikTok", "erro": "erro"}
RASCUNHO_EXPIRA_H = 24


# ---------------------------------------------------------------- horários

def agora_utc() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def para_utc(local: str) -> str:
    """'2026-11-04T12:00' (São Paulo) -> '2026-11-04 15:00:00' (UTC, formato do SQLite)."""
    dt = datetime.fromisoformat(local).replace(tzinfo=TZ)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def para_local(utc: str | None, fmt: str = "%d/%m %H:%M") -> str:
    if not utc:
        return ""
    dt = datetime.fromisoformat(utc.replace(" ", "T")).replace(tzinfo=timezone.utc).astimezone(TZ)
    return dt.strftime(fmt)


def local_input(utc: str | None) -> str:
    """Valor para <input type=datetime-local>."""
    return para_local(utc, "%Y-%m-%dT%H:%M") if utc else ""


def dia_semana(utc: str) -> str:
    dt = datetime.fromisoformat(utc.replace(" ", "T")).replace(tzinfo=timezone.utc).astimezone(TZ)
    return f"{DIAS[dt.weekday()]} {dt:%d/%m}"


def horarios(con) -> dict[int, list[str]]:
    r = con.execute("SELECT valor FROM ajuste WHERE chave = 'horarios_semana'").fetchone()
    d = json.loads(r[0]) if r else {}
    return {i: sorted(d.get(str(i), [])) for i in range(7)}


def salvar_horarios(con, h: dict[int, list[str]]):
    valor = json.dumps({str(k): v for k, v in h.items()})
    con.execute("INSERT INTO ajuste (chave, valor) VALUES ('horarios_semana', ?) "
                "ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor", (valor,))


def modo_real(con) -> bool:
    r = con.execute("SELECT valor FROM ajuste WHERE chave = 'publicacao_real'").fetchone()
    return bool(r and r[0] == "1")


# ---------------------------------------------------------------- legendas

def legenda_final(video, plataforma: str) -> str:
    especifica = (video["legenda_" + plataforma] or "").strip()
    base = especifica or (video["legenda_base"] or "").strip()
    tags = (video["hashtags"] or "").strip()
    return f"{base}\n\n{tags}".strip() if tags and tags not in base else base


def contar_hashtags(texto: str) -> int:
    return sum(1 for p in texto.split() if p.startswith("#") and len(p) > 1)


# ---------------------------------------------------------------- publicações

def publicacao(con, video_id: int, plataforma: str):
    return con.execute("SELECT * FROM publicacao WHERE video_id = ? AND plataforma = ?",
                       (video_id, plataforma)).fetchone()


def garantir(con, video_id: int, plataforma: str) -> int:
    p = publicacao(con, video_id, plataforma)
    if p:
        return p["id"]
    return con.execute("INSERT INTO publicacao (video_id, plataforma) VALUES (?, ?)",
                       (video_id, plataforma)).lastrowid


def registrar(con, pub_id: int, msg: str):
    linha = f"{datetime.now(TZ):%d/%m %H:%M:%S} {msg}\n"
    con.execute("UPDATE publicacao SET log = log || ?, atualizado_em = datetime('now') WHERE id = ?", (linha, pub_id))


def agendar(con, video_id: int, plataforma: str, quando_utc: str, lote: str | None = None) -> int:
    pid = garantir(con, video_id, plataforma)
    p = con.execute("SELECT status FROM publicacao WHERE id = ?", (pid,)).fetchone()
    if p["status"] in ("publicado", "enviando"):
        raise ValueError(f"{PLATAFORMAS[plataforma]}: já {STATUS[p['status']]}.")
    con.execute("UPDATE publicacao SET status = 'agendado', agendado_para = ?, erro = NULL, lote = ?,"
                " atualizado_em = datetime('now') WHERE id = ?", (quando_utc, lote, pid))
    registrar(con, pid, f"agendado para {para_local(quando_utc)}")
    _status_tema(con, video_id)
    return pid


def cancelar(con, pub_id: int):
    p = con.execute("SELECT * FROM publicacao WHERE id = ?", (pub_id,)).fetchone()
    if p and p["status"] in ("agendado", "erro"):
        con.execute("UPDATE publicacao SET status = 'pendente', agendado_para = NULL, lote = NULL,"
                    " atualizado_em = datetime('now') WHERE id = ?", (pub_id,))
        registrar(con, pub_id, "agendamento cancelado")
        _status_tema(con, p["video_id"])


def publicar_agora(con, video_id: int, plataforma: str) -> int:
    """Coloca na fila imediatamente (o worker executa)."""
    pid = garantir(con, video_id, plataforma)
    p = con.execute("SELECT status FROM publicacao WHERE id = ?", (pid,)).fetchone()
    if p["status"] in ("publicado", "enviando"):
        raise ValueError(f"{PLATAFORMAS[plataforma]}: já {STATUS[p['status']]}.")
    con.execute("UPDATE publicacao SET status = 'agendado', agendado_para = datetime('now'), erro = NULL,"
                " atualizado_em = datetime('now') WHERE id = ?", (pid,))
    registrar(con, pid, "publicar agora (confirmado)")
    disparar_vencidas(con)
    return pid


def _status_tema(con, video_id: int):
    """Tema: 'publicado' se alguma plataforma publicou, 'agendado' se há agendamento, senão 'aprovado'."""
    v = con.execute("SELECT tema_id FROM video WHERE id = ?", (video_id,)).fetchone()
    sts = {r[0] for r in con.execute("SELECT status FROM publicacao WHERE video_id = ?", (video_id,))}
    novo = ("publicado" if sts & {"publicado", "rascunho_enviado"} else
            "agendado" if sts & {"agendado", "enviando"} else "aprovado")
    con.execute("UPDATE tema SET status = ?, atualizado_em = datetime('now') WHERE id = ?", (novo, v["tema_id"]))


def disparar_vencidas(con) -> int:
    """Publicações agendadas cujo horário chegou viram trabalhos na fila (status 'enviando')."""
    n = 0
    with transacao(con):
        vencidas = con.execute("SELECT publicacao.*, video.tema_id FROM publicacao JOIN video ON video.id = video_id"
                               " WHERE publicacao.status = 'agendado' AND agendado_para <= datetime('now')").fetchall()
        for p in vencidas:
            con.execute("UPDATE publicacao SET status = 'enviando', atualizado_em = datetime('now') WHERE id = ?",
                        (p["id"],))
            con.execute("INSERT INTO trabalho (tipo, referencia_id, payload_json) VALUES ('publicacao', ?, ?)",
                        (p["tema_id"], json.dumps({"publicacao_id": p["id"]})))
            n += 1
    return n


# ---------------------------------------------------------------- preencher a semana

def preencher_semana(con, plataformas: list[str], inicio: datetime | None = None, dias: int = 7) -> list[dict]:
    """Distribui vídeos aprovados ainda sem agendamento nos horários livres dos próximos `dias`."""
    lote = "lote-" + secrets.token_hex(4)
    inicio = (inicio or datetime.now(TZ)).astimezone(TZ)
    h = horarios(con)
    ocupados = {r[0] for r in con.execute(
        "SELECT agendado_para FROM publicacao WHERE status IN ('agendado', 'enviando') AND agendado_para IS NOT NULL")}
    slots = []
    for d in range(dias):
        dia = (inicio + timedelta(days=d)).date()
        for hora in h[(inicio + timedelta(days=d)).weekday()]:
            hh, mm = map(int, hora.split(":"))
            dt = datetime(dia.year, dia.month, dia.day, hh, mm, tzinfo=TZ)
            if dt <= inicio + timedelta(minutes=10):
                continue
            utc = dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            if utc not in ocupados:
                slots.append(utc)
    resultado = []
    videos = con.execute("SELECT * FROM video ORDER BY aprovado_em, id").fetchall()
    fila = []
    for v in videos:
        faltam = []
        for plat in plataformas:
            p = publicacao(con, v["id"], plat)
            if p is None or p["status"] in ("pendente", "erro"):
                faltam.append(plat)
        if faltam:
            fila.append((v, faltam))
    for (v, faltam), slot in zip(fila, slots):
        for plat in faltam:
            agendar(con, v["id"], plat, slot, lote)
        resultado.append({"video": v["titulo"], "quando": f"{dia_semana(slot)} {para_local(slot, '%H:%M')}", "plataformas": faltam,
                          "lote": lote})
    return resultado


def desfazer_lote(con, lote: str) -> int:
    ids = [r[0] for r in con.execute("SELECT id FROM publicacao WHERE lote = ? AND status = 'agendado'", (lote,))]
    for i in ids:
        cancelar(con, i)
    return len(ids)


# ---------------------------------------------------------------- painel

def painel(con) -> dict:
    agora = agora_utc()
    linhas = con.execute(
        "SELECT publicacao.*, video.titulo, video.tema_id, video.caminho_capa FROM publicacao"
        " JOIN video ON video.id = publicacao.video_id ORDER BY coalesce(agendado_para, publicado_em, enviado_em)").fetchall()
    agendados = [p for p in linhas if p["status"] in ("agendado", "enviando")]
    publicados = sorted([p for p in linhas if p["status"] == "publicado"],
                        key=lambda p: p["publicado_em"] or "", reverse=True)
    erros = [p for p in linhas if p["status"] == "erro"]
    rascunhos = []
    for p in linhas:
        if p["status"] == "rascunho_enviado" and p["enviado_em"]:
            enviado = datetime.fromisoformat(p["enviado_em"].replace(" ", "T")).replace(tzinfo=timezone.utc)
            resta = enviado + timedelta(hours=RASCUNHO_EXPIRA_H) - agora
            rascunhos.append({"p": p, "horas": resta.total_seconds() / 3600})
    semana = {}
    for p in agendados:
        semana.setdefault(dia_semana(p["agendado_para"]), []).append(p)
    return {"agendados": agendados, "publicados": publicados, "erros": erros, "rascunhos": rascunhos,
            "semana": semana}
