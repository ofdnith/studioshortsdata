# Estúdio de vídeos curtos: temas, produção e agendamento (Instagram + TikTok)

## Contexto
Produzo vídeos curtos (Reels/TikTok) com curiosidades de ciência de dados, animados por
código e narrados com voz sintética em pt-BR: cerca de 70 s, 1080x1920, 30 fps,
H.264 + AAC. Já fiz três vídeos de forma manual (Viés de sobrevivência, Datasaurus e
Quarteto de Anscombe, Paradoxo de Simpson). O código deles está em `referencia/` e é a
base do motor de renderização.

Quero uma plataforma única, rodando **localmente no meu Mac**, com três abas:
1. **Temas:** uma lista enorme de temas (dados agora, outros assuntos depois).
2. **Produção:** transformar um tema em vídeo (roteiro pela API do Claude, revisão,
   narração, renderização, aprovação).
3. **Agenda:** biblioteca de vídeos aprovados e agendamento do envio para Instagram e TikTok.

Os vídeos vão para contas **novas, dedicadas ao canal** (um Instagram e um TikTok). As
contas de desenvolvedor (Meta e TikTok for Developers) são as minhas pessoais.

## Regras de trabalho
- Fale comigo em português.
- Rodar localmente com recarregamento automático, vendo cada mudança enquanto você edita.
  Pode instalar o que for necessário, mas diga antes o que vai instalar e por quê.
- Trabalhe em incrementos pequenos. A cada um, diga o que mudou e como eu vejo o resultado.
- Segredos nunca vão para o repositório: use `.env` (no `.gitignore`) e um `.env.example`
  sem valores.
- Antes de qualquer ação que publique algo de verdade numa rede social, peça minha confirmação.
- Antes de qualquer chamada à API do Claude feita por você durante o desenvolvimento (não pelo
  app), avise: cada chamada consome créditos.
- Use Git desde o início, com commits pequenos e mensagens claras.

## Ambiente
- macOS, MacBook Air M2. Já tenho VS Code, Node.js LTS, Git e a extensão do Claude Code.
- Sem nuvem por enquanto: nada de Cloudflare, Vercel etc. Tudo roda no Mac.
- Exceção futura: o Instagram baixa o vídeo de uma URL pública e o OAuth exige redirect
  HTTPS. Na fase do Instagram, verifique na documentação oficial se dá para usar upload
  direto (resumable upload) pela Instagram API with Instagram Login; se não der, use um
  túnel temporário (`cloudflared tunnel --url` ou similar) só durante a publicação.

## Stack (justificativa: o motor de render é Python, então uma linguagem só)
- **Backend:** Python 3.12 + FastAPI, `uvicorn --reload`.
- **Banco:** SQLite (um arquivo em `data/estudio.db`), com migrações simples.
- **Interface:** HTML renderizado no servidor (Jinja2) + HTMX para interações + CSS próprio,
  leve. Sem framework de frontend pesado. Tema escuro, igual à identidade dos vídeos.
- **Trabalhos em segundo plano:** um processo `worker` separado que lê uma tabela de
  trabalhos no SQLite (roteiro, narração, render, publicação) e executa um por vez.
- **Agendamento:** o mesmo worker verifica a cada minuto as publicações vencidas.
- **Arquivos:** `storage/` (MP4, capas, prévias, áudios), fora do Git.
- **Comando único para subir tudo:** `make dev` (ou script equivalente) que sobe o servidor
  e o worker juntos, com logs coloridos.

## Motor de renderização (`motor/`)
Transforme o código de `referencia/` numa biblioteca Python reutilizável + CLI:
`python -m motor render roteiro.json --saida video.mp4`.
- Desenho: `skia-python`. Vídeo: FFmpeg (libx264, CRF 18, preset veryfast, yuv420p, 30 fps).
- Fontes: Inter (empacotada no projeto, em `motor/fontes/`).
- Voz: Kokoro (`kokoro-onnx`), voz **`pm_alex`**, velocidade **1,2**, idioma `pt-br`. Os
  arquivos do modelo (`kokoro-v1.0.onnx` e `voices-v1.0.bin`) vêm dos releases do GitHub
  `thewh1teagle/kokoro-onnx` (tag `model-files-v1.0`) e ficam em `models/`, fora do Git.
  Crie um script que baixa os modelos.
- **Narração primeiro:** gerar cada trecho da fala, cortar os silêncios das pontas, medir a
  duração e montar um cronograma (início e fim de cada trecho). Toda animação é programada a
  partir do início do trecho que ela ilustra. Normalizar o áudio para cerca de -15 LUFS.
