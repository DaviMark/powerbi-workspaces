## O que muda

<!-- Dashboard(s) afetado(s) e o porquê, em linguagem de negócio. -->

## Tipo
- [ ] Novo dashboard
- [ ] Refatoração de legado
- [ ] Alteração em dashboard existente
- [ ] Identidade visual / conexão / framework

## Framework (só para mudanças no `_sistema/`)
- [ ] Testes passam: `python -m unittest discover -s _sistema/testes -v`
- [ ] `CHANGELOG.md` atualizado

## Checklist (Definition of Done)
- [ ] `pbw validar` sem erros (o `.pbip` abre no Power BI Desktop)
- [ ] Aberto de verdade no Power BI Desktop com `pbw abrir` (Windows)
- [ ] Com a skill instalada: `pbw auditar` sem bloqueadores (informe a nota de harmonia de cada página)
- [ ] Gate 1 (desenho + protótipo) aprovado — `trabalho-da-ia/desenho.md`
- [ ] Números conferidos — `trabalho-da-ia/conferencia.md` (Gate 2)
- [ ] `LEIA-ME.md`, `trabalho-da-ia/historico.md` e `trabalho-da-ia/ficha.toml` atualizados · `pbw documentar` rodado
- [ ] Sem dados, sem segredos (`pbw seguranca` ok)
- [ ] Visual customizado? Decisão registrada em `trabalho-da-ia/desenho.md`
