# Código de referência dos três primeiros vídeos

Scripts usados para gerar os vídeos à mão, antes da plataforma. Servem de base para o
`motor/` (ver PROMPT.md, fase 3). Não são código de produção: têm caminhos absolutos do
ambiente onde foram escritos (`/home/claude/...`, `/tmp/claude-0/kok/` para o modelo Kokoro)
e uma cena programada à mão por vídeo.

| Pasta | Vídeo | O que vale reaproveitar |
| --- | --- | --- |
| `video1_vies_sobrevivencia/` | Viés de sobrevivência (70 s) | Primeira versão; narração adicionada depois (`build_audio.py`) |
| `video2_datasaurus/` | Datasaurus + Quarteto de Anscombe (70 s) | Helpers de texto, painéis, gráfico de pontos com morph (matching húngaro), painel de estatísticas, fluxo "narração primeiro" (`narr/narr.py` gera `sched.json`), render por seção + concat |
| `video3_paradoxo_simpson/` | Paradoxo de Simpson (69 s) | Barras, barras pareadas, barra empilhada, tabela, diagrama causal, caricatura genérica (`caricature`, com `older=True`), silhueta neutra, ilustração de lugar (Berkeley + mapa da Califórnia), linha de fonte no rodapé |

## Como os vídeos foram feitos
1. `narr/*.py` gera cada trecho da fala com Kokoro (`pm_alex`, velocidade 1,2), corta
   silêncios, grava `sched.json` (início/fim de cada trecho) e `narracao_raw.wav`.
2. Normalização: `ffmpeg -i narracao_raw.wav -af loudnorm=I=-15:TP=-1.5:LRA=11 -ar 48000 -ac 2 narracao.wav`.
3. `make_videoN.py preview T1 T2 ...` gera quadros PNG para conferir; `make_videoN.py render`
   gera uma seção por MP4 e junta tudo com o áudio.

## Dados
- `DatasaurusDozen.tsv`: Matejka & Fitzmaurice (2017), ACM CHI. https://doi.org/10.1145/3025453.3025912
- `anscombe.csv`: Anscombe (1973), The American Statistician. https://doi.org/10.1080/00031305.1973.10478966
- `ucb.csv` (UCBAdmissions): Bickel, Hammel & O'Connell (1975), Science. https://doi.org/10.1126/science.187.4175.398
