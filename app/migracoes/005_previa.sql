-- Prévia por trecho + verificações: novo tipo de trabalho 'previa' e resultado no roteiro.
-- O SQLite não altera CHECK: recria a tabela trabalho com os tipos novos.

CREATE TABLE trabalho_novo (
    id            INTEGER PRIMARY KEY,
    tipo          TEXT NOT NULL CHECK (tipo IN ('roteiro', 'render', 'publicacao', 'gerar_temas', 'previa')),
    referencia_id INTEGER,
    status        TEXT NOT NULL DEFAULT 'na_fila' CHECK (status IN ('na_fila', 'rodando', 'ok', 'erro', 'cancelado')),
    tentativas    INTEGER NOT NULL DEFAULT 0,
    erro          TEXT,
    criado_em     TEXT NOT NULL DEFAULT (datetime('now')),
    atualizado_em TEXT NOT NULL DEFAULT (datetime('now')),
    payload_json  TEXT NOT NULL DEFAULT '{}',
    log           TEXT NOT NULL DEFAULT ''
);
INSERT INTO trabalho_novo (id, tipo, referencia_id, status, tentativas, erro, criado_em, atualizado_em, payload_json, log)
    SELECT id, tipo, referencia_id, status, tentativas, erro, criado_em, atualizado_em, payload_json, log FROM trabalho;
DROP TABLE trabalho;
ALTER TABLE trabalho_novo RENAME TO trabalho;
CREATE INDEX trabalho_fila ON trabalho (status, id);

ALTER TABLE roteiro ADD COLUMN previa_json TEXT NOT NULL DEFAULT '{}';
