# dashboards

Um dashboard por pasta, organizado em empresa, área e subárea.

## Novo dashboard

1. Duplique `nome-da-empresa/nome-da-area/nome-da-subarea/nome-do-dashboard`.
2. Renomeie cada pasta (ex.: `acme/financeiro/contas-a-receber/aging-de-titulos`).
3. Preencha `1-seu-pedido/PEDIDO.md`.
4. Peça à IA: **"crie o dashboard aging-de-titulos"**.

A IA ajusta os nomes do projeto Power BI e mantém o seu pedido. Pelo terminal, o mesmo resultado:
`pbw novo "Acme/Financeiro/Contas a Receber/Aging de Títulos"`.

## Dentro de cada dashboard

```
<dashboard>/
├── LEIA-ME.md          comece aqui
├── 1-seu-pedido/       você: PEDIDO.md e anexos/
├── 2-power-bi/         abra o .pbip aqui
├── 3-entrega/          o .pbit final
└── trabalho-da-ia/     a IA cuida
```

Cores e logo vêm de `identidade-visual/<empresa>/`, para todos os dashboards da empresa.
Lista de todos os dashboards: [`CATALOGO.md`](CATALOGO.md). Exemplo completo:
[`acme/financeiro/contas-a-receber/aging-de-titulos`](acme/financeiro/contas-a-receber/aging-de-titulos/LEIA-ME.md).
