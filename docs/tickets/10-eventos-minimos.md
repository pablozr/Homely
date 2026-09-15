# 10 - Eventos minimos da casa

**What to build:** permitir registrar eventos datados da casa e exibir os que afetam o dia atual na Home.

**Blocked by:** 08 - Home Hoje.

**Status:** ready-for-agent

- [ ] Membro ativo cria evento com titulo e inicio obrigatorios, como dia inteiro ou horario local da casa; fim e tipo sao opcionais.
- [ ] Membro ativo edita ou cancela, preservando quem cancelou e quando.
- [ ] Home mostra apenas eventos em andamento ou que iniciam hoje e nunca eventos cancelados.
- [ ] Criacao e idempotente e todas as alteracoes relevantes geram auditoria.
