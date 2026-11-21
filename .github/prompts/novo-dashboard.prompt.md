---
agent: agent
argument-hint: "caminho do dashboard ou descrição"
description: "Cria um dashboard Power BI governado, do pedido ao relatório"
---
Siga o workflow **A. NEW dashboard** do `AGENTS.md` (fases 0→7, com Gate 1 e Gate 2) para o dashboard informado.
Se a pasta não existir, crie com `pbw novo "<Empresa>/<Área>/<Subárea>/<Dashboard>"`.
Carregue a skill `powerbi-architect` se estiver disponível. No Gate 1, escreva `trabalho-da-ia/desenho.md`, rode
`pbw prototipo <dashboard>`, diga ao analista para abrir com `pbw abrir <dashboard>` e peça aprovação.
