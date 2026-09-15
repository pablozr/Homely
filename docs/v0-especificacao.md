# Homely V0 - Especificacao de Produto

## Problema

Moradores compartilham tarefas, compras e compromissos pelo WhatsApp, memoria e planilhas. Isso torna dificil saber rapidamente o estado da casa, quem esta responsavel e o que ja foi feito.

## Solucao

Um aplicativo mobile compartilhado por household. A Home responde em poucos segundos o que exige atencao hoje. O V0 inicia com tarefas avulsas, compras e eventos e evolui incrementalmente para recorrencia, distribuicao automatica e notificacoes.

## User Stories

1. Como morador, quero entrar por magic link para usar o app sem senha.
2. Como primeiro morador, quero criar uma casa com nome e timezone para iniciar a rotina compartilhada.
3. Como owner, quero convidar pessoas por link de uso unico para formar a casa.
4. Como morador, quero abrir o app diretamente na minha Home para nao perder tempo navegando.
5. Como morador, quero criar uma tarefa avulsa rapidamente para registrar uma necessidade da casa.
6. Como morador, quero concluir uma tarefa em um toque para o app entrar na rotina real.
7. Como morador, quero desfazer uma conclusao acidental sem apagar seu historico.
8. Como morador, quero ver tarefas atrasadas e de hoje primeiro para agir no momento certo.
9. Como morador, quero ver tarefas da casa sem responsavel para decidir se devo assumir uma.
10. Como morador, quero adicionar e marcar itens de compra em um toque para substituir mensagens no grupo.
11. Como morador, quero registrar eventos que afetam a casa para ve-los na Home.
12. Como morador, quero criar uma regra semanal ou mensal para nao recriar a mesma tarefa.
13. Como morador, quero atribuir uma regra a uma pessoa, revezar ou distribuir automaticamente sem ver termos tecnicos.
14. Como morador, quero que ausencias sejam consideradas antes de receber uma nova tarefa.
15. Como morador, quero transferir uma ocorrencia pontual com registro do combinado.
16. Como morador, quero ignorar ou cancelar apenas uma ocorrencia sem apagar seu passado ou futuro.
17. Como morador, quero receber lembretes uteis, mas poder desligar notificacoes de tarefas.
18. Como owner, quero gerenciar convites, membros, ownership, timezone e desativacao da casa sem destruir historico.

## Decisoes de Dominio

### Household e membership

- Todo recurso de dominio pertence a uma `household` ativa.
- Usuarios possuem identidade global por e-mail normalizado e podem pertencer a varias casas.
- Membership e historica: entrada cria um periodo com `joined_at`; saida define `left_at` e status inativo. Um retorno cria nova membership.
- Ha exatamente um `OWNER` ativo. Transferencia e atomica; o ultimo owner nao pode sair, ser removido ou perder o papel.
- Household desativada somente pelo owner quando for o unico membro ativo. Ela bloqueia operacoes, jobs e notificacoes, sem apagar dados.

### Autenticacao e convites

- V0 e mobile-only. A API gera e consome magic links; provedor de e-mail apenas entrega mensagens.
- `POST /auth/magic-link` gera token aleatorio de uso unico, persiste apenas seu hash, expira em 15 minutos e invalida tokens ativos anteriores do e-mail.
- O deep link contem somente `auth_code`. `POST /auth/exchange` o consome atomicamente, cria o usuario apenas apos validacao e retorna access token curto e refresh token opaco.
- Access token fica em memoria; refresh token fica apenas no SecureStore. A rotacao e a revogacao por familia permanecem no backend.
- Convite tem token independente, alta entropia, uso unico, sete dias e pode ser revogado. O aceite autenticado cria/encontra membership e consome o convite na mesma transacao.
- Limites iniciais: magic link 3/e-mail/15 min e 10/IP/hora; exchange 10/IP/15 min; aceite 10/usuario ou IP/15 min.

### Tarefas e ocorrencias

- `Task` e a definicao conceitual e possui titulo atual e arquivamento opcional.
- `TaskOccurrence` e a unidade operacional para tarefas avulsas e recorrentes. Ela concentra estado, responsavel, conclusao, prazo e auditoria.
- Estados: `PENDING`, `DONE`, `SKIPPED` e `CANCELLED`. Atraso e derivado de `PENDING` com `due_at` passado; nao existe estado `OVERDUE`.
- Tarefa avulsa requer titulo; responsavel e prazo sao opcionais. Prazo deve ser futuro. Enquanto pendente, titulo, responsavel e prazo podem ser editados por membro ativo.
- Conclusao e transicao atomica. A primeira conclusao define `completed_by` e `completed_at`; concorrentes recebem o estado atual sem sobrescrever autoria.
- O autor pode desfazer em 10 segundos. Depois, qualquer membro ativo pode usar `Desfazer conclusao`; toda reversao e auditada e nunca apaga a conclusao original.
- Tarefas avulsas pendentes podem ser canceladas, sem exclusao fisica. Tarefas recorrentes materializadas permitem somente concluir, desfazer, assumir, transferir, ignorar ou cancelar.

### Recorrencia e versionamento

- Regras suportam semanal com dias selecionados e mensal com dia de 1 a 31; dia inexistente ocorre no ultimo dia do mes.
- Cada regra possui `effective_from`; o padrao e hoje no timezone da casa. Nao ha geracao retroativa.
- Cada alteracao operacional cria `TaskRuleVersion` imutavel. Frequencia, dias, prazo, participantes, peso e politica versionam o futuro; titulo altera apenas `Task`.
- Ocorrencias referenciam a versao que as originou. Atributos historicos operacionais nunca sao sobrescritos.
- Materializar uma janela movel de 45 dias de forma idempotente, com unicidade por versao/regra e data, sem duplicar datas preservadas de versoes anteriores.
- `FIXED` atribui na materializacao. `ROTATION` e `FAIRNESS` recebem atribuicao nos sete dias anteriores a `scheduled_for` e nao sao reatribuidas automaticamente depois.
- A regra armazena `due_time` local; cada ocorrencia persiste `due_at` UTC e timezone de materializacao. Hora DST inexistente avanca ao proximo horario valido; hora ambigua usa a primeira ocorrencia.

