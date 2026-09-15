# 12 - Recorrencia com responsavel fixo

**What to build:** permitir criar tarefas semanais ou mensais atribuiveis a uma pessoa, gerar ocorrencias futuras idempotentes e preservar versoes de regra.

**Blocked by:** 07 - Conclusao de tarefa em um toque.

**Status:** ready-for-agent

- [ ] UI cria regra semanal por dias ou mensal por dia 1-31, com responsavel especifico e defaults de prazo, peso e inicio.
- [ ] Regras possuem versoes imutaveis e `effective_from`; mudancas operacionais criam versao nova e nunca geram retroativos.
- [ ] Scheduler materializa janela movel de 45 dias, calcula UTC com timezone/DST da casa e nao duplica ocorrencias.
- [ ] FIXED atribui na materializacao; ocorrencias preservam versao, prazo e responsavel historicos.