- Uma cena por arquivo MP4 temporário, renomeado só quando o FFmpeg termina com sucesso;
  junção com o concat demuxer e `-c copy`; áudio por último com `-c:v copy`.
- Gerar também: capa (primeiro quadro) e 4 quadros de prévia em PNG.
- **Mesmo visual para todos os temas.** Identidade: fundo azul-escuro `#0B1220` com grade de
  pontos sutil e vinheta; texto `#F4F6FB`; cinza `#97A3B8`; destaque amarelo `#FFC145`;
  vermelho `#FF4D5E`; verde `#3DDC97`; painéis `#121B2E`. Títulos ExtraBold, palavras de
  destaque marcadas com `*asteriscos*` no texto.
- Áreas seguras do Reels: conteúdo entre y=250 e y=1550; nada importante no canto inferior
  direito (ícones).
- O primeiro quadro já precisa ter visual (ele vira a capa), nunca só título.

### Catálogo de cenas (o Claude só pode usar estes tipos)
| Tipo | Uso | Referência |
| --- | --- | --- |
| `barras` | Comparar poucos valores, com contagem animada | Homens 45% × Mulheres 30% |
| `barras_pareadas` | Grupos lado a lado, marcando o vencedor | Departamentos A–F |
| `barra_empilhada` | Partes de um todo, com destaque | Onde cada grupo se candidatou |
| `dispersao` | Pontos, com morph entre conjuntos e painel de estatísticas | Datasaurus |
| `grade_graficos` | Vários gráficos pequenos, foco em um por vez | Quarteto de Anscombe |
| `tabela` | Poucos números em linhas e colunas, vencedor destacado | Pedras nos rins |
| `diagrama_causal` | Nós e setas (variável escondida, causa e efeito) | Gênero → departamento → aprovação |
| `pessoa` | Caricatura genérica + cartão com nome, datas e feito | Edward Simpson, Anscombe |
| `lugar` | Ilustração de um lugar, de uma biblioteca de lugares | Torre de Berkeley + mapa |
| `mapa` | Mapa simples com alfinete, quando o lugar não tem ilustração | — |
| `texto_grande` | Frase de impacto ou carimbo | "NÃO", "Esperem." |
| `chamada` | Fechamento com "Siga para mais curiosidades de dados" | — |

Regras das cenas:
- **Pessoas reais:** nunca usar foto. Caricatura genérica com cor de pele e faixa etária da
  pessoa **na época do fato**, sem copiar traços do rosto. Se cor ou idade não forem
  conhecidas com fonte, usar silhueta neutra. Cartão com nome, datas e o que a pessoa fez.
- **Lugares reais:** ilustração desenhada por código (biblioteca que cresce com o uso). Lugar
  sem ilustração cai na cena `mapa`.
- **Fonte na tela:** todo trecho que cita estudo, artigo, base de dados ou número mostra no
  rodapé a fonte oficial ("Fonte: Autores (ano), Revista").

## Roteiro pela API do Claude
- SDK oficial `anthropic` para Python. Chave em `ANTHROPIC_API_KEY` no `.env`.
- Modelo: **`claude-fable-5-1`** (o mais capaz para raciocínio e checagem de fatos),
  configurável em `CLAUDE_MODEL`.
- Use as ferramentas de servidor **web search** e **web fetch** da API para o Claude
  encontrar e abrir as fontes oficiais (artigo, DOI, página da revista, base de dados).
- Use **structured outputs** (JSON schema) para garantir o formato do roteiro. Consulte a
  documentação atual antes de implementar:
  - https://platform.claude.com/docs/en/build-with-claude/structured-outputs
  - https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool
  - https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-fetch-tool
  - https://platform.claude.com/docs/en/build-with-claude/prompt-caching (o prompt de
    sistema com as regras e o catálogo é fixo: cachear)
- Guardar tokens de entrada e saída de cada chamada para mostrar o custo por vídeo.

