SELECT id, identificador_interno, solicitacao_aghu, paciente_codigo_aghu, paciente_nome,
       prontuario_aghu, tipo_exame, etapa_atual, status, criado_por, criado_em, atualizado_em
  FROM casos
 WHERE id = :caso_id
   AND ativo = 1;