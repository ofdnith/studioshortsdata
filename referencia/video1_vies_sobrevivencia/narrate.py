import sys, json, soundfile as sf
from kokoro_onnx import Kokoro
K = '/tmp/claude-0/kok/'
k = Kokoro(K + 'kokoro.onnx', K + 'voices.bin')
VOICE = sys.argv[1] if len(sys.argv) > 1 else 'pm_alex'
SPEED = float(sys.argv[2]) if len(sys.argv) > 2 else 1.05
LINES = [
 "Na Segunda Guerra, quase blindaram os aviões no lugar errado.",
 "Os aviões voltavam das missões cheios de buracos de bala. Nas asas, na fuselagem, na cauda.",
 "A ideia óbvia era reforçar a blindagem justamente onde tinha mais buracos.",
 "Mas o estatístico Abraham Vald disse: esperem. Onde estão os buracos dos aviões que não voltaram?",
 "Pense em todos os aviões que partiram. Os que levaram tiro no motor ou na cabine caíram, e nunca entraram na conta. Os dados só mostravam quem sobreviveu.",
 "Então, a blindagem tinha que ir onde não havia buracos. Um tiro ali derrubava o avião.",
 "Isso é o viés de sobrevivência: concluir algo olhando só para quem passou pelo filtro. Como analisar só os clientes que ficaram, as estartáps que deram certo, ou quem respondeu a pesquisa.",
 "Então, antes de olhar os dados, pergunte: quem ficou de fora? Siga para mais curiosidades de dados.",
]
if '--ph' in sys.argv:
    for l in LINES: print(k.tokenizer.phonemize(l, 'pt-br'))
    sys.exit()
out = {}
for i, l in enumerate(LINES):
    a, sr = k.create(l, voice=VOICE, speed=SPEED, lang='pt-br')
    p = f'/home/claude/video/narr/s{i+1}.wav'; sf.write(p, a, sr); out[i+1] = round(len(a) / sr, 2)
print(json.dumps(out))