### Formato do roteiro (JSON)
```json
{
  "tema": "Paradoxo de Simpson",
  "titulo_capa": "Berkeley *discriminava* mulheres?",
  "legenda": "Em 1973, os números de Berkeley pareciam provar discriminação...",
  "hashtags": ["#cienciadedados", "#estatistica"],
  "trechos": [
    {
      "fala": "Em mil novecentos e setenta e três, a Universidade de Bérqueli parecia discriminar mulheres.",
      "titulo_tela": ["Berkeley *discriminava*", "mulheres?"],
      "cena": { "tipo": "lugar", "lugar": "berkeley" },
      "fonte_id": "bickel1975"
    },
    {
      "fala": "Nos seis maiores departamentos, quarenta e cinco por cento dos homens foram aprovados. Das mulheres, só trinta.",
      "titulo_tela": ["Aprovados nos 6 maiores", "departamentos"],
      "cena": { "tipo": "barras", "unidade": "%",
                "dados": [{ "rotulo": "Homens", "valor": 44.5 }, { "rotulo": "Mulheres", "valor": 30.4 }] },
      "fonte_id": "bickel1975"
    }
  ],
  "fontes": [
    { "id": "bickel1975",
      "rodape": "Bickel, Hammel & O'Connell (1975), Science",
      "citacao": "Bickel, P. J., Hammel, E. A., & O'Connell, J. W. (1975). Sex Bias in Graduate Admissions: Data from Berkeley. Science, 187(4175), 398–404.",
      "url": "https://doi.org/10.1126/science.187.4175.398",
      "trecho_que_comprova": "..." }
  ],
  "pessoas": [
    { "nome": "Edward H. Simpson", "datas": "1922–2019", "feito": "descreveu o paradoxo em 1951",
      "cor_pele": "clara", "idade_na_epoca": 29, "fonte_id": "..." }
  ]
}
```

### Regras do roteiro (vão no prompt de sistema)
- Português do Brasil, tom de curiosidade, sem jargão desnecessário.
- **65 a 72 s** de fala: cerca de 190–210 palavras na velocidade 1,2. Gancho forte nos
  primeiros 3 s.
- Ritmo rápido: o texto na tela troca a cada 2–5 s e mostra palavras-chave, não a frase falada.
- Duas histórias ou exemplos por vídeo quando possível (ex.: Berkeley + pedras nos rins).
- **Dados reais e checados.** Todo número, data, nome e estudo precisa de uma fonte em
  `fontes`, com **URL oficial** que o Claude abriu com web fetch e o trecho que comprova.
  Nada de número sem fonte.
