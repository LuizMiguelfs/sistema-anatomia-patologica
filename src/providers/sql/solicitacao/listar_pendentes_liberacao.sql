-- Etapa posterior à validação clínica; liberação AGHU e arquivamento são eventos distintos.
SELECT id, identificador_interno, solicitacao_aghu, paciente_nome, prontuario_aghu,
       tipo_exame, etapa_atual, status, urgente, atualizado_em
FROM solicitacoes_exame
WHERE ativo = 1 AND etapa_atual = 'AGUARDANDO_LIBERACAO'
  AND status IN ('AGUARDANDO_LIBERACAO', 'LAUDO_LIBERADO')
ORDER BY urgente DESC, atualizado_em ASC, id ASC
LIMIT :limite OFFSET :deslocamento;
