# Changelog

Formato: [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) · [SemVer](https://semver.org/lang/pt-BR/).

## [2.1.0] — 2026-11-22

O `.pbip` volta a abrir em pastas com caminho comprido, a skill `powerbi-architect` ganha comandos no
`pbw` e o `pbw validar` passa a pegar visuais quebrados.

### Corrigido
- **"O caminho especificado, o nome do arquivo ou ambos são muito longos" ao abrir no Power BI Desktop.**
  O Desktop não lê arquivos com 260 caracteres ou mais e o PBIR é fundo. `pbw abrir` agora mede o maior
  caminho do projeto (inclusive o próximo visual que o Desktop criar) e, quando passa do limite, abre o
  projeto por uma unidade virtual curta (`subst P: <repositório>`): os mesmos arquivos, sem copiar nada.
  `--sem-atalho` desliga.
- `.gitignore` protegia `documentos/legado/original.pbit`, uma pasta que não existe: o `.pbit` legado em
  `trabalho-da-ia/legado/` (que pode ter hosts no Power Query) podia ir para o Git.
- O catálogo trazia a data de geração, então a etapa "Catálogo atualizado" do CI falhava em qualquer dia
  depois do último `pbw catalogo`. Agora ele só muda quando um dashboard muda.
- `.gitattributes` e `.vscode/settings.json` apontavam para pastas antigas (`analytics/`, `docs/`,
  `documentos/legado/`): arquivos gerados voltam a ficar recolhidos no diff dos PRs.
- Hook `pre-commit`: procura um Python 3.11+ que funcione de verdade (no Windows, `python3` pode ser só o
  atalho da Microsoft Store e bloqueava todo commit).
- Hook de início de sessão do Claude Code: tenta `python3` e depois `python` (macOS e Linux sem `python`).
- Licença renomeada para `LICENSE.md`, que o GitHub mostra formatada.
- Notas da versão 2.0.0 citavam pastas (`documentos/`, `entrega/`) que não existem: corrigidas.

### Adicionado
- Regra **PBW025**: caminho longo demais para o Power BI Desktop (no Windows mede a pasta real; fora dele,
  uma pasta curta típica). `pbw novo` avisa na hora.
- Regra **PBW026**: pasta de página/visual diferente do `name` do JSON; duas páginas com o mesmo nome.
- Regra **PBW027**: visual usando tabela, coluna ou medida que não existe no modelo.
- `pbw diagnostico`: tamanho da pasta do repositório, aviso de pasta sincronizada (OneDrive/SharePoint),
  `core.longpaths` do Git no Windows e a versão da skill instalada.
- `pbw skill`: onde a skill `powerbi-architect` está instalada (projeto, global ou plugin do Claude Code),
  a versão de cada cópia e como instalar ou atualizar. Não instala nada.
- `pbw auditar <dashboard>`: roda a auditoria da skill (achados + nota de harmonia por página).
- `pbw previa <dashboard>`: roda a prévia da skill e abre as páginas no navegador, sem Power BI.
- `pbw abrir` (e os outros comandos) sem nome e fora de um dashboard lista os dashboards existentes.
- `AGENTS.md`: seção sobre a skill (o que vale quando os dois discordam, grafo antes dos arquivos,
  auditoria na fase 6) e regra de tamanho de caminho no PBIR.
- Guias: onde clonar (`C:\pbw`), `git config --global core.longpaths true`, FAQ do erro de caminho longo.
- `powerbi-graph/` saiu do `.gitignore` da raiz: a skill cria o próprio `.gitignore` dentro da pasta, e
  `--commit-graph` volta a funcionar para quem quer versionar o grafo.
- Modelos de issue (saída do `pbw diagnostico`/`pbw validar`) e de PR (abrir no Desktop, auditoria).
- Testes: caminhos longos (inclusive `subst` de verdade no Windows do CI), PBW026/PBW027, `.gitignore`
  derivado do layout, skill, hook `pre-commit`.

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
  o tema em **todos** os dashboards da empresa; empresa sem pasta usa a identidade neutra de
  `_sistema/identidade-padrao/` (antes `example/`).
- Raiz: `analytics/` → `dashboards/` · `refactor/inbox/` → `refatorar/` · `brand/` → `identidade-visual/` ·
  `config/connections/` → `conexoes/` · `config/workspaces.toml` → `workspaces.toml` · `docs/` → `guias/` ·
  `tools/`, `templates/`, `tests/` → `_sistema/` · `CONTRIBUTING`, `SECURITY`, `CODE_OF_CONDUCT` → `.github/`.
- Dashboard: `<Nome>.pbip`, `.Report/` e `.SemanticModel/` saem de `src/` para `2-power-bi/`;
  `src/sql/` → `trabalho-da-ia/sql/`; `briefing/` → `1-seu-pedido/PEDIDO.md` + `1-seu-pedido/anexos/`;
  `design/` (4 arquivos) → `trabalho-da-ia/desenho.md` (Modelo · Métricas · Páginas · Decisões);
  `tests/` → `trabalho-da-ia/conferencia.md`; `docs/dicionario.md` → `trabalho-da-ia/dicionario.md`;
  `CHANGELOG.md` → `trabalho-da-ia/historico.md`; `dist/` → `3-entrega/`; `visuals/` → `trabalho-da-ia/visuais-customizados/`
  (só quando existe); `legacy/` → `trabalho-da-ia/legado/`; `dashboard.toml` → `trabalho-da-ia/ficha.toml`; `README.md` → `LEIA-ME.md`.
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
- `pbw prototipo`: desenha as páginas de `trabalho-da-ia/desenho.md › Páginas` como protótipo (caixas no
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
