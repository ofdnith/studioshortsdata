-- Migração inicial: modelo de dados do PROMPT.md + personalização por vídeo.

CREATE TABLE tema (
    id            INTEGER PRIMARY KEY,
    titulo        TEXT NOT NULL,
    categoria     TEXT NOT NULL DEFAULT '',
    gancho        TEXT NOT NULL DEFAULT '',
    notas         TEXT NOT NULL DEFAULT '',
    prioridade    TEXT NOT NULL DEFAULT 'media' CHECK (prioridade IN ('alta', 'media', 'baixa')),
    status        TEXT NOT NULL DEFAULT 'ideia',
    -- Personalização (voz, velocidade, duração alvo, tom, instruções). Chaves ausentes = padrão.
    config_json   TEXT NOT NULL DEFAULT '{}',
    criado_em     TEXT NOT NULL DEFAULT (datetime('now')),
    atualizado_em TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX tema_titulo_unico ON tema (lower(titulo));
CREATE INDEX tema_status ON tema (status);

CREATE TABLE roteiro (
    id             INTEGER PRIMARY KEY,
    tema_id        INTEGER NOT NULL REFERENCES tema (id),
    versao         INTEGER NOT NULL,
    json           TEXT NOT NULL,
    modelo         TEXT NOT NULL DEFAULT '',
    tokens_entrada INTEGER NOT NULL DEFAULT 0,
    tokens_saida   INTEGER NOT NULL DEFAULT 0,
    custo_estimado REAL NOT NULL DEFAULT 0,
    criado_em      TEXT NOT NULL DEFAULT (datetime('now')),
    aprovado_em    TEXT,
    UNIQUE (tema_id, versao)
);

CREATE TABLE render (
    id           INTEGER PRIMARY KEY,
    roteiro_id   INTEGER NOT NULL REFERENCES roteiro (id),
    status       TEXT NOT NULL DEFAULT 'na_fila' CHECK (status IN ('na_fila', 'rodando', 'ok', 'erro')),
    -- Parâmetros usados nesta geração (voz, velocidade etc.), para mostrar nos assets.
    config_json  TEXT NOT NULL DEFAULT '{}',
    progresso    INTEGER NOT NULL DEFAULT 0,
    caminho_mp4  TEXT,
    caminho_capa TEXT,
    duracao_s    REAL,
    log          TEXT NOT NULL DEFAULT '',
    iniciado_em  TEXT,
    terminado_em TEXT
);

CREATE TABLE video (
    id           INTEGER PRIMARY KEY,
    tema_id      INTEGER NOT NULL REFERENCES tema (id),
    render_id    INTEGER NOT NULL REFERENCES render (id),
    caminho      TEXT NOT NULL,
    titulo       TEXT NOT NULL,
    legenda_base TEXT NOT NULL DEFAULT '',
    hashtags     TEXT NOT NULL DEFAULT '',
    duracao      REAL,
    criado_em    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE publicacao (
    id                 INTEGER PRIMARY KEY,
    video_id           INTEGER NOT NULL REFERENCES video (id),
    plataforma         TEXT NOT NULL CHECK (plataforma IN ('instagram', 'tiktok')),
    legenda_especifica TEXT,
    status             TEXT NOT NULL DEFAULT 'pendente' CHECK (status IN
                         ('pendente', 'agendado', 'enviando', 'publicado', 'rascunho_enviado', 'erro')),
    agendado_para      TEXT,
    id_externo         TEXT,
    erro               TEXT,
    atualizado_em      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (video_id, plataforma)
);

CREATE TABLE conta (
    plataforma    TEXT PRIMARY KEY CHECK (plataforma IN ('instagram', 'tiktok')),
    access_token  TEXT,
    refresh_token TEXT,
    expira_em     TEXT,
    atualizado_em TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE trabalho (
    id            INTEGER PRIMARY KEY,
    tipo          TEXT NOT NULL CHECK (tipo IN ('roteiro', 'render', 'publicacao', 'gerar_temas')),
    referencia_id INTEGER,
    status        TEXT NOT NULL DEFAULT 'na_fila' CHECK (status IN ('na_fila', 'rodando', 'ok', 'erro', 'cancelado')),
    tentativas    INTEGER NOT NULL DEFAULT 0,
    erro          TEXT,
    criado_em     TEXT NOT NULL DEFAULT (datetime('now')),
    atualizado_em TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX trabalho_fila ON trabalho (status, id);

-- Prompts de correção por vídeo, com histórico.
CREATE TABLE correcao (
    id          INTEGER PRIMARY KEY,
    tema_id     INTEGER NOT NULL REFERENCES tema (id),
    alvo        TEXT NOT NULL CHECK (alvo IN ('roteiro', 'trecho', 'render')),
    trecho_idx  INTEGER,
    texto       TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pendente' CHECK (status IN ('pendente', 'aplicada', 'erro')),
    resultado   TEXT,
    criado_em   TEXT NOT NULL DEFAULT (datetime('now')),
    aplicada_em TEXT
);
