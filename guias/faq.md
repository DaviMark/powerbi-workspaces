# Perguntas frequentes (e receios honestos)

**Preciso de Fabric/Premium?** Não. PBIP funciona no Power BI Desktop gratuito. Fabric Git integration é opcional.

**A IA vai inventar números?** Ela não calcula números: escreve SQL/DAX. Por isso há o **Gate 2** —
você confere `trabalho-da-ia/conferencia.md` contra uma fonte confiável antes de publicar. Com o Power BI Modeling
MCP a IA também roda as consultas de validação.

**A IA pode apagar ou publicar algo sozinha?** O `AGENTS.md` proíbe publicar, mudar para `production` ou
agir fora da árvore governada. Mesmo assim, revise os diffs: tudo é texto versionado e reversível com Git.

**E se o PBIP não abrir no meu Desktop?** Os arquivos usam versões de schema antigas e estáveis,
validadas contra os schemas oficiais; o Desktop atualiza ao salvar. Use uma versão recente do Desktop.
Abra uma issue com a mensagem de erro (sem dados sensíveis).

**Minha fonte não aceita SQL nativo (Excel, SharePoint, API).** Leve os dados para uma camada
consultável (view, lakehouse, warehouse) — essa é a recomendação de arquitetura. Se não der, registre a
exceção em `trabalho-da-ia/desenho.md`; o validate só vai avisar.

**Por que TOML e não YAML?** O Python lê TOML nativamente (zero dependências) e TOML é difícil de quebrar
com indentação.

**Por que Python e não PowerShell?** Roda igual em Windows, macOS, Linux e no CI, e é auditável.

**Posso usar sem IA?** Sim. Estrutura, CLI, templates e validação valem para times humanos também.

**Qual IA é melhor?** Qualquer uma que leia `AGENTS.md`/skills e edite arquivos (modo agente).
O resultado depende mais do pedido e dos gates do que da ferramenta.

**LGPD?** Marque `contains_pii` e `classification` na `trabalho-da-ia/ficha.toml`, importe o mínimo de colunas pessoais,
use RLS quando o público variar, e mantenha o repositório privado.
