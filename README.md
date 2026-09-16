# Homely

Aplicativo mobile para moradores organizarem a rotina de uma casa compartilhada: tarefas, compras e eventos. O V0 prioriza respostas rápidas para o que exige atenção agora, sem transformar a casa em um sistema corporativo.

## Estrutura

- `backend/`: API FastAPI, migrations Alembic, PostgreSQL e processos de scheduler/worker.
- `mobile/`: aplicativo Expo/React Native. Será criado no primeiro ticket de fundação.
- `docs/`: visão, especificação, arquitetura e tickets locais do V0.

## Princípios

- O backend é dono das regras de domínio e da autorização.
- PostgreSQL, e-mail, push, storage e hospedagem são infraestrutura substituível.
- Cada entrega deve deixar algo utilizável pelos moradores.
- Priorizar baixo atrito: concluir tarefa e marcar compra exigem um toque.
- Preservar histórico; mudanças futuras não reescrevem decisões já materializadas.

## Ambientes

| Ambiente | Uso | Dados e integrações |
| --- | --- | --- |
| `development` | Desenvolvimento local | PostgreSQL via Docker Compose, e-mail capturado localmente e push desabilitado. |
| `preview` | Builds internas para moradores | API, banco, e-mail e credenciais próprios; pode ser reiniciado. |
| `production` | Uso real | Dados isolados, backups automáticos, monitoramento e restore testado. |

Builds mobile apontam apenas para a API do ambiente correspondente. Tokens, storage, bancos e chaves nunca são compartilhados entre ambientes.

## Desenvolvimento planejado

1. Fundação e onboarding mobile.
2. Primeiro ciclo real: tarefas avulsas, Home, compras e eventos.
3. Recorrência com atribuição fixa.
4. Rotação, fairness, ausências e transferências.
5. Push notifications e operação.

Os detalhes técnicos e decisões de domínio estão em `docs/v0-especificacao.md` e `docs/arquitetura-v0.md`.

## Ambiente Local

Pré-requisitos: Docker Compose e Python 3.11+.

1. Copie `backend/.env.example` para `backend/.env`.
2. Inicie PostgreSQL e Mailpit:

```powershell
docker compose -f backend/docker-compose.yml up -d --wait
```

3. Instale as dependências e aplique migrations:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
```

4. Inicie a API:

```powershell
uvicorn main:app --reload
```

Serviços locais:

- API: `http://localhost:8000/health`
- PostgreSQL: `localhost:5432` (`homely` / `homely`), acessivel somente nesta maquina
- Mailpit: `http://localhost:8025` e SMTP em `localhost:1025`
- Push: desabilitado (`PUSH_ENABLED=false`)

Para encerrar os serviços, execute `docker compose -f backend/docker-compose.yml down`. Use `down -v` somente quando quiser apagar o banco local.
