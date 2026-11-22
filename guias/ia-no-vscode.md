# IA no VS Code — como cada ferramenta entende o repositório

Um só contrato: **[`AGENTS.md`](../AGENTS.md)**. Cada ferramenta tem um "ponteiro" para ele:

| Ferramenta | Lê automaticamente | Comandos prontos |
|---|---|---|
| GitHub Copilot (agent mode) | `.github/copilot-instructions.md`, `.github/instructions/*.instructions.md`, `AGENTS.md`, skills em `.github/skills/` | `/novo-dashboard`, `/refatorar`, `/identidade-visual`, `/documentar`, `/revisar`, `/trocar-conexao` (`.github/prompts/`) |
| Claude Code | `CLAUDE.md` (importa `AGENTS.md`), skills em `.claude/skills/` | mesmos comandos em `.claude/commands/` |
| Cursor | `.cursor/rules/workspaces.mdc`, `AGENTS.md`, skills | — |
| OpenAI Codex | `AGENTS.md`, skills em `.agents/skills/` | — |
| Gemini CLI | `GEMINI.md` → `AGENTS.md` | — |

## Instale a skill `powerbi-architect`

É o "cérebro" de Power BI (star schema, DAX, PBIR/TMDL, design, custom visuals). Este repositório
define **onde e em que ordem**; a skill define **como fazer em nível sênior**.

```bash
git clone https://github.com/DaviMark/powerbi-architect.git ../powerbi-architect
../powerbi-architect/install/install.sh .          # macOS/Linux/Git Bash
# ou, no PowerShell:
..\powerbi-architect\install\install.ps1 -Target .
```

O instalador copia a skill para `.claude/skills/`, `.github/skills/` e `.agents/skills/`. Depois ele gera
o grafo de conhecimento em `powerbi-graph/` (ignorado pelo Git):
- `GRAPH_REPORT.md`: visão geral e achados, como colunas sem uso e campos quebrados;
- `wiki/<modelo>.md`: um card por modelo;
- os comandos `query`, `explain`, `impact` e `path`.

O instalador também adiciona uma seção ao `AGENTS.md` para a IA consultar o grafo antes de abrir os arquivos.
E cria hooks que mantêm o grafo atualizado. Para só copiar a skill, use `--no-graph` / `-NoGraph`.
Quer versionar o grafo para o time inteiro? Instale com `--commit-graph`: o repositório deixa essa
escolha para a skill.

Para conferir a instalação, a versão de cada cópia e como atualizar: `pbw skill`. Com a skill instalada,
você ganha dois comandos:

- `pbw auditar <dashboard>`: auditoria do modelo e dos visuais, com nota de harmonia por página
  (a skill pede 90 ou mais para entregar);
- `pbw previa <dashboard>`: prévia das páginas no navegador, sem o Power BI Desktop.

## (Opcional) Power BI Modeling MCP

O MCP oficial da Microsoft permite à IA abrir o modelo no Power BI Desktop/PBIP, criar medidas e
**executar consultas DAX** para validar números. Instale pela extensão do VS Code
*Power BI Modeling MCP* (ou o pacote npm `@microsoft/powerbi-modeling-mcp`). Em `workspaces.toml`,
`[ai] model_editing = ["mcp", "files"]` diz à IA para preferir o MCP quando ele estiver disponível.

> Conecte o MCP a modelos de **desenvolvimento**. A IA verá resultados de consultas DAX.

## Boas práticas de prompt

- Diga **o caminho** do dashboard: *"crie o dashboard dashboards/acme/…"*.
- Peça **uma fase por vez** se quiser revisar com calma: *"faça só o Gate 1"*.
- Use `/revisar` antes de abrir PR.
