-- Atualiza exclusivamente o snapshot local; não altera o AGHU.
UPDATE casos
   SET paciente_nome = :paciente_nome,
       prontuario_aghu = :prontuario_aghu,
       prontuario_indice = :prontuario_indice,
       ultima_sincronizacao_aghu = :agora,
       atualizado_em = :agora
 WHERE id = :caso_id AND ativo = 1 AND status <> 'ARQUIVADO';
