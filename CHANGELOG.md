# Registro de alterações — pacote de refino

## 2026-11-10 — Preparação para homologação (sem tag de produção)

- Dashboard conectado aos dados locais, com definição de cada KPI e SLAs parametrizados.
- Cadastro de pacientes read-only, com backend sem operações de escrita no AGHU.
- Criação de casos com exame definido exclusivamente pelo AGHU, sem entrada manual.
- Conciliação cadastral sob demanda com transação única, trilha de auditoria e tratamento de conflitos.
- Migração `20261110_refino_aghu`, novos testes de API e documentação de homologação.
- Testes locais: 110 aprovados, 6 ignorados; `npm run build` e 11/11 pilares do auditor aprovados.
- **Pendente antes de produção:** mapeamento real do exame e das regras de SLA; integração e segurança institucional.
