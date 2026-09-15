# 09 - Lista unica de compras

**What to build:** permitir que a casa mantenha uma unica lista ativa de compras, com adicao e marcacao em um toque.

**Blocked by:** 08 - Home Hoje.

**Status:** ready-for-agent

- [ ] Cada household possui uma unica lista ativa Compras; item requer nome e aceita quantidade opcional.
- [ ] Membro ativo adiciona, edita, compra e restaura itens; compra e transicao atomica que preserva autor e horario.
- [ ] Itens comprados saem da lista ativa e ficam acessiveis no historico; restauracao e auditavel.
- [ ] Home mostra contagem pendente e app refaz cache apos mutacao ou retorno a tela, sem WebSocket.
