# Arquitetura V0

## Visao

Homely inicia como monolito modular. O aplicativo mobile consome exclusivamente a API; a API concentra autenticacao, autorizacao, regras de dominio e acesso ao PostgreSQL. E-mail, push e hospedagem sao adaptadores de infraestrutura substituiveis.

```text
Expo Mobile -- HTTPS --> FastAPI API --> PostgreSQL
                              |             ^
                              v             |
                       Email / Push     Scheduler + Worker
```

Scheduler e worker residem no mesmo repositorio e podem executar como processos separados do mesmo deployment. Nao ha microservicos, ORM de aplicacao, Redis, fila externa ou WebSocket no V0.

## Organizacao do Repositorio

```text
Homely/
  README.md
  backend/
    core/                 # configuracao, seguranca, cookies/sessoes, respostas e infra compartilhada
    routes/               # HTTP e dependencias FastAPI
    schemas/              # validacao e contratos Pydantic
    services/             # regras de dominio e orquestracao transacional
    repositories/         # SQL explicito asyncpg e consultas especificas
    migrations/           # Alembic
    tests/                # testes de comportamento da API e servicos
    specs/
  mobile/
    app/                  # rotas e layouts Expo Router; nenhuma regra de negocio
    src/
      api/                # cliente HTTP, tipos OpenAPI gerados e contratos comuns
      features/           # auth, households, tasks, shopping, events, notifications
      components/         # UI com reuso real
      hooks/              # hooks transversais com reuso real
      stores/             # sessao, household ativa e convite pendente
      theme/              # tokens e componentes visuais
      lib/                # SecureStore, deep links, notificacoes e integracoes nativas
      test/               # suporte a testes unitarios
    maestro/              # fluxos E2E nativos
```

Backend preserva os limites atuais: rotas cuidam de HTTP, schemas validam e serializam, services concentram regras e transacoes, repositories executam SQL parametrizado com `asyncpg`. Nao introduzir ORM ou repositorio generico.

No mobile, cada feature mantem suas telas, componentes, chamadas HTTP, queries, mutations e schemas proximos. Um componente somente sai da feature quando houver reuso concreto. UI nao chama HTTP diretamente; hooks da feature escondem esse detalhe.

## Dominio e Persistencia

Entidades iniciais: `users`, `households`, `household_members`, `household_invites`, sessoes e tokens de magic link. O ciclo de uso adiciona `tasks`, `task_occurrences`, `shopping_items`, `events` e `activity_events`. Recorrencia adiciona `task_rule_versions` e participantes. Distribuicao inclui ausencias e transferencias. Operacao inclui `scheduled_jobs` e `device_push_tokens`.

Entidades operacionais possuem UUID exposto, `household_id` quando pertencem a uma casa, timestamps UTC e autoria quando aplicavel. Migrations sao exclusivamente versionadas por Alembic. Leitura e escrita selecionam apenas colunas necessarias e usam parametros.

## Contratos

FastAPI publica OpenAPI como fonte de verdade. O mobile gera somente tipos TypeScript a partir de `openapi.json`; CI falha quando os tipos estao desatualizados. O cliente HTTP e pequeno e explicito. Zod valida entradas de formulario, deep links, SecureStore e integracoes externas, sem duplicar todo o OpenAPI manualmente.

Rotas usam `household_id` explicito, mas dependencias de autorizacao confirmam que o usuario participa da casa ativa. Services retornam o contrato existente de status/mensagem/dados e rotas usam `default_response`.

## Sessao Mobile

Deep links possuem codigo temporario de uso unico. O app troca o codigo pela sessao, mantem access token curto em memoria e armazena refresh token opaco apenas no SecureStore. A renovacao rotaciona tokens. Na abertura, restaura sessao, carrega memberships e abre diretamente a ultima casa usada ou a unica casa ativa; convite pendente e retomado apos a sessao.

## Jobs

`scheduled_jobs` persiste tipo, chave deterministica, estado, tentativa, proxima execucao, lock e erro seguro. O scheduler cria/atualiza jobs; workers buscam trabalho com `FOR UPDATE SKIP LOCKED`. Efeitos de dominio sao idempotentes e persistidos na mesma transacao quando necessario. Locks vencidos voltam a pendente apos 10 minutos; tentativas usam backoff e falhas finais permanecem visiveis para diagnostico.

## Ambientes e Distribuicao

| Ambiente | Banco e integracoes | Mobile |
| --- | --- | --- |
| Development | PostgreSQL no Docker Compose, e-mail capturado localmente, push desligado | Expo Go quando suficiente; Development Build para deep links e push. |
| Preview | API, PostgreSQL, e-mail e credenciais isolados; dados descartaveis | Build interna EAS para Android e iOS usada pelos moradores. |
| Production | Banco e credenciais isolados, backup automatico, monitoramento e restore testado | Build EAS apontando somente para API de producao. |

Migrations passam por pipeline controlado antes do deploy. Nenhum banco, token, storage ou segredo e compartilhado entre ambientes. Preview pode ser reiniciado; production exige backup e teste periodico de restore.

## Qualidade e Observabilidade

Logs estruturados incluem `request_id`, usuario, household, rota, duracao e status quando disponiveis. Erros inesperados sao registrados no limite HTTP/worker e retornam mensagens seguras. Auditoria append-only explica alteracoes sem substituir estado operacional.

CI executa lint, typecheck, testes, aplicacao de migrations e verificacao dos tipos OpenAPI. Maestro executa smoke E2E nativo sem bloquear indevidamente PRs; suite completa roda em `main` ou em agenda. Nao ha E2E web para a API.
