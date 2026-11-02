-- Fase 5: custos por vídeo, ajustes gerais e detalhes do render.

-- Custos lançados à mão (os de API são calculados a partir da tabela roteiro).
CREATE TABLE custo (
    id        INTEGER PRIMARY KEY,
    tema_id   INTEGER NOT NULL REFERENCES tema (id),
    categoria TEXT NOT NULL DEFAULT 'outro',
    descricao TEXT NOT NULL DEFAULT '',
    valor     REAL NOT NULL,
    moeda     TEXT NOT NULL DEFAULT 'BRL' CHECK (moeda IN ('BRL', 'USD')),
    data      TEXT NOT NULL DEFAULT (date('now')),
    criado_em TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX custo_tema ON custo (tema_id);

-- Ajustes gerais (chave/valor), ex.: cotação do dólar.
CREATE TABLE ajuste (
    chave TEXT PRIMARY KEY,
    valor TEXT NOT NULL
);
INSERT INTO ajuste (chave, valor) VALUES ('cotacao_usd_brl', '5.50');

ALTER TABLE render ADD COLUMN previas_json TEXT NOT NULL DEFAULT '[]';
ALTER TABLE video ADD COLUMN caminho_capa TEXT;
ALTER TABLE video ADD COLUMN aprovado_em TEXT;
