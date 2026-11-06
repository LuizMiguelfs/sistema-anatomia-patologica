INSERT INTO casos (
    identificador_interno, solicitacao_aghu, paciente_codigo_aghu, paciente_nome,
    prontuario_aghu, tipo_exame, etapa_atual, status, criado_por, criado_em, atualizado_em, ativo
) VALUES (
    :identificador_provisorio, :solicitacao_aghu, :paciente_codigo_aghu, :paciente_nome,
    :prontuario_aghu, :tipo_exame, :etapa_atual, :status, :usuario, :agora, :agora, 1
)
RETURNING id;