-- SOMENTE LEITURA (RNF005). Nomes de tabela/coluna do AGHU: VALIDAR com o DBA/SETISD.
SELECT soe.seq               AS solicitacao_aghu,
       pac.codigo            AS paciente_codigo_aghu,
       pac.nome              AS paciente_nome,
       pac.prontuario        AS prontuario_aghu
  FROM agh.ael_solicitacao_exames soe
  JOIN agh.agh_atendimentos       atd ON atd.seq = soe.atd_seq
  JOIN agh.aip_pacientes          pac ON pac.codigo = atd.pac_codigo
 WHERE soe.seq = :solicitacao_aghu;