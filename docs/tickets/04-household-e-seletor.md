# 04 - Criar household e selecionar casa

**What to build:** permitir criar uma household com nome e timezone, tornando o criador owner, e abrir diretamente a casa correta em acessos futuros.

**Blocked by:** 03 - Perfil e onboarding sem casa.

**Status:** ready-for-agent

- [ ] Criacao atomica gera household e membership OWNER, com timezone IANA e `default_due_time` inicial de 20:00.
- [ ] O app abre diretamente a unica household ativa; com varias, reabre a ultima usada e permite troca em seletor simples.
- [ ] Todas as operacoes de household validam membership no backend.
- [ ] Criacao aceita idempotency key e retries nao duplicam household nem auditoria.
