SELECT COUNT(*) AS total
  FROM casos
 WHERE ativo = 1
   AND (:solicitacao   IS NULL OR solicitacao_aghu = :solicitacao)
   AND (:prontuario    IS NULL OR prontuario_indice = :prontuario)
   AND (:identificador IS NULL OR identificador_interno = :identificador)
   AND (:tipo_exame    IS NULL OR tipo_exame = :tipo_exame)
   AND (:etapa         IS NULL OR etapa_atual = :etapa)
   AND (:status        IS NULL OR status = :status);