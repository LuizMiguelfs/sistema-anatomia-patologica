-- Retrato das filas para o Início: quantas solicitações estão em cada etapa agora.
-- Só contagens: nenhum dado de paciente nem texto de formulário sai desta consulta.
-- "Pendente" segue a mesma regra das filas (listar_fila_fase.sql e contar_solicitacoes.sql).
-- campos_pre_laudo -> JSON {etapa: campo do pré-laudo}; rascunho com esse campo preenchido
--                     conta como aguardando a validação do patologista.
SELECT c.etapa_atual AS etapa,
       COUNT(*) AS pendentes,
       SUM(CASE WHEN c.urgente = 1 THEN 1 ELSE 0 END) AS urgentes,
       SUM(CASE WHEN c.etapa_atual = 'RECEPCAO' AND c.retirado_em IS NULL THEN 1 ELSE 0 END) AS nao_retiradas,
       SUM(CASE WHEN c.etapa_atual = 'RECEPCAO' AND c.retirado_em IS NULL AND c.urgente = 1 THEN 1 ELSE 0 END)
           AS nao_retiradas_urgentes,
       SUM(CASE WHEN f.situacao = 'RASCUNHO'
                 AND length(trim(COALESCE(
                       json_extract(f.dados, '$.' || json_extract(:campos_pre_laudo, '$.' || c.etapa_atual)),
                       ''))) > 0
                THEN 1 ELSE 0 END) AS aguardando_patologista
  FROM solicitacoes_exame c
  LEFT JOIN solicitacao_fases f ON f.solicitacao_id = c.id AND f.etapa = c.etapa_atual
 WHERE c.ativo = 1
   AND c.status <> 'ARQUIVADO'
 GROUP BY c.etapa_atual;
