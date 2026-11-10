-- Nenhum identificador pessoal é retornado para o dashboard.
SELECT tipo_exame, status, criado_em, etapa_atual
  FROM casos
 WHERE ativo = 1;
