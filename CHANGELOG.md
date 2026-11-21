# Changelog

Formato: [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) · [SemVer](https://semver.org/lang/pt-BR/).

## [2.0.0] — 2026-11-21

Reestruturação para analistas de dados: pastas com nomes em português, o `.pbip` no topo de cada
dashboard e sempre pronto para abrir no Power BI Desktop.

### Alterado (quebra compatibilidade)
- Pasta do dashboard organizada por quem faz o quê: `1-seu-pedido/` (`PEDIDO.md` em formato de
  formulário, com seções **Regras de negócio** e **Visuais que eu quero**, + `anexos/`), `2-power-bi/`
  (o `.pbip`), `3-entrega/` (o `.pbit`) e `trabalho-da-ia/` (SQL, desenho, conferência, dicionário,
  histórico, `ficha.toml`). `LEIA-ME.md` de cada dashboard começa com "Onde coloco o quê".
- Identidade visual **só por empresa**: `identidade-visual/<empresa>/1-cole-aqui/` (material da marca) e
  `trabalho-da-ia/` (`identidade.toml`, `diretrizes.md`, `tema/`, `logos/`). `pbw identidade <empresa>` aplica
  o tema em **todos** os dashboards da empresa; empresa sem pasta usa `identidade-visual/padrao/`
  (antes `example/`).
- Raiz: `analytics/` → `dashboards/` · `refactor/inbox/` → `refatorar/` · `brand/` → `identidade-visual/` ·
  `config/connections/` → `conexoes/` · `config/workspaces.toml` → `workspaces.toml` · `docs/` → `guias/` ·
  `tools/`, `templates/`, `tests/` → `_sistema/` · `CONTRIBUTING`, `SECURITY`, `CODE_OF_CONDUCT` → `.github/`.
- Dashboard: `<Nome>.pbip`, `.Report/` e `.SemanticModel/` saem de `src/` para o topo da pasta;
  `src/sql/` → `sql/`; `briefing/` → `documentos/pedido.md` + `documentos/anexos/`;
  `design/` (4 arquivos) → `documentos/desenho.md` (Modelo · Métricas · Páginas · Decisões);
  `tests/` → `documentos/conferencia.md`; `docs/dicionario.md` → `documentos/dicionario.md`;
  `CHANGELOG.md` → `documentos/historico.md`; `dist/` → `entrega/`; `visuals/` → `visuais-customizados/`
  (só quando existe); `legacy/` → `documentos/legado/`; `dashboard.toml` → `ficha.toml`; `README.md` → `LEIA-ME.md`.
- Comandos em português: `novo`, `refatorar`, `extrair`, `conexoes`, `conectar`, `sincronizar-sql`,
  `identidade`, `documentar`, `catalogo`, `validar`, `seguranca`, `instalar-hooks`, `diagnostico`
  (os nomes em inglês continuam funcionando). O dashboard pode ser informado só pelo nome
  (`pbw abrir aging-de-titulos`) ou omitido dentro da pasta dele.

### Adicionado
- Pastas-modelo prontas para duplicar e renomear: `dashboards/nome-da-empresa/…/nome-do-dashboard`,
  `identidade-visual/nome-da-empresa/1-cole-aqui/{logo,manual-da-marca,cores-e-fontes,exemplos-de-relatorios}`,
  `refatorar/nome-da-empresa/…/nome-do-dashboard`. Modelos não são validados nem catalogados; uma cópia
  renomeada é reconhecida por `pbw novo` (mantém o pedido) e apontada por `pbw validar`.
- `1-seu-pedido/anexos/{consultas-sql,imagens-e-rascunhos,documentos}` já criadas em todo dashboard.
- `index.html`: guia visual e animado do repositório (abre direto no navegador).
- Identidade neutra movida para `_sistema/identidade-padrao/`.
- Padrão visual de produto (`guias/padrao-visual.md`): moldura de aplicativo em toda página (barra lateral
  na cor da marca com navegação, barra superior com caminho, período e filtros), tema refeito (escala da
  marca, cartões arredondados, sem linhas de grade nem títulos de eixo) e tokens `sidebar*`/`ramp` na identidade.
- Sem arquivos da Microsoft: o tema base CY24SU06 foi removido; os relatórios usam só o tema da empresa.
- Início de sessão: toda IA pergunta se o analista quer a explicação do repositório enquanto ele tiver
  no máximo um dashboard próprio (`dashboards/` + `refatorar/`). `pbw boas-vindas`, hook do Claude Code em
  `.claude/settings.json` e roteiro em `guias/apresentacao.md`.
- Atalhos `pbw.cmd` (Windows) e `pbw` (macOS/Linux/Git Bash) na raiz.
- `pbw abrir`: abre o `.pbip` no Power BI Desktop.
- `pbw prototipo`: desenha as páginas de `documentos/desenho.md › Páginas` como protótipo (caixas no
  grid de 8 px; cartões reais quando a medida já existe). Todo `pbw novo`/`pbw refatorar` já cria o
  protótipo; páginas reais nunca são sobrescritas.
- Regra PBW007 ampliada: o `.pbip` precisa abrir (relatório e modelo existem e se apontam, JSON válido,
  `pages.json` coerente). Regra PBW024: páginas de protótipo (erro em revisão/produção).
- `pbw diagnostico` confere se todo dashboard tem um `.pbip`.
- Suporte a caminhos longos no Windows (pastas profundas, OneDrive).

## [1.1.0] — 2026-11-21

### Alterado
- Projeto renomeado: **PBIP Blueprint → Power BI Workspaces** (`powerbi-workspaces`). CLI `tools/bp.py` → `tools/pbw.py`
  (comando `pbw`), pacote `tools/blueprint/` → `tools/workspaces/`, `config/blueprint.toml` → `config/workspaces.toml`,
  regras `BP0xx` → `PBW0xx`, marcador `bp:allow-secret` → `pbw:allow-secret`.

### Adicionado
- `powerbi-graph/` no `.gitignore`: grafo de conhecimento gerado pela skill powerbi-architect 1.1.

## [1.0.0] — 2026-11-23

### Adicionado
- Árvore governada `analytics/<empresa>/<área>/<subárea>/<dashboard>/` com manifesto, briefing, design, src, docs, tests.
- CLI `tools/pbw.py` (Python stdlib, offline): `new`, `refactor`, `extract`, `connections`, `connect`, `sql-sync`,
  `brand`, `docs`, `catalog`, `validate`, `scan`, `install-hooks`, `doctor`.
- Perfis de conexão para SQL Server/Fabric, SAP HANA, BigQuery, PostgreSQL, Snowflake, Databricks, Oracle, MySQL.
- Esqueleto PBIP (PBIR + TMDL) validado contra os schemas oficiais, com páginas Visão Geral e Documentação,
  tabelas `_Medidas`, `_Documentacao` (INFO.VIEW), `_Cargas` e `Calendario`.
- Refatoração de legado a partir de `.pbit`: diagnóstico, colunas sem uso, PQ, relatório, plano.
- `AGENTS.md` + integrações para Copilot, Claude Code, Cursor, Codex e Gemini.
- 25+ regras de governança, scanner de segredos, pre-commit e CI (Linux + Windows).
- Dashboard de exemplo completo (Acme · Aging de Títulos).
