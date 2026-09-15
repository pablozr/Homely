# 16 - Transferencia, ignorar e cancelar ocorrencias

**What to build:** permitir tratar excecoes pontuais de uma recorrencia sem editar a ocorrencia nem reescrever o futuro.

**Blocked by:** 14 - Rotacao e ausencias.

**Status:** ready-for-agent

- [ ] Membro ativo transfere ocorrencia para membro elegivel, sem aceite, preservando responsavel original, origem, destino, ator, horario e motivo opcional.
- [ ] Transferencia afeta apenas a ocorrencia e peso concluido conta para responsavel vigente.
- [ ] Ignorar preserva que a ocorrencia valida nao foi realizada; cancelar preserva que ela foi invalidada.
- [ ] Undo curto restaura estado anterior sem apagar auditoria; transicoes e concorrencia sao testadas.