- O número falado tem que bater com o da tela (arredondamento consistente).
- Números, anos e siglas escritos por extenso na `fala` (ex.: "mil novecentos e setenta e
  três"); nomes estrangeiros grafados do jeito que se pronuncia (ex.: "Bérqueli", "Ânscom").
- Só tipos de cena do catálogo.

### Validação antes da revisão (no backend)
- JSON válido no schema; só cenas do catálogo; todo trecho com número tem `fonte_id`.
- Contagem de palavras dentro da faixa.
- Cada URL de fonte responde (status 200/3xx). Marque em vermelho as que falharem.

## Telas
### Temas
- Tabela com busca e filtros: título, categoria, prioridade, status, data.
- Status: `ideia`, `em_roteiro`, `roteiro_pronto`, `roteiro_aprovado`, `renderizando`,
  `pronto_para_revisao`, `aprovado`, `agendado`, `publicado`, `descartado`.
- Importar CSV (comece importando `temas_iniciais.csv`), adicionar manualmente, editar,
  descartar.
- Botão "Gerar mais temas": pede ao Claude N temas novos sobre um assunto, mandando a lista
  existente para não repetir.
- Selecionar um ou vários temas e "Enviar para produção".

### Produção
- Fila de temas em produção com status ao vivo.
- **Revisão do roteiro:** fala e textos de tela editáveis por trecho, tipo de cena, e a lista
  de **fontes com link clicável** (abre em nova aba), citação completa e o trecho que
  comprova. Pessoas citadas com os dados usados na caricatura e a fonte. Contador de
  palavras e duração estimada. Botões: aprovar, regenerar (com instrução opcional), editar.
- **Render:** barra de progresso e log; ao terminar, player do MP4, capa e 4 quadros de prévia.
- **Ajustes:** trocar a velocidade da voz, editar um trecho e re-renderizar.
- Aprovar o vídeo final: cria o registro na biblioteca com a legenda e as hashtags do roteiro
  (a legenda inclui as fontes no final).

### Agenda
- Biblioteca: miniatura, duração, tema, status por plataforma.
- Editor: legenda base + variação por plataforma, com contador de caracteres.
- "Publicar agora" (com confirmação) e "Agendar" (data e hora em America/Sao_Paulo).
- "Preencher a semana": distribui vídeos aprovados nos horários que eu definir.
- Painel: agendados, publicados, rascunhos pendentes no TikTok (com tempo restante para
  expirar) e erros legíveis.
- Contas: conectar e reconectar Instagram e TikTok, ver a validade dos tokens.

### Personalização por vídeo (pedido em 2026-11-02)
Cada tema/vídeo tem uma página de detalhes onde dá para:
- Personalizar: voz (vozes pt-br do Kokoro: `pm_alex`, `pm_santa`, `pf_dora`), velocidade,
  duração alvo, tom, instruções livres para o roteiro. O que não for preenchido usa o padrão.
- Ver todos os assets do vídeo: roteiro (todas as versões), áudios por trecho, narração, MP4,
  capa, prévias, log do render, com os parâmetros usados em cada geração (voz, velocidade,
  modelo, tokens).
- Entrar com prompts de correção ("o trecho 3 está longo demais", "troque a cena 5 por uma
  tabela", "fale mais devagar") para regenerar o roteiro inteiro, só um trecho ou só o
  render. Guardar o histórico das correções.

## Modelo de dados (inicial)
- **tema:** id, titulo, categoria, notas, prioridade, status, criado_em.
- **roteiro:** id, tema_id, versao, json, modelo, tokens_entrada, tokens_saida, custo_estimado,
  aprovado_em.
- **render:** id, roteiro_id, status (`na_fila|rodando|ok|erro`), caminho_mp4, caminho_capa,
  duracao_s, log, iniciado_em, terminado_em.
- **video:** id, tema_id, render_id, caminho, titulo, legenda_base, hashtags, duracao, criado_em.
- **publicacao:** video_id, plataforma (`instagram|tiktok`), legenda_especifica, status
  (`pendente|agendado|enviando|publicado|rascunho_enviado|erro`), agendado_para,
  id_externo, erro.
- **conta:** plataforma, access_token, refresh_token, expira_em. Renovação automática.
- **trabalho:** id, tipo (`roteiro|render|publicacao|gerar_temas`), referencia_id, status,
  tentativas, erro, criado_em.

## Integração: Instagram (Instagram API with Instagram Login)
- Conta Profissional (Criador). Não precisa de Página do Facebook.
- Escopos: `instagram_business_basic`, `instagram_business_content_publish`.
- App em modo de desenvolvimento, com a conta do canal adicionada ao app. Não precisa de
  App Review.
- Credenciais: Instagram app ID e app secret (os da página "API setup with Instagram login",
  não o App ID da Meta).
- Fluxo: `POST /{ig-id}/media` com `media_type=REELS` e `caption` (vídeo por URL pública ou
  upload direto, ver "Ambiente"); consultar `GET /{container-id}?fields=status_code` até
  `FINISHED`; `POST /{ig-id}/media_publish` com o `creation_id`.
- Limite: 50 posts por 24 h. Consultar `content_publishing_limit` antes de publicar.
- Token de longa duração (60 dias), renovado automaticamente.

## Integração: TikTok (Content Posting API)
- App no TikTok for Developers com Login Kit + Content Posting API, escopos
  `user.info.basic` e `video.upload`.
- Usar **upload para a caixa de entrada** (`/v2/post/publish/inbox/video/init/`). NÃO usar
  Direct Post: sem auditoria, os posts saem privados.
- Enviar o arquivo local em chunks (`FILE_UPLOAD`). Evitar `PULL_FROM_URL`.
- O rascunho expira em 24 h se não for finalizado no app. Mostrar isso no painel.
- Access token de 24 h, refresh token de 1 ano, com renovação automática.
- Testes em modo Sandbox, com a conta do canal como usuária de teste.
- A revisão do app exige páginas de Termos de Uso e Política de Privacidade: servir pelo
  próprio app.

## Fases
1. **Esqueleto:** projeto, `make dev`, interface com as 3 abas e dados fictícios.
2. **Banco e temas:** SQLite, importação de `temas_iniciais.csv`, aba Temas funcional.
3. **Motor:** `referencia/` vira `motor/` + CLI. Critério: renderizar o roteiro de exemplo do
   Paradoxo de Simpson em JSON e obter um vídeo equivalente ao de referência.
4. **Roteiro pela API:** prompt de sistema, structured outputs, web search/fetch, validação e
   tela de revisão com fontes clicáveis. Critério: gerar e aprovar o roteiro de um tema novo.
5. **Produção completa:** worker, narração, render, prévia, aprovação, biblioteca.
6. **Instagram:** OAuth + publicação de um Reel de ponta a ponta (com confirmação).
7. **TikTok:** OAuth + envio para a caixa de entrada.
8. **Agenda:** agendamento, "preencher a semana", painel.
9. **Extras:** produção em lote, "gerar mais temas", revisão automática dos quadros de prévia
   pela visão do Claude (aponta texto cortado, números divergentes, capa vazia), custo por vídeo.

Ao final de cada fase, me diga o que testar e o que vem a seguir.
