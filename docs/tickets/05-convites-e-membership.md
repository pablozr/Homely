# 05 - Convites e membership historica

**What to build:** permitir que o owner convide moradores por link e que o aceite autenticado crie membership historica de maneira segura.

**Blocked by:** 04 - Criar household e selecionar casa.

**Status:** ready-for-agent

- [ ] Owner cria e revoga convite generico de uso unico, alta entropia e validade de sete dias.
- [ ] App guarda `invite_token` pendente, autentica separadamente e retoma o aceite apos restaurar sessao.
- [ ] Aceite e atomico, idempotente para membro existente e nunca consome convite sem criar/encontrar membership.
- [ ] Remocao, saida voluntaria, retorno em nova membership e transferencia atomica de ownership preservam historico e nunca deixam casa sem owner.
