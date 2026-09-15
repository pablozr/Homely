# 18 - Operacao e distribuicao interna

**What to build:** preparar a validacao com os quatro moradores por builds internas e diagnosticar erros sem expor dados sensiveis.

**Blocked by:** 09 - Lista unica de compras, 10 - Eventos minimos da casa, 17 - Push notifications e acoes rapidas.

**Status:** ready-for-agent

- [ ] Preview possui banco, e-mail, push, segredos e build EAS isolados de development e production.
- [ ] Logs estruturados e error tracker registram falhas de API e jobs com contexto seguro.
- [ ] Backups e procedimento de restore de production estao configurados e documentados antes de dados reais.
- [ ] Maestro cobre smoke nativo de login, convite, Home, conclusao e compras; suite completa roda em `main` ou agenda sem virar gargalo de PR.
