# 07 - Conclusao de tarefa em um toque

**What to build:** permitir concluir uma tarefa pendente em um toque, sem perder autoria nem corromper dados em toques concorrentes.

**Blocked by:** 06 - Criar e listar tarefas avulsas.

**Status:** ready-for-agent

- [ ] A primeira transicao atomica de PENDING para DONE define `completed_by` e `completed_at`; tentativas posteriores retornam o estado atual.
- [ ] O autor conclui e pode desfazer em 10 segundos; membros ativos podem corrigir posteriormente por acao explicita auditada.
- [ ] A Home e a tela de Tarefas oferecem conclusao em um toque e feedback imediato apos confirmacao do backend.
- [ ] Testes cobrem concorrencia, undo condicionado, auditoria e autorizacao.
