-- SOMENTE LEITURA (RNF005). Nomes de tabela/coluna do AGHU: VALIDAR com o DBA/SETISD.
SELECT soe.seq               AS solicitacao_aghu,
       pac.codigo            AS paciente_codigo_aghu,
       pac.nome              AS paciente_nome,
       pac.prontuario        AS prontuario_aghu,
       NULL::varchar(3)       AS tipo_exame -- PENDENTE: DBA mapear a classificação do procedimento no AGHU; não inferir/aceitar valor manual
  FROM agh.ael_solicitacao_exames soe
  JOIN agh.agh_atendimentos       atd ON atd.seq = soe.atd_seq
  JOIN agh.aip_pacientes          pac ON pac.codigo = atd.pac_codigo
 WHERE soe.seq = :solicitacao_aghu;