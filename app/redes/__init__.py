"""Contas das redes (tokens no SQLite local) e a tarefa de publicação."""

import json
from datetime import datetime, timedelta, timezone

from app import agenda as ag
from app.db import RAIZ

RENOVAR_ANTES_DIAS = 10


def conta(con, plataforma: str):
    return con.execute("SELECT * FROM conta WHERE plataforma = ? AND access_token IS NOT NULL",
                       (plataforma,)).fetchone()


def salvar_conta(con, plataforma: str, d: dict):
    con.execute(
        "INSERT INTO conta (plataforma, access_token, refresh_token, expira_em, usuario, conta_id, escopos,"
        " refresh_expira_em, renovado_em, atualizado_em) VALUES (?,?,?,?,?,?,?,?,datetime('now'),datetime('now'))"
        " ON CONFLICT(plataforma) DO UPDATE SET access_token=excluded.access_token,"
        " refresh_token=coalesce(excluded.refresh_token, conta.refresh_token), expira_em=excluded.expira_em,"
        " usuario=coalesce(excluded.usuario, conta.usuario), conta_id=coalesce(excluded.conta_id, conta.conta_id),"
        " escopos=coalesce(excluded.escopos, conta.escopos),"
        " refresh_expira_em=coalesce(excluded.refresh_expira_em, conta.refresh_expira_em),"
        " renovado_em=datetime('now'), atualizado_em=datetime('now')",
        (plataforma, d.get("access_token"), d.get("refresh_token"), d.get("expira_em"), d.get("usuario"),
         d.get("conta_id"), d.get("escopos"), d.get("refresh_expira_em")))


def desconectar(con, plataforma: str):
    con.execute("DELETE FROM conta WHERE plataforma = ?", (plataforma,))


def dias_restantes(expira_em: str | None) -> float | None:
    if not expira_em:
        return None
    dt = datetime.fromisoformat(expira_em.replace(" ", "T")).replace(tzinfo=timezone.utc)
    return (dt - datetime.now(timezone.utc)).total_seconds() / 86400


def renovar_tokens(con, log=print):
    """Instagram: renova o token longo quando faltam menos de 10 dias (e ele tem 24 h+)."""
    from app.redes import instagram
    c = conta(con, "instagram")
    if not c:
        return
    resta = dias_restantes(c["expira_em"])
    renovado = datetime.fromisoformat((c["renovado_em"] or "2000-01-01 00:00:00").replace(" ", "T")).replace(
        tzinfo=timezone.utc)
    if resta is not None and 0 < resta < RENOVAR_ANTES_DIAS and \
            datetime.now(timezone.utc) - renovado > timedelta(hours=24):
        try:
            salvar_conta(con, "instagram", instagram.renovar(c["access_token"]))
            log("token do Instagram renovado")
        except Exception as e:
            log(f"falha ao renovar o token do Instagram: {e}")


def tarefa_publicacao(con, trabalho):
    pid = json.loads(trabalho["payload_json"])["publicacao_id"]
    p = con.execute("SELECT * FROM publicacao WHERE id = ?", (pid,)).fetchone()
    v = con.execute("SELECT * FROM video WHERE id = ?", (p["video_id"],)).fetchone()
    plat = p["plataforma"]
    legenda = ag.legenda_final(v, plat)

    def log(m):
        ag.registrar(con, pid, m)
        con.execute("UPDATE trabalho SET log = log || ? WHERE id = ?",
                    (f"{datetime.now():%H:%M:%S} {m}\n", trabalho["id"]))

    try:
        if not ag.modo_real(con):
            log(f"SIMULAÇÃO: publicaria no {ag.PLATAFORMAS[plat]} “{v['titulo']}” ({len(legenda)} caracteres de legenda)")
            if plat == "tiktok":
                con.execute("UPDATE publicacao SET status = 'rascunho_enviado', enviado_em = datetime('now'),"
                            " simulado = 1, id_externo = 'simulado' WHERE id = ?", (pid,))
            else:
                con.execute("UPDATE publicacao SET status = 'publicado', publicado_em = datetime('now'),"
                            " simulado = 1, id_externo = 'simulado', link = NULL WHERE id = ?", (pid,))
            return
        if plat == "instagram":
            from app.redes import instagram
            from app.redes.tunel import url_publica
            c = conta(con, "instagram")
            if not c:
                raise RuntimeError("Conta do Instagram não conectada (aba Contas).")
            arquivo = RAIZ / "storage" / v["caminho"]
            log(f"publicando no Instagram como @{c['usuario']}")
            with url_publica(arquivo, log=log) as url:
                res = instagram.publicar_reel(c, url, legenda, log=log)
            con.execute("UPDATE publicacao SET status = 'publicado', publicado_em = datetime('now'), simulado = 0,"
                        " id_externo = ?, link = ? WHERE id = ?", (res["id"], res["link"], pid))
            log(f"publicado: {res['link'] or res['id']}")
        else:
            raise RuntimeError("Envio para o TikTok chega na Fase 7.")
    except Exception as e:
        con.execute("UPDATE publicacao SET status = 'erro', erro = ? WHERE id = ?", (str(e), pid))
        log(f"ERRO: {e}")
        raise
    finally:
        ag._status_tema(con, v["id"])
