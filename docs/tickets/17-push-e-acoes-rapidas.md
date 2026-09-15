# 17 - Push notifications e acoes rapidas

**What to build:** enviar lembretes de tarefa uteis e permitir concluir a partir de uma notificacao sem abrir detalhes.

**Blocked by:** 13 - Scheduler e worker persistidos, 16 - Transferencia, ignorar e cancelar ocorrencias.

**Status:** ready-for-agent

- [ ] App pede permissao de push apenas apos beneficio claro e registra varios tokens por usuario, com plataforma, last seen e inativacao por falha permanente.
- [ ] Scheduler envia atribuicao, lembrete as 09:00 quando util, aviso uma hora antes e transferencia, respeitando preferencia TAREFAS.
- [ ] Envio e idempotente em retries e nao envia alteracoes comuns ou lembrete tardio.
- [ ] Acao Concluir abre o app, restaura sessao quando possivel e usa a mesma transicao atomica e undo da Home.
