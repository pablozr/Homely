# 00 - Configuracao dos ambientes

**What to build:** estabelecer os ambientes isolados de development, preview e production para que backend, mobile, banco, e-mail, push e builds sempre apontem para recursos do ambiente correto.

**Blocked by:** None - can start immediately.

**Status:** ready-for-agent

- [ ] Development usa PostgreSQL via Docker Compose, e-mail capturado localmente e push desabilitado.
- [ ] Preview possui API, PostgreSQL, e-mail, push e segredos isolados para builds internas descartaveis.
- [ ] Production possui recursos e credenciais isolados, backups automaticos e procedimento documentado de restore testado.
- [ ] Configuracao mobile diferencia development, preview e production, incluindo base URL da API e esquema de deep link, sem compartilhar segredos entre ambientes.
- [ ] Pipeline aplica migrations de forma controlada antes de cada deploy e impede configuracoes de desenvolvimento em production.
