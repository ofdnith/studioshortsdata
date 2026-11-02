"""Trilha de fundo e efeitos gerados por código (sem direitos autorais).

- `trilha_ambiente`: pad suave (Lá menor – Fá – Dó – Sol) com um arpejo leve, em loop.
- `whoosh`: sopro curto de ruído filtrado para as trocas de cena.
- `abaixar_sob_voz`: ducking — a trilha abaixa sozinha quando a voz fala.
"""

import numpy as np
from scipy.signal import butter, lfilter

NOTAS = {"A2": 110.0, "C3": 130.81, "D3": 146.83, "E3": 164.81, "F2": 87.31, "F3": 174.61, "G2": 98.0,
         "G3": 196.0, "A3": 220.0, "B3": 246.94, "C4": 261.63, "D4": 293.66, "E4": 329.63, "G4": 392.0,
         "A4": 440.0, "B4": 493.88, "C5": 523.25, "E5": 659.25}
ACORDES = [("A2", ["A3", "C4", "E4"], ["A4", "C5", "E5", "C5"]),
           ("F2", ["F3", "A3", "C4"], ["A4", "C5", "A4", "F3"]),
           ("C3", ["C4", "E4", "G4"], ["G4", "C5", "E5", "C5"]),
           ("G2", ["G3", "B3", "D4"], ["G4", "B4", "D4", "B4"])]
DUR_ACORDE = 4.0     # s (BPM 120 → 2 compassos de 4/4 por acorde... mais calmo: 1 acorde a cada 4 s)


def _lowpass(x, corte, sr, ordem=2):
    b, a = butter(ordem, corte / (sr / 2), "low")
    return lfilter(b, a, x)


def trilha_ambiente(duracao: float, sr: int = 24000, semente: int = 3) -> np.ndarray:
    n = int(duracao * sr) + 1
    t = np.arange(n) / sr
    pad = np.zeros(n)
    arp = np.zeros(n)
    rng = np.random.default_rng(semente)
    n_acordes = int(np.ceil(duracao / DUR_ACORDE)) + 1
    for k in range(n_acordes):
        baixo, notas, arpejo = ACORDES[k % len(ACORDES)]
        ini, fim = k * DUR_ACORDE - 0.6, (k + 1) * DUR_ACORDE + 0.6   # sobreposição: troca suave
        i0, i1 = max(0, int(ini * sr)), min(n, int(fim * sr))
        if i0 >= i1:
            continue
        tt = t[i0:i1] - ini
        env = np.clip(tt / 1.0, 0, 1) * np.clip((fim - ini - tt) / 1.0, 0, 1)   # ataque/soltura de 1 s
        for nome in notas:
            f = NOTAS[nome]
            for desafino in (-0.15, 0.0, 0.15):   # leve coro
                pad[i0:i1] += env * np.sin(2 * np.pi * (f + desafino) * tt + rng.uniform(0, 6.28)) / 9
        f = NOTAS[baixo]
        pad[i0:i1] += env * 0.5 * np.sin(2 * np.pi * f * tt)
        # arpejo: 8 notas por acorde, cada uma com decaimento exponencial (som de "pluck" suave)
        passo = DUR_ACORDE / 8
        for j in range(8):
            ts = k * DUR_ACORDE + j * passo
            j0 = int(ts * sr)
            if j0 >= n:
                break
            tam = min(n - j0, int(1.2 * sr))
            tn = np.arange(tam) / sr
            fn = NOTAS[arpejo[j % len(arpejo)]]
            nota = np.sin(2 * np.pi * fn * tn) * np.exp(-tn * 4.0) * (0.9 if j % 2 == 0 else 0.6)
            arp[j0:j0 + tam] += nota
    sinal = _lowpass(pad, 1800, sr) + 0.35 * _lowpass(arp, 3000, sr)
    sinal *= 1 + 0.08 * np.sin(2 * np.pi * 0.07 * t)          # respiração lenta
    sinal[: int(1.5 * sr)] *= np.linspace(0, 1, int(1.5 * sr))  # fade in
    fo = int(2.0 * sr)
    sinal[-fo:] *= np.linspace(1, 0, fo)                       # fade out
    return (sinal / (np.max(np.abs(sinal)) + 1e-9)).astype(np.float32)


def whoosh(sr: int = 24000, dur: float = 0.45, semente: int = 0) -> np.ndarray:
    """Sopro curto e grave (ruído filtrado), discreto: marca a troca de cena sem chamar atenção."""
    rng = np.random.default_rng(semente)
    n = int(dur * sr)
    ruido = rng.standard_normal(n)
    grave = _lowpass(ruido, 350, sr)
    medio = _lowpass(ruido, 1400, sr)
    k = np.linspace(0, 1, n)
    sinal = grave * (1 - k) + medio * k
    env = np.sin(np.pi * k) ** 3     # ataque e saída bem suaves
    s = sinal * env
    return (s / (np.max(np.abs(s)) + 1e-9)).astype(np.float32)


def envelope(voz: np.ndarray, sr: int, ataque: float = 0.05, soltura: float = 0.35) -> np.ndarray:
    """Envelope suavizado da voz: sobe rápido (máximo em janela) e desce devagar (filtro de 1 polo)."""
    from scipy.ndimage import maximum_filter1d
    janela = int(0.03 * sr)
    pot = np.sqrt(np.convolve(voz.astype(np.float64) ** 2, np.ones(janela) / janela, mode="same"))
    pot = maximum_filter1d(pot, size=max(1, int(ataque * sr)))
    a = np.exp(-1 / (soltura * sr))
    return lfilter([1 - a], [1, -a], pot)


def abaixar_sob_voz(trilha: np.ndarray, voz: np.ndarray, sr: int, reducao: float = 0.6) -> np.ndarray:
    env = envelope(voz[: len(trilha)], sr)
    env = env / (np.percentile(env[env > 0], 90) + 1e-9) if np.any(env > 0) else env
    ganho = 1 - reducao * np.clip(env, 0, 1)
    return trilha * ganho


def db(x: float) -> float:
    return 10 ** (x / 20)
