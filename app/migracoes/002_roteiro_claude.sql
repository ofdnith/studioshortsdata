-- Fase 4: detalhes da geração do roteiro e log dos trabalhos.

ALTER TABLE roteiro ADD COLUMN tokens_cache_escrita INTEGER NOT NULL DEFAULT 0;
ALTER TABLE roteiro ADD COLUMN tokens_cache_leitura INTEGER NOT NULL DEFAULT 0;
ALTER TABLE roteiro ADD COLUMN buscas_web INTEGER NOT NULL DEFAULT 0;
-- 'claude' (gerado), 'correcao' (gerado a partir de uma correção) ou 'edicao' (editado à mão)
ALTER TABLE roteiro ADD COLUMN origem TEXT NOT NULL DEFAULT 'claude';
ALTER TABLE roteiro ADD COLUMN instrucao TEXT NOT NULL DEFAULT '';
-- buscas feitas, páginas abertas, notas para revisão
ALTER TABLE roteiro ADD COLUMN pesquisa_json TEXT NOT NULL DEFAULT '{}';
-- resultado da validação (problemas, palavras, status das URLs)
ALTER TABLE roteiro ADD COLUMN validacao_json TEXT NOT NULL DEFAULT '{}';

ALTER TABLE trabalho ADD COLUMN payload_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE trabalho ADD COLUMN log TEXT NOT NULL DEFAULT '';
