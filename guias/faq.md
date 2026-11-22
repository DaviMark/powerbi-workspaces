# Perguntas frequentes (e receios honestos)

**Preciso de Fabric/Premium?** Não. PBIP funciona no Power BI Desktop gratuito. Fabric Git integration é opcional.

**A IA vai inventar números?** Ela não calcula números: escreve SQL/DAX. Por isso há o **Gate 2** —
você confere `trabalho-da-ia/conferencia.md` contra uma fonte confiável antes de publicar. Com o Power BI Modeling
MCP a IA também roda as consultas de validação.

**A IA pode apagar ou publicar algo sozinha?** O `AGENTS.md` proíbe publicar, mudar para `production` ou
agir fora da árvore governada. Mesmo assim, revise os diffs: tudo é texto versionado e reversível com Git.

**E se o PBIP não abrir no meu Desktop?** Os arquivos usam versões de schema antigas e estáveis,
validadas contra os schemas oficiais; o Desktop atualiza ao salvar. Use uma versão recente do Desktop.
Abra uma issue com a mensagem de erro e a saída do `pbw diagnostico` (sem dados sensíveis).

**"O caminho especificado, o nome do arquivo ou ambos são muito longos".** O Power BI Desktop não lê
arquivos com 260 caracteres ou mais, e o formato PBIR é fundo
(`…\2-power-bi\Nome.Report\definition\pages\<id>\visuals\<id>\visual.json`). Com o repositório em
uma pasta comprida (Área de Trabalho, OneDrive, SharePoint sincronizado) o limite estoura. Três saídas,
da mais simples à definitiva:

1. **Abra com `pbw abrir <dashboard>`.** Quando o caminho é longo demais, ele cria uma unidade virtual
   curta (ex.: `P:`) que aponta para a pasta do repositório e abre o projeto por ela. São os mesmos
   arquivos: nada é copiado. A unidade some ao reiniciar o Windows e o `pbw abrir` cria de novo.
   Para não usar a unidade: `pbw abrir <dashboard> --sem-atalho`.
2. **Mova o repositório para uma pasta curta**, como `C:\pbw` (feche o VS Code e o Power BI antes).
   O `pbw diagnostico` mostra quantos caracteres a pasta tem e se algum dashboard passa do limite.
3. **Use nomes curtos** para empresa, área, subárea e dashboard. O `pbw validar` (regra PBW025) avisa
   quando um dashboard passa do limite.

Ligar "caminhos longos" no Windows (registro `LongPathsEnabled`) ajuda o Git e o Python, mas não o
Power BI Desktop. Para o Git, rode uma vez: `git config --global core.longpaths true`.

**O que é a skill `powerbi-architect`? Preciso dela?** Não é obrigatória, mas é recomendada: ela ensina
à IA modelagem, DAX e design no nível de um especialista, e traz scripts que o `pbw` usa (`pbw auditar`,
`pbw previa`). Cada pessoa instala a sua: `pbw skill` mostra como.

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
