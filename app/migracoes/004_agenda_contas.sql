-- Fase 8 (agenda) e base da Fase 6 (contas das redes).

ALTER TABLE publicacao ADD COLUMN publicado_em TEXT;
ALTER TABLE publicacao ADD COLUMN enviado_em TEXT;          -- TikTok: rascunho enviado (expira em 24 h)
ALTER TABLE publicacao ADD COLUMN link TEXT;
ALTER TABLE publicacao ADD COLUMN simulado INTEGER NOT NULL DEFAULT 0;
ALTER TABLE publicacao ADD COLUMN log TEXT NOT NULL DEFAULT '';
ALTER TABLE publicacao ADD COLUMN lote TEXT;                 -- "preencher a semana" (para desfazer)
CREATE INDEX publicacao_vencidas ON publicacao (status, agendado_para);

ALTER TABLE video ADD COLUMN legenda_instagram TEXT NOT NULL DEFAULT '';
ALTER TABLE video ADD COLUMN legenda_tiktok TEXT NOT NULL DEFAULT '';

ALTER TABLE conta ADD COLUMN usuario TEXT;
ALTER TABLE conta ADD COLUMN conta_id TEXT;
ALTER TABLE conta ADD COLUMN escopos TEXT;
ALTER TABLE conta ADD COLUMN refresh_expira_em TEXT;
ALTER TABLE conta ADD COLUMN renovado_em TEXT;

-- Segurança: começa em simulação (o worker não publica de verdade).
INSERT INTO ajuste (chave, valor) VALUES ('publicacao_real', '0');
-- Horários da semana (America/Sao_Paulo), segunda = 0.
INSERT INTO ajuste (chave, valor) VALUES ('horarios_semana',
  '{"0": ["12:00"], "1": ["12:00"], "2": ["12:00"], "3": ["12:00"], "4": ["12:00"], "5": ["11:00"], "6": ["11:00"]}');
