# 14 - Rotacao e ausencias

**What to build:** permitir revezamento previsivel entre participantes e impedir que ausentes recebam novas atribuicoes.

**Blocked by:** 12 - Recorrencia com responsavel fixo, 13 - Scheduler e worker persistidos.

**Status:** ready-for-agent

- [ ] Regra ROTATION possui participantes explicitos e ordem configuravel em opcoes avancadas.
- [ ] Job de atribuicao resolve ocorrencias sem responsavel nos proximos sete dias em ordem deterministica e avanca cursor ao atribuir.
- [ ] Ausencia usa intervalo inclusivo; membro ativo gerencia a propria ausencia e owner pode remove-la.
- [ ] Ausentes sao pulados sem consumir posicao; sem elegiveis a ocorrencia requer atencao e nao avanca cursor.
