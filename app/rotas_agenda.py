"""Rotas da Agenda (publicações, semana, painel) e das Contas (Instagram; TikTok na Fase 7)."""

import json
import os
import time

from fastapi import Request
from fastapi.responses import RedirectResponse

from app import agenda as ag
from app import custos as cst
from app.db import conexao

CONFIRMACAO = "PUBLICAR"


def registrar_rotas(app, pagina, templates, redirecionar):

    # ------------------------------------------------------------ Agenda

    @app.get("/agenda")
    def agenda(request: Request):
        with conexao() as con:
            videos = con.execute(
                "SELECT video.*, tema.titulo AS tema_titulo,"
                " (SELECT status FROM publicacao p WHERE p.video_id = video.id AND p.plataforma = 'instagram') AS ig,"
                " (SELECT status FROM publicacao p WHERE p.video_id = video.id AND p.plataforma = 'tiktok') AS tt"
                " FROM video JOIN tema ON tema.id = video.tema_id ORDER BY video.aprovado_em DESC").fetchall()
            totais = cst.totais_por_tema(con)
            ctx = dict(videos=videos, totais=totais, cotacao=cst.cotacao(con), painel=ag.painel(con),
                       horarios=ag.horarios(con), real=ag.modo_real(con),
                       contas={r["plataforma"]: r for r in con.execute("SELECT * FROM conta")})
        ctx["soma"] = {m: sum(totais.get(v["tema_id"], {}).get(m, 0) for v in videos) for m in ("BRL", "USD")}
        ctx["sem_agenda"] = [v for v in videos if not v["ig"] or v["ig"] in ("pendente", "erro")
                             or not v["tt"] or v["tt"] in ("pendente", "erro")]
        return pagina(request, "agenda.html", "agenda", dias=ag.DIAS, para_local=ag.para_local,
                      plataformas=ag.PLATAFORMAS, status_pub=ag.STATUS, lote=request.query_params.get("lote"), **ctx)

    @app.post("/agenda/horarios")
    async def agenda_horarios(request: Request):
        form = await request.form()
        h = {}
        for i in range(7):
            itens = [x.strip() for x in str(form.get(f"h_{i}", "")).replace(";", ",").split(",") if x.strip()]
            ok = []
            for x in itens:
                try:
                    hh, mm = map(int, x.split(":"))
                    assert 0 <= hh < 24 and 0 <= mm < 60
                    ok.append(f"{hh:02d}:{mm:02d}")
                except (ValueError, AssertionError):
                    return redirecionar("/agenda", erro=f"Horário inválido: “{x}” (use 12:00, 19:30).")
            h[i] = sorted(set(ok))
        with conexao() as con:
            ag.salvar_horarios(con, h)
        return redirecionar("/agenda", msg="Horários da semana salvos.")

    @app.post("/agenda/preencher")
    async def agenda_preencher(request: Request):
        form = await request.form()
        plats = [p for p in form.getlist("plataformas") if p in ag.PLATAFORMAS]
        if not plats:
            return redirecionar("/agenda", erro="Escolha pelo menos uma plataforma.")
        with conexao() as con:
            res = ag.preencher_semana(con, plats)
        if not res:
            return redirecionar("/agenda", erro="Nada para agendar: sem vídeos aprovados pendentes ou sem horários livres.")
        texto = "; ".join(f"{r['video']} → {r['quando']}" for r in res)
        return redirecionar("/agenda", msg=f"{len(res)} vídeo(s) agendado(s): {texto}", lote=res[0]["lote"])

    @app.post("/agenda/desfazer/{lote}")
    def agenda_desfazer(lote: str):
        with conexao() as con:
            n = ag.desfazer_lote(con, lote)
        return redirecionar("/agenda", msg=f"{n} agendamento(s) desfeito(s).")

    @app.post("/agenda/modo")
    async def agenda_modo(request: Request):
        form = await request.form()
        real = form.get("real") == "1"
        if real and form.get("confirmacao", "").strip().upper() != CONFIRMACAO:
            return redirecionar("/agenda", erro=f"Para ligar a publicação real, digite {CONFIRMACAO}.")
        with conexao() as con:
            con.execute("INSERT INTO ajuste (chave, valor) VALUES ('publicacao_real', ?) "
                        "ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor", ("1" if real else "0",))
        return redirecionar("/agenda", msg="Publicação REAL ligada: os horários vencidos serão publicados de verdade."
                            if real else "Modo simulação ligado: nada é publicado de verdade.")

    # ------------------------------------------------------------ editor de publicação do vídeo

    @app.get("/videos/{video_id}")
    def video_publicacao(request: Request, video_id: int):
        with conexao() as con:
            v = con.execute("SELECT video.*, tema.titulo AS tema_titulo FROM video JOIN tema ON tema.id = video.tema_id"
                            " WHERE video.id = ?", (video_id,)).fetchone()
            if not v:
                return redirecionar("/agenda", erro="Vídeo não encontrado.")
            pubs = {p: ag.publicacao(con, video_id, p) for p in ag.PLATAFORMAS}
            ctx = dict(v=v, pubs=pubs, real=ag.modo_real(con), custos=cst.resumo(con, v["tema_id"]),
                       contas={r["plataforma"]: r for r in con.execute("SELECT * FROM conta")})
        finais = {p: ag.legenda_final(v, p) for p in ag.PLATAFORMAS}
        return pagina(request, "publicacao.html", "agenda", finais=finais, limites=ag.LIMITE_LEGENDA,
                      contar_hashtags=ag.contar_hashtags, plataformas=ag.PLATAFORMAS, status_pub=ag.STATUS,
                      para_local=ag.para_local, local_input=ag.local_input, confirmacao=CONFIRMACAO, **ctx)

    @app.post("/videos/{video_id}/legendas")
    async def video_legendas(request: Request, video_id: int):
        form = await request.form()
        with conexao() as con:
            con.execute("UPDATE video SET legenda_base = ?, legenda_instagram = ?, legenda_tiktok = ?, hashtags = ?,"
                        " titulo = ? WHERE id = ?",
                        (form.get("legenda_base", "").strip(), form.get("legenda_instagram", "").strip(),
                         form.get("legenda_tiktok", "").strip(), " ".join(form.get("hashtags", "").split()),
                         form.get("titulo", "").strip(), video_id))
        return redirecionar(f"/videos/{video_id}", msg="Legendas salvas.")

    @app.post("/videos/{video_id}/agendar")
    async def video_agendar(request: Request, video_id: int):
        form = await request.form()
        plat, quando = form.get("plataforma"), form.get("quando")
        if plat not in ag.PLATAFORMAS or not quando:
            return redirecionar(f"/videos/{video_id}", erro="Escolha a data e a hora.")
        utc = ag.para_utc(quando)
        if utc <= ag.agora_utc().strftime("%Y-%m-%d %H:%M:%S"):
            return redirecionar(f"/videos/{video_id}", erro="Esse horário já passou. Para agora, use “Publicar agora”.")
        try:
            with conexao() as con:
                ag.agendar(con, video_id, plat, utc)
        except ValueError as e:
            return redirecionar(f"/videos/{video_id}", erro=str(e))
        return redirecionar(f"/videos/{video_id}", msg=f"{ag.PLATAFORMAS[plat]} agendado para {ag.para_local(utc)}.")

    @app.post("/videos/{video_id}/publicar-agora")
    async def video_publicar_agora(request: Request, video_id: int):
        form = await request.form()
        plat = form.get("plataforma")
        if plat not in ag.PLATAFORMAS:
            return redirecionar(f"/videos/{video_id}", erro="Plataforma inválida.")
        with conexao() as con:
            if ag.modo_real(con) and form.get("confirmacao", "").strip().upper() != CONFIRMACAO:
                return redirecionar(f"/videos/{video_id}",
                                    erro=f"Publicação real: digite {CONFIRMACAO} para confirmar.")
            try:
                ag.publicar_agora(con, video_id, plat)
            except ValueError as e:
                return redirecionar(f"/videos/{video_id}", erro=str(e))
            real = ag.modo_real(con)
        return redirecionar(f"/videos/{video_id}", msg=f"{ag.PLATAFORMAS[plat]}: na fila "
                            f"({'PUBLICAÇÃO REAL' if real else 'simulação'}). Acompanhe abaixo.")

    @app.post("/publicacoes/{pub_id}/cancelar")
    async def publicacao_cancelar(request: Request, pub_id: int):
        form = await request.form()
        with conexao() as con:
            ag.cancelar(con, pub_id)
        return redirecionar(form.get("voltar") or "/agenda", msg="Agendamento cancelado.")

    @app.post("/publicacoes/{pub_id}/marcar-publicado")
    async def publicacao_marcar(request: Request, pub_id: int):
        """TikTok: depois de finalizar o rascunho no app, marca como publicado."""
        form = await request.form()
        with conexao() as con:
            p = con.execute("SELECT * FROM publicacao WHERE id = ?", (pub_id,)).fetchone()
            con.execute("UPDATE publicacao SET status = 'publicado', publicado_em = datetime('now'),"
                        " link = coalesce(nullif(?, ''), link) WHERE id = ?", (form.get("link", "").strip(), pub_id))
            ag.registrar(con, pub_id, "marcado como publicado (finalizado no app)")
            ag._status_tema(con, p["video_id"])
        return redirecionar(form.get("voltar") or "/agenda", msg="Marcado como publicado.")

    # ------------------------------------------------------------ Contas

    @app.get("/contas")
    def contas(request: Request):
        from app.redes import dias_restantes
        from app.redes import instagram as ig
        from app.redes.tunel import cloudflared_instalado
        from app.roteirista.conexao import mascarar

        with conexao() as con:
            cs = {r["plataforma"]: r for r in con.execute("SELECT * FROM conta")}
            teste = json.loads((con.execute("SELECT valor FROM ajuste WHERE chave = 'ig_teste'").fetchone() or ["null"])[0])
        cred = ig.credenciais()
        return pagina(request, "contas.html", "contas", cs=cs, cred=cred, mascarar=mascarar,
                      ig_configurado=ig.configurado(), cloudflared=cloudflared_instalado(), teste=teste,
                      dias_ig=dias_restantes(cs["instagram"]["expira_em"]) if "instagram" in cs else None,
                      redirect_padrao=ig.REDIRECT_PADRAO, escopos=ig.ESCOPOS)

    @app.post("/contas/instagram/credenciais")
    async def ig_credenciais(request: Request):
        from app.redes.instagram import ENV
        from app.roteirista.conexao import salvar_no_env

        form = await request.form()
        for campo, chave in ENV.items():
            valor = (form.get(campo) or "").strip()
            if valor or campo == "redirect":
                if campo == "secret" and not valor:
                    continue
                salvar_no_env(chave, valor)
        return redirecionar("/contas", msg="Credenciais do app do Instagram salvas no .env.")

    @app.get("/contas/instagram/conectar")
    def ig_conectar():
        from app.redes import instagram as ig

        if not ig.configurado():
            return redirecionar("/contas", erro="Preencha o App ID e o App Secret do Instagram primeiro.")
        state = ig.novo_state()
        with conexao() as con:
            con.execute("INSERT INTO ajuste (chave, valor) VALUES ('ig_state', ?) ON CONFLICT(chave) DO UPDATE "
                        "SET valor = excluded.valor", (state,))
        return RedirectResponse(ig.url_autorizacao(state), status_code=303)

    def _finalizar_conexao(texto: str):
        from app.redes import instagram as ig
        from app.redes import salvar_conta

        try:
            codigo, state = ig.extrair_codigo(texto)
            with conexao() as con:
                esperado = (con.execute("SELECT valor FROM ajuste WHERE chave = 'ig_state'").fetchone() or [None])[0]
                if state and esperado and state != esperado:
                    return redirecionar("/contas", erro="O 'state' não confere: comece a conexão de novo.")
                dados = ig.conectar(codigo)
                salvar_conta(con, "instagram", dados)
                con.execute("DELETE FROM ajuste WHERE chave = 'ig_state'")
        except Exception as e:
            return redirecionar("/contas", erro=f"Não consegui conectar: {e}")
        return redirecionar("/contas", msg=f"Instagram conectado como @{dados.get('usuario')}.")

    @app.get("/contas/instagram/retorno")
    def ig_retorno(request: Request):
        return _finalizar_conexao(str(request.url))

    @app.post("/contas/instagram/colar")
    async def ig_colar(request: Request):
        form = await request.form()
        return _finalizar_conexao(form.get("url", ""))

    @app.post("/contas/instagram/testar")
    def ig_testar():
        from app.redes import conta
        from app.redes import instagram as ig

        with conexao() as con:
            c = conta(con, "instagram")
            if not c:
                return redirecionar("/contas", erro="Instagram não conectado.")
            try:
                perfil = ig.ler_perfil(c["access_token"])
                lim = ig.limite(c)
                res = {"ok": True, "msg": f"@{perfil.get('username')} ({perfil.get('account_type', '?')}) · "
                                          f"limite {lim['uso']}/{lim['total']} posts em 24 h"}
            except Exception as e:
                res = {"ok": False, "msg": str(e)}
            res["quando"] = time.strftime("%d/%m %H:%M")
            con.execute("INSERT INTO ajuste (chave, valor) VALUES ('ig_teste', ?) ON CONFLICT(chave) DO UPDATE "
                        "SET valor = excluded.valor", (json.dumps(res),))
        return redirecionar("/contas", **({"msg": res["msg"]} if res["ok"] else {"erro": res["msg"]}))

    @app.post("/contas/instagram/renovar")
    def ig_renovar():
        from app.redes import conta, salvar_conta
        from app.redes import instagram as ig

        with conexao() as con:
            c = conta(con, "instagram")
            if not c:
                return redirecionar("/contas", erro="Instagram não conectado.")
            try:
                salvar_conta(con, "instagram", ig.renovar(c["access_token"]))
            except Exception as e:
                return redirecionar("/contas", erro=f"Não renovou: {e}")
        return redirecionar("/contas", msg="Token do Instagram renovado.")

    @app.post("/contas/{plataforma}/desconectar")
    def conta_desconectar(plataforma: str):
        from app.redes import desconectar

        with conexao() as con:
            desconectar(con, plataforma)
        return redirecionar("/contas", msg="Conta desconectada (token apagado do banco local).")

    # ------------------------------------------------------------ páginas públicas (revisão dos apps)

    @app.get("/termos")
    def termos(request: Request):
        return templates.TemplateResponse(request, "legal.html", {"tipo": "termos", "contato": os.environ.get("CONTATO_EMAIL", "")})

    @app.get("/privacidade")
    def privacidade(request: Request):
        return templates.TemplateResponse(request, "legal.html", {"tipo": "privacidade", "contato": os.environ.get("CONTATO_EMAIL", "")})
