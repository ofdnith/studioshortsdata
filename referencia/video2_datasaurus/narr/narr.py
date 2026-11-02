"""Gera a narração. Cada trecho: (id, pausa_antes, texto). Saída: clips + sched.json"""
import sys, json, numpy as np, soundfile as sf
from kokoro_onnx import Kokoro
K = '/tmp/claude-0/kok/'
k = Kokoro(K + 'kokoro.onnx', K + 'voices.bin')
SPEED = float(sys.argv[1]) if len(sys.argv) > 1 else 1.12
SEG = [
 ("A1", 0.10, "Um dinossauro e uma estrela."),
 ("A2", 0.15, "Mesma média, mesmo desvio padrão, mesma correlação."),
 ("A3", 0.20, "Como gráficos tão diferentes podem ter os mesmos números?"),
 ("B1", 0.35, "Em mil novecentos e setenta e três, o estatístico Francis Ânscom criou quatro conjuntos de dados, com onze pontos cada."),
 ("B2", 0.20, "Nos quatro, a média de x é nove, a de y é sete e meio, e a correlação é zero vírgula oitenta e dois."),
 ("B3", 0.15, "Até a reta de regressão é idêntica."),
 ("B4", 0.20, "Mas olhe os gráficos. O primeiro é uma relação linear com ruído."),
 ("B5", 0.12, "O segundo é uma curva."),
 ("B6", 0.12, "No terceiro, um único ponto fora da curva entorta a reta."),
 ("B7", 0.12, "E no quarto, um ponto sozinho cria uma correlação que não existe."),
 ("C1", 0.35, "Em dois mil e dezessete, Justin Matêika e Djórdji Fits-móris, da Autodésk, levaram isso ao extremo."),
 ("C2", 0.18, "Partiram de um dinossauro de pontos e moveram cada ponto um pouquinho, milhares de vezes, aceitando só as mudanças que mantinham as estatísticas."),
 ("C3", 0.18, "Assim nasceu o Datassáurus: treze gráficos completamente diferentes, com as mesmas estatísticas até a segunda casa decimal."),
 ("C4", 0.12, "Estrela, círculo, alvo, xis, linhas, e o que mais você imaginar."),
 ("D1", 0.35, "A lição? Média e correlação não contam a história inteira. Resumos escondem a forma dos dados."),
 ("D2", 0.18, "Antes de calcular qualquer coisa, desenhe seus dados."),
 ("D3", 0.18, "Siga para mais curiosidades de dados."),
]
if '--ph' in sys.argv:
    for i, _, l in SEG: print(i, k.tokenizer.phonemize(l, 'pt-br'))
    sys.exit()
clips = {}; t = 0.0; sched = []
for sid, gap, text in SEG:
    a, sr = k.create(text, voice='pm_alex', speed=SPEED, lang='pt-br')
    idx = np.where(np.abs(a) > 0.01)[0]; a = a[max(0, idx[0] - 500): idx[-1] + 1800]
    t += gap; d = len(a) / sr
    sched.append({"id": sid, "start": round(t, 3), "end": round(t + d, 3), "text": text})
    clips[sid] = a; t += d
total = t + 1.4
mix = np.zeros(int(total * sr) + 1, np.float32)
for s in sched:
    a = clips[s["id"]]; i = int(s["start"] * sr); mix[i:i + len(a)] += a
sf.write('/home/claude/video2/narr/narracao_raw.wav', mix, sr)
json.dump({"total": round(total, 2), "seg": sched}, open('/home/claude/video2/narr/sched.json', 'w'), ensure_ascii=False, indent=1)
for s in sched: print(f'{s["id"]} {s["start"]:6.2f}-{s["end"]:6.2f}')
print("TOTAL", round(total, 2))
