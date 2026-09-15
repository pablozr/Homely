# 13 - Scheduler e worker persistidos

**What to build:** executar materializacao e demais trabalhos agendados com recuperacao segura de falhas, sem fila externa.

**Blocked by:** 12 - Recorrencia com responsavel fixo.

**Status:** ready-for-agent

- [ ] `scheduled_jobs` persiste chave deterministica, tentativas, proxima execucao, locks e erro seguro.
- [ ] Scheduler cria/atualiza jobs e worker consome com transacao e `FOR UPDATE SKIP LOCKED`.
- [ ] Locks expirados retornam a pendente apos 10 minutos e jobs longos podem renovar lock.
- [ ] Retry com backoff nao duplica efeitos de dominio nem eventos de auditoria.
