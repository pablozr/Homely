# 15 - Fairness e assuncao manual

**What to build:** distribuir tarefas automaticamente de forma deterministica e permitir que a casa resolva rapidamente ocorrencias sem responsavel.

**Blocked by:** 14 - Rotacao e ausencias.

**Status:** ready-for-agent

- [ ] Regra FAIRNESS seleciona membro ativo e presente com menor carga de pesos DONE nos ultimos 30 dias.
- [ ] Empates usam ultima atribuicao FAIRNESS e `user_id` de forma deterministica.
- [ ] Ocorrencia sem responsavel aparece em Outras tarefas da casa e qualquer membro ativo pode assumir em um toque.
- [ ] Assuncao e conclusao contabilizam peso para responsavel vigente sem alterar cursor de rotacao.
