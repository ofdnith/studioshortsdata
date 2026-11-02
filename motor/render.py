"""Render: quadro a quadro com skia, uma seção (corrida) por MP4, junção e áudio."""

import json
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

import skia

from motor import estilo as E
from motor.cenas import CENAS
from motor.linha_do_tempo import FADE, Contexto, Corrida, eh_carimbo, montar, novas_cenas
from motor.narracao import Cronograma, narrar
from motor.roteiro import Roteiro

CRF, PRESET = "18", "veryfast"


@dataclass
class Config:
    voz: str = "pm_alex"
    velocidade: float = 1.2


@dataclass
class Resultado:
    mp4: Path
    capa: Path
    previas: list[Path]
    duracao_s: float
    cronograma: Path
    parametros: dict = field(default_factory=dict)


# ---------------------------------------------------------------- quadro

def _titulo(c, t, tt, primeiro_do_video: bool):
    if not tt.titulo:
        return
    t0 = -0.5 if primeiro_do_video else tt.inicio - 0.05
    a, e = E.vis(t, t0, tt.prox - 0.1)
    if a > 0.002:
        E.linhas(c, tt.titulo, E.Y_TITULO + (1 - e) * 26, 84 if len(tt.titulo) > 1 else 88, alpha=a)


def _fonte(c, t, corrida: Corrida, roteiro: Roteiro, tts):
    """Rodapé 'Fonte: ...' do trecho atual (contínuo quando a fonte se repete)."""
    for tt in corrida.trechos:
        f = roteiro.fonte(tt.fonte_id)
        if not f:
            continue
        ant = tts[tt.indice - 1] if tt.indice > 0 else None
        prox = tts[tt.indice + 1] if tt.indice + 1 < len(tts) else None
        mesma_ant = ant is not None and ant.fonte_id == tt.fonte_id and ant in corrida.trechos
        mesma_prox = prox is not None and prox.fonte_id == tt.fonte_id and prox in corrida.trechos
        t0 = -9 if (mesma_ant or tt.indice == 0) else tt.inicio - 0.1
        t1 = None if (mesma_prox or prox is None) else tt.prox - 0.1
        a, _ = E.vis(t, t0, t1, 0.25, 0.2)
        if a > 0.002:
            texto = f.rodape if f.rodape.lower().startswith("fonte") else f"Fonte: {f.rodape}"
            fo = E.font("SemiBold", 26)
            tam = 26
            while fo.measureText(texto) > 900 and tam > 14:
                tam -= 1
                fo = E.font("SemiBold", tam)
            tw = fo.measureText(texto)
            c.drawString(texto, E.W / 2 - tw / 2, E.Y_FONTE, fo, E.paint(E.CINZA, a * 0.95))


def _carimbo(c, t, tt):
    k = E.ease_out((t - (tt.inicio + 0.6)) / 0.3)
    if k <= 0:
        return
    txt = E.sem_marcas(tt.cena.texto).upper()
    c.save()
    c.translate(E.W / 2, 1060)
    c.rotate(-12)
    s = 1.6 - 0.6 * E.back_out((t - (tt.inicio + 0.6)) / 0.3)
    c.scale(s, s)
    tam = 150
    f = E.font("Black", tam)
    while f.measureText(txt) > 760 and tam > 40:
        tam -= 4
        f = E.font("Black", tam)
    tw = f.measureText(txt)
    r = skia.Rect.MakeXYWH(-tw / 2 - 40, -tam * 0.83, tw + 80, tam * 1.13)
    c.drawRRect(skia.RRect.MakeRectXY(r, 20, 20), E.paint(E.FUNDO, 0.75 * k))
    c.drawRRect(skia.RRect.MakeRectXY(r, 20, 20), E.paint(E.VERMELHO, k, stroke=10))
    c.drawString(txt, -tw / 2, tam * 0.08, f, E.paint(E.VERMELHO, k))
    c.restore()


class Quadros:
    def __init__(self, roteiro: Roteiro, cron: Cronograma):
        self.roteiro = roteiro
        self.cron = cron
        self.tts, self.corridas = montar(roteiro, cron)
        self.fundo = E.fazer_fundo()
        self.surf = skia.Surface.MakeRaster(E.INFO)

    def corrida_em(self, t: float) -> int:
        for k, cr in enumerate(self.corridas):
            if cr.ini <= t < cr.fim:
                return k
        return len(self.corridas) - 1

    def desenhar(self, t: float) -> skia.Surface:
        c = self.surf.getCanvas()
        c.drawImage(self.fundo, 0, 0)
        k = self.corrida_em(t)
        cr = self.corridas[k]
        ultima = k == len(self.corridas) - 1
        fin = 1.0 if k == 0 else E.ease_io((t - cr.ini) / FADE)
        fout = 1.0 if ultima else 1 - E.ease_io((t - (cr.fim - FADE)) / FADE)
        al = min(fin, fout)
        if al < 0.999:
            c.saveLayerAlpha(None, int(255 * al))
        ctx = Contexto(t, cr, self.roteiro)
        CENAS[cr.cena_base.tipo](c, ctx)
        for tt in cr.trechos:
            if eh_carimbo(tt.cena):
                _carimbo(c, t, tt)
        for tt in cr.trechos:
            _titulo(c, t, tt, tt.indice == 0)
        _fonte(c, t, cr, self.roteiro, self.tts)
        if al < 0.999:
            c.restore()
        return self.surf

    def png(self, t: float, caminho: Path):
        self.desenhar(t).makeImageSnapshot().save(str(caminho), skia.kPNG)


# ---------------------------------------------------------------- vídeo

def _ffmpeg_entrada(destino: Path):
    return subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba",
         "-s", f"{E.W}x{E.H}", "-r", str(E.FPS), "-i", "-",
         "-c:v", "libx264", "-preset", PRESET, "-crf", CRF, "-pix_fmt", "yuv420p",
         "-r", str(E.FPS), "-f", "mp4", str(destino)],
        stdin=subprocess.PIPE, stderr=subprocess.PIPE)


def tempos_previa(q: Quadros) -> list[float]:
    """4 instantes representativos: trechos em 20%, 40%, 60% e 85% do vídeo."""
    res = []
    for frac in (0.2, 0.4, 0.6, 0.85):
        alvo = q.cron.total * frac
        tt = min(q.tts, key=lambda x: abs((x.inicio + x.fim) / 2 - alvo))
        # fim do trecho: as animações já terminaram e o título ainda está na tela
        res.append(round(max(tt.inicio + 0.5, min(tt.fim - 0.25, tt.prox - 0.45)), 2))
    return res


def renderizar(roteiro: Roteiro, saida: Path, config: Config = Config(), pasta: Path | None = None,
               progresso=None, log=print) -> Resultado:
    """Gera MP4 + capa + 4 prévias. `progresso(fracao)` é chamado durante o render."""
    saida = Path(saida)
    pasta = Path(pasta) if pasta else saida.parent / (saida.stem + "_trabalho")
    pasta.mkdir(parents=True, exist_ok=True)
    inicio = time.time()
    progresso = progresso or (lambda f: None)

    # 1. narração primeiro
    cron, wav = narrar([t.fala for t in roteiro.trechos], novas_cenas(roteiro),
                       config.voz, config.velocidade, pasta, log=log)
    log(f"narração: {cron.total:.1f} s, {len(cron.trechos)} trechos")
    progresso(0.05)

    # 2. quadros, uma seção por corrida
    q = Quadros(roteiro, cron)
    n_total = round(cron.total * E.FPS)
    cortes = [round(cr.ini * E.FPS) for cr in q.corridas] + [n_total]
    nomes, feitos = [], 0
    for k in range(len(q.corridas)):
        nome = f"secao{k:02d}.mp4"
        tmp, final = pasta / (nome + ".part"), pasta / nome
        p = _ffmpeg_entrada(tmp)
        for n in range(cortes[k], cortes[k + 1]):
            p.stdin.write(q.desenhar(n / E.FPS).makeImageSnapshot().tobytes())
            feitos += 1
            if feitos % 30 == 0:
                progresso(0.05 + 0.9 * feitos / n_total)
        p.stdin.close()
        if p.wait() != 0:
            raise RuntimeError(f"FFmpeg falhou na seção {k}: {p.stderr.read().decode()[-500:]}")
        tmp.replace(final)   # só renomeia quando terminou com sucesso
        nomes.append(nome)
        log(f"seção {k + 1}/{len(q.corridas)} ok ({q.corridas[k].cena_base.tipo})")

    # 3. junção (concat demuxer, -c copy) e áudio por último (-c:v copy)
    lista = pasta / "lista.txt"
    lista.write_text("".join(f"file '{n}'\n" for n in nomes))
    saida.parent.mkdir(parents=True, exist_ok=True)
    tmp = saida.with_name(saida.stem + ".part.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lista),
                    "-i", str(wav), "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(tmp)], check=True)
    tmp.replace(saida)

    # 4. capa (primeiro quadro) e 4 prévias
    capa = saida.with_name(saida.stem + "_capa.png")
    q.png(0.0, capa)
    previas = []
    for i, t in enumerate(tempos_previa(q), 1):
        p_ = saida.with_name(f"{saida.stem}_previa{i}.png")
        q.png(t, p_)
        previas.append(p_)
    progresso(1.0)
    log(f"pronto: {saida} ({cron.total:.1f} s) em {time.time() - inicio:.0f} s")
    params = {"voz": config.voz, "velocidade": config.velocidade, "duracao_s": cron.total,
              "crf": CRF, "preset": PRESET, "fps": E.FPS}
    (pasta / "parametros.json").write_text(json.dumps(params, ensure_ascii=False, indent=1))
    return Resultado(saida, capa, previas, cron.total, pasta / "cronograma.json", params)


def previa(roteiro: Roteiro, tempos: list[float], pasta: Path, config: Config = Config(),
           log=print) -> list[Path]:
    """Gera só PNGs (usa a narração, em cache) para conferir quadros."""
    pasta.mkdir(parents=True, exist_ok=True)
    cron, _ = narrar([t.fala for t in roteiro.trechos], novas_cenas(roteiro),
                     config.voz, config.velocidade, pasta, log=lambda *_: None)
    q = Quadros(roteiro, cron)
    res = []
    for t in tempos:
        p = pasta / f"t{t:05.1f}.png"
        q.png(t, p)
        res.append(p)
        log(str(p))
    return res