### Atribuicao e distribuicao

- Politicas: `FIXED`, `ROTATION` e `FAIRNESS`. A UX mostra respectivamente responsavel especifico, revezar e distribuir automaticamente.
- Peso padrao e 1. Peso e ordem manual ficam em opcoes avancadas.
- Participantes sao explicitos; inicialmente incluem membros ativos. Entradas futuras nao alteram regras existentes. Removidos deixam de ser elegiveis, mas permanecem no historico.
- `ROTATION` processa ocorrencias por `scheduled_for`, `id`, escolhe o proximo participante elegivel apos o ultimo efetivamente atribuido e avanca no momento da atribuicao. Ausentes sao pulados sem consumir posicao; transferencias e conclusoes nao alteram cursor.
- `FAIRNESS` escolhe menor soma de pesos de ocorrencias `DONE` nos 30 dias anteriores. Empata por quem ha mais tempo nao recebe atribuicao `FAIRNESS`, depois menor `user_id`. Conta para o responsavel vigente no instante da conclusao.
- Ausencia usa datas inclusivas no timezone da casa e apenas impede atribuicoes ainda nao resolvidas. Se nao houver elegiveis, `assigned_to` fica nulo e a ocorrencia requer atencao. Qualquer membro ativo pode assumir; isso nao avanca rotacao.
- Transferencia vale somente para a ocorrencia, atualiza responsavel, preserva responsavel original e registra origem, destino, ator, momento e motivo opcional. Nao exige aceite e notifica o novo responsavel.

### Compras, eventos e Home

- Existe uma unica lista ativa `Compras` por household. Item possui nome obrigatorio; quantidade opcional; categoria e observacao avancadas.
- Marcar comprado e transicao atomica, preservando `purchased_by` e `purchased_at`. Restaurar e auditavel e nao apaga a marcacao anterior.
- Evento requer titulo e inicio. Pode ser dia inteiro ou horario, com fim opcional. Cancelamento preserva `cancelled_at` e `cancelled_by`.
- `GET /households/{id}/today` devolve, ja ordenados no timezone da casa: tarefas do usuario atrasadas/hoje, demais tarefas de hoje, resumo de compras, eventos em andamento ou iniciando hoje e proximas atribuicoes do usuario em sete dias.
- Tela Tarefas possui Lista e Semana. Semana usa `scheduled_for` para recorrentes e data local de `due_at` para avulsas; tarefas sem prazo ficam apenas na Lista.

### Notificacoes, jobs e auditoria

- Notificar atribuicao, lembrete as 09:00 no dia de vencimento quando ainda util, uma hora antes do prazo e transferencia. Categoria `TAREFAS` e opt-out; eventos de seguranca/acesso nao.
- Acao de concluir em notificacao abre o app e usa a mesma transicao atomica da Home.
- Jobs persistidos sao idempotentes. Scheduler planeja materializacao, atribuicao e notificacoes; worker usa locks transacionais. Lock expira em 10 minutos e pode ser renovado. Falhas usam backoff e permanecem diagnosticaveis.
- `activity_events` e append-only e nao e fonte de verdade. Registra ator opcional, entidade, tipo, horario UTC e metadata util, inclusive acoes automaticas do sistema.
- Criacoes sensiveis usam chave de idempotencia por usuario, household e operacao por 24 horas. Repeticao com mesmo payload retorna resultado original; payload diferente retorna conflito.

## Decisoes de Implementacao

- Mobile React Native/Expo com Expo Router e TypeScript; API FastAPI, `asyncpg`, SQL explicito e Alembic.
- Mobile organiza-se por feature. TanStack Query e fonte do estado remoto; Zustand guarda somente sessao, household ativa e convite pendente.
- FastAPI/OpenAPI e fonte unica do contrato estatico. Mobile gera tipos TypeScript e mantem cliente HTTP fino e hooks explicitos por feature. Zod protege formularios, deep links, SecureStore e fronteiras runtime necessarias.
- Toda autorizacao verifica membership no backend; nunca confiar no `household_id` enviado pelo cliente.

## Testes

- Backend testa comportamento observavel de servicos e HTTP: autenticacao, autorizacao por household, migracoes, transacoes atomicas, idempotencia, convites e transicoes de ocorrencias.
- Mobile testa hooks/mutations e componentes criticos: restauracao de sessao, aceite de convite, conclusao e compra em um toque.
- Maestro cobre E2E nativo em Android/iOS; smoke em PRs quando viavel e suite completa em `main` ou agendada. API nao possui E2E web.
- CI executa lint, typecheck, testes, migracoes e verifica tipos OpenAPI gerados.

## Fora do Escopo

- Despesas, saldos, settlements e contas recorrentes.
- Manutencao, anexos, uploads, avatares reais e storage.
- Realtime/WebSocket, fila offline, CRDT, sincronizacao complexa e optimistic updates persistentes.
- RRULE generico, calendario mensal, drag and drop, overrides de ocorrencia e recorrencia de eventos.
- Senhas, web, Expo Web, co-owners, RBAC granular, exclusao definitiva de conta e troca de e-mail.
- Busca, filtros avancados, analytics, feed completo, ranking, ML e IA.
