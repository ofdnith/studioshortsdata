"""Narração primeiro: gera cada trecho com Kokoro, corta silêncios, mede e monta o cronograma.

Cada trecho fica em cache (pasta `cache/`, chave = voz + velocidade + texto), então editar
um trecho só regenera aquele áudio.
"""

import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import soundfile as sf

RAIZ = Path(__file__).resolve().parent.parent
MODELO = RAIZ / "models" / "kokoro-v1.0.onnx"
VOZES = RAIZ / "models" / "voices-v1.0.bin"
CACHE_PADRAO = RAIZ / "storage" / "cache_voz"

SR = 24000
PAUSA_INICIAL, PAUSA_MESMA_CENA, PAUSA_NOVA_CENA, CAUDA = 0.10, 0.15, 0.35, 1.4
LIMIAR = 0.01            # amplitude considerada silêncio
MARGEM_ANTES, MARGEM_DEPOIS = 400, 1500   # amostras mantidas nas pontas

_kokoro = None


def kokoro():
    global _kokoro
    if _kokoro is None:
        if not MODELO.exists() or not VOZES.exists():
            raise FileNotFoundError("Modelos do Kokoro não encontrados. Rode ./scripts/baixar_modelos.sh")
        from kokoro_onnx import Kokoro
        _kokoro = Kokoro(str(MODELO), str(VOZES))
    return _kokoro


def sintetizar(texto: str, voz: str, velocidade: float, cache: Path = CACHE_PADRAO) -> np.ndarray:
    """Áudio (float32, 24 kHz) de um trecho, sem silêncio nas pontas."""
    chave = hashlib.sha1(f"{voz}|{velocidade:.3f}|{texto}".encode()).hexdigest()[:16]
    arq = cache / f"{chave}.wav"
    if arq.exists():
        a, _ = sf.read(arq, dtype="float32")
        return a
    a, sr = kokoro().create(texto, voice=voz, speed=velocidade, lang="pt-br")
    assert sr == SR, sr
    idx = np.where(np.abs(a) > LIMIAR)[0]
    if len(idx):
        a = a[max(0, idx[0] - MARGEM_ANTES): idx[-1] + MARGEM_DEPOIS]
    cache.mkdir(parents=True, exist_ok=True)
    sf.write(arq, a, SR)
    return a.astype(np.float32)


ALVO = "I=-15:TP=-1.5:LRA=11"


def normalizar(entrada: Path, saida: Path):
    """Loudnorm em duas passadas (mede, depois aplica) para chegar perto de -15 LUFS."""
    med = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(entrada), "-af",
                          f"loudnorm={ALVO}:print_format=json", "-f", "null", "-"],
                         capture_output=True, text=True, check=True).stderr
    m = json.loads(med[med.rindex("{"):med.rindex("}") + 1])
    filtro = (f"loudnorm={ALVO}:measured_I={m['input_i']}:measured_TP={m['input_tp']}"
              f":measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}"
              f":offset={m['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(entrada), "-af", filtro,
                    "-ar", "48000", "-ac", "2", str(saida)], check=True)


@dataclass
class Marca:
    inicio: float
    fim: float
    texto: str


@dataclass
class Cronograma:
    total: float
    trechos: list[Marca]

    def salvar(self, caminho: Path):
        caminho.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=1), encoding="utf-8")


def narrar(falas: list[str], novas_cenas: list[bool], voz: str, velocidade: float, pasta: Path,
           cache: Path = CACHE_PADRAO, log=print) -> tuple[Cronograma, Path]:
    """Gera narracao.wav (normalizada, 48 kHz estéreo) e o cronograma em `pasta`.

    novas_cenas[i] = True quando o trecho i começa uma cena nova (pausa maior antes).
    """
    pasta.mkdir(parents=True, exist_ok=True)
    t, marcas, clipes = 0.0, [], []
    for i, (fala, nova) in enumerate(zip(falas, novas_cenas)):
        log(f"voz: trecho {i + 1}/{len(falas)}")
        a = sintetizar(fala, voz, velocidade, cache)
        t += PAUSA_INICIAL if i == 0 else (PAUSA_NOVA_CENA if nova else PAUSA_MESMA_CENA)
        d = len(a) / SR
        marcas.append(Marca(round(t, 3), round(t + d, 3), fala))
        clipes.append(a)
        t += d
    total = round(t + CAUDA, 2)
    mix = np.zeros(int(total * SR) + 1, np.float32)
    for m, a in zip(marcas, clipes):
        i = int(m.inicio * SR)
        mix[i:i + len(a)] += a
    bruto = pasta / "narracao_bruta.wav"
    sf.write(bruto, mix, SR)
    final = pasta / "narracao.wav"
    normalizar(bruto, final)
    cron = Cronograma(total, marcas)
    cron.salvar(pasta / "cronograma.json")
    return cron, final


def amostra(voz: str, velocidade: float, destino: Path,
            texto: str = "Olá! Esta é a voz que vai narrar as curiosidades de dados deste vídeo.") -> Path:
    """MP3 curto para ouvir a voz (botão 'Ouvir amostra')."""
    a = sintetizar(texto, voz, velocidade)
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_suffix(".tmp.wav")
    sf.write(tmp, a, SR)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp),
                    "-af", "loudnorm=I=-15:TP=-1.5", "-b:a", "128k", str(destino)], check=True)
    tmp.unlink()
    return destino
