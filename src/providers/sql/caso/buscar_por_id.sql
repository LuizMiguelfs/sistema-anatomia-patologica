SELECT id, identificador_interno, solicitacao_aghu, paciente_codigo_aghu, paciente_nome,
       prontuario_aghu, tipo_exame, ultima_sincronizacao_aghu, etapa_atual, status, urgente, retirado_em, retirado_por, criado_por, criado_em, atualizado_em
  FROM casos
 WHERE id = :caso_id
   AND ativo = 1;