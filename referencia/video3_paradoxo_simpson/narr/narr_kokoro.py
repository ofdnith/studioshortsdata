import sys, json, numpy as np, soundfile as sf
from kokoro_onnx import Kokoro
K = '/tmp/claude-0/kok/'
KK = Kokoro(K + 'kokoro.onnx', K + 'voices.bin')
SP = float(sys.argv[1]) if len(sys.argv) > 1 else 1.1
VOICE = sys.argv[2] if len(sys.argv) > 2 else 'pm_alex'
SEG = [
 ("A1", 0.10, "Em mil novecentos e setenta e três, a Universidade de Bérqueli parecia discriminar mulheres."),
 ("A2", 0.18, "Nos seis maiores departamentos, quarenta e cinco por cento dos homens foram aprovados. Das mulheres, só trinta."),
 ("A3", 0.15, "Caso encerrado? Não."),
 ("B1", 0.35, "Quando separaram os dados por departamento, a história virou."),
 ("B2", 0.15, "Em quatro dos seis, as mulheres tinham taxa de aprovação maior que a dos homens."),
 ("B3", 0.12, "No departamento A: oitenta e dois por cento contra sessenta e dois."),
 ("C1", 0.30, "Então por que o total diz o contrário? Por causa de onde cada grupo se candidatou."),
 ("C2", 0.15, "Metade dos homens tentou os dois departamentos mais fáceis."),
 ("C3", 0.15, "Já noventa e três por cento das mulheres foram para os quatro mais concorridos."),
 ("D1", 0.35, "Isso é o paradoxo de Simpsom: uma tendência que aparece em cada grupo se inverte quando você junta tudo."),
 ("D2", 0.15, "O culpado é uma variável escondida. Aqui, o departamento."),
 ("E1", 0.35, "Na medicina também: num estudo sobre pedras nos rins, o tratamento A venceu nas pedras pequenas e nas grandes."),
 ("E2", 0.15, "Mas no total, o tratamento B parecia melhor: oitenta e três contra setenta e oito por cento."),
 ("E3", 0.15, "O motivo? O tratamento A era usado justamente nos casos mais difíceis."),
 ("F1", 0.35, "A lição: antes de confiar num número agregado, pergunte que variável pode estar escondida."),
 ("F2", 0.18, "Siga para mais curiosidades de dados."),
]
sr = 24000
t = 0.0; sched = []; clips = {}
for sid, gap, text in SEG:
    a, _ = KK.create(text, voice=VOICE, speed=SP, lang='pt-br')
    idx = np.where(np.abs(a) > 0.01)[0]; a = a[max(0, idx[0] - 400): idx[-1] + 1500]
    t += gap; sched.append({"id": sid, "start": round(t, 3), "end": round(t + len(a) / sr, 3), "text": text}); clips[sid] = a; t += len(a) / sr
total = t + 1.4
mix = np.zeros(int(total * sr) + 1, np.float32)
for s in sched: i = int(s["start"] * sr); mix[i:i + len(clips[s["id"]])] += clips[s["id"]]
sf.write('/home/claude/video3/narr/narracao_raw.wav', mix, sr)
json.dump({"total": round(total, 2), "seg": sched}, open('/home/claude/video3/narr/sched.json', 'w'), ensure_ascii=False, indent=1)
for s in sched: print(f'{s["id"]} {s["start"]:6.2f}-{s["end"]:6.2f}')
print("TOTAL", round(total, 2))
