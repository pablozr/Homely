# 02 - Magic link e sessao mobile

**What to build:** permitir que uma pessoa entre no app sem senha por magic link, retorne via deep link e tenha sessao restaurada silenciosamente no proximo acesso.

**Blocked by:** 01 - Fundacao backend e mobile.

**Status:** ready-for-agent

- [ ] A API solicita, entrega e consome magic links de uso unico, com hash persistido, expiracao de 15 minutos, invalidacao anterior e rate limits definidos.
- [ ] O exchange atomico cria usuario somente apos validar o codigo e emite access token curto e refresh token opaco rotacionavel.
- [ ] O app recebe o deep link, armazena somente refresh token no SecureStore e restaura a sessao sem mostrar login quando ela for valida.
- [ ] Testes cobrem expiracao, uso concorrente, rotacao/reuso de refresh token e fluxo mobile de restauracao.
