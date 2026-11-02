import sys, json, numpy as np, soundfile as sf
from kokoro_onnx import Kokoro
K = '/tmp/claude-0/kok/'
k = Kokoro(K + 'kokoro.onnx', K + 'voices.bin')
VOICE, SPEED = 'pm_alex', 1.0
SEG = [
 (0.15, "Na Segunda Guerra, quase blindaram os aviões no lugar errado."),
 (4.40, "Os aviões voltavam das missões cheios de buracos de bala. Nas asas, na fuselagem, na cauda."),
 (12.30, "A ideia óbvia era reforçar a blindagem justamente onde tinha mais buracos."),
 (20.30, "Mas o estatístico Abraham Vald disse: esperem."),
 (24.10, "Onde estão os buracos dos aviões que não voltaram?"),
 (30.30, "Pense em todos os aviões que partiram."),
 (33.70, "Os que levaram tiro no motor ou na cabine caíram, e nunca entraram na conta."),
 (39.00, "Os dados só mostravam quem sobreviveu."),
 (42.30, "Então, a blindagem tinha que ir onde não havia buracos."),
 (45.85, "Um tiro ali derrubava o avião."),
 (50.30, "Isso é o viés de sobrevivência: concluir algo olhando só para quem passou pelo filtro."),
 (None, "Como analisar só os clientes que ficaram,"),
 (None, "as estartáps que deram certo,"),
 (None, "ou quem respondeu a pesquisa."),
 (62.30, "Então, antes de olhar os dados, pergunte: quem ficou de fora?"),
 (None, "Siga para mais curiosidades de dados."),
]
TOTAL = 70.0
clips = []
for st, text in SEG:
    a, sr = k.create(text, voice=VOICE, speed=SPEED, lang='pt-br')
    # corta silêncio do início/fim
    idx = np.where(np.abs(a) > 0.01)[0]; a = a[max(0, idx[0] - 600): idx[-1] + 2400]
    clips.append([st, a, text])
# encadeia os sem horário fixo logo após o anterior (pausa curta)
t = 0
for c in clips:
    if c[0] is None: c[0] = t + 0.25
    t = c[0] + len(c[1]) / sr
mix = np.zeros(int(TOTAL * sr), np.float32)
sched = []
for st, a, text in clips:
    i = int(st * sr); mix[i:i + len(a)] += a[: len(mix) - i]
    sched.append((round(st, 2), round(st + len(a) / sr, 2), text[:40]))
sf.write('/home/claude/video/narr/narracao_raw.wav', mix, sr)
prev = 0
for s, e, tx in sched:
    print(f"{s:6.2f}-{e:6.2f} {'OVERLAP' if s < prev else ''} {tx}"); prev = e
json.dump(sched, open('/home/claude/video/narr/sched.json', 'w'))
