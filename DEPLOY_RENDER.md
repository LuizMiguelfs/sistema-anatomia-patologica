# Publicar o SAP no Render — demonstração exclusivamente sintética

Este pacote foi preparado a partir do projeto fornecido. **Não contém a pasta `.git`, bancos locais ou credenciais**.
Os exemplos de pacientes e solicitações AGHU foram substituídos por informações artificiais.
Ele NÃO é uma configuração de produção hospitalar. `ENV=development`, `AUTH_ALLOW_MOCK=true`
e `AGHU_PROVIDER_TYPE=SIMULADO` só são toleráveis para demonstração **com dados fictícios**.

## Publicação recomendada

1. Extraia o ZIP em uma pasta e revise os arquivos. Use **repositório GitHub privado**.
   Se seu projeto já estiver no GitHub, copie apenas os novos arquivos de deploy,
   preservando os commits existentes: `render.yaml`, `Dockerfile`, `docker-entrypoint.sh`,
   `.dockerignore`, `requirements.txt`, `data/aghu_simulado.json`, `data/pacientes.csv`.
2. Envie para seu repositório GitHub (não envie arquivos `.env`, dados clínicos ou credenciais).
3. No Render: **New > Blueprint**; conecte o repositório com `render.yaml`.
4. Quando solicitado, defina `MOCK_AUTH_PASSWORD` com uma senha longa, aleatória e exclusiva.
   `JWT_SECRET` e `SAP_DATA_KEY` são gerados pela plataforma automaticamente e devem ser preservados.
5. Crie o serviço; o Render executará o Dockerfile, as migrações Alembic e a carga sintética
   na primeira inicialização. Acompanhe a aba **Logs**.
6. Abra a URL `https://<seu-servico>.onrender.com` e entre com
   `demo.recepcao` (ou `demo.chefia`) e a senha que você configurou.
7. Verifique o endpoint `https://<seu-servico>.onrender.com/api/health`.

## Limitações importantes

- Plano **Free**: o SQLite é **efêmero**, incluindo a perda de alterações após reinícios,
  redeploys e hibernação. A carga sintética será refeita. Adequado apenas para apresentação.
- Render exige **plano pago + Persistent Disk** para persistir SQLite; configure o disco em
  `/app/data` e conserve `SAP_DATA_KEY`/`JWT_SECRET` ao longo dos deploys.
- Nunca insira dados reais de pacientes no ambiente demo. Não conecte o AGHU/AD reais.
- Para produção hospitalar: `ENV=production`, LDAPS, AGHU PostgreSQL privado e controlado,
  HTTPS, banco persistente e backups, avaliação de segurança/LGPD e aprovação institucional.
- A autenticação demo é Mock; escolha uma senha forte e não divulgue publicamente os logins.
- Prazos do dashboard foram deixados desativados (`{}`) até homologação clínica.

## Desenvolvimento e testes

O ambiente local requer variáveis como `JWT_SECRET`, `SAP_DATA_KEY`,
`AUTH_ALLOW_MOCK`, `MOCK_AUTH_PASSWORD` e a configuração de provedores.
O ZIP inclui `.env.example` do projeto, mas não inclui segredos prontos.
**Build do Docker não foi executado nesta preparação** (indisponibilidade do daemon).

## Implantação sem Blueprint

Render > New > Web Service > repositório > Language: Docker.
Health Check Path: `/api/health`.
Copie as variáveis de `render.yaml` para Environment, gere `JWT_SECRET` e `SAP_DATA_KEY`
com 32 bytes em base64 e defina `MOCK_AUTH_PASSWORD` forte.
