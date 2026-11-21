# Apresentação do repositório

Roteiro que a IA segue quando o analista aceita a explicação do início da sessão. Cada parte é uma
mensagem curta: a IA explica, pergunta se ficou claro e só então segue para a próxima. Sem jargão,
sem emojis, em português.

## 1. A ideia (uma frase)

"Você descreve o dashboard num formulário, eu construo no padrão da empresa, e você vê tudo no
Power BI antes de aprovar."

Sugira abrir o guia visual: `index.html`, na raiz, com dois cliques.

## 2. As pastas que importam

| Pasta | Para que serve |
|---|---|
| `dashboards/` | os dashboards, por empresa, área e subárea |
| `identidade-visual/` | cores e logo de cada empresa; vale para todos os dashboards dela |
| `refatorar/` | onde se coloca um dashboard antigo (`.pbit`) para refazer no padrão |
| `conexoes/` | o endereço dos bancos de dados, nunca a senha |
| `guias/` | passo a passo e perguntas frequentes |
| `_sistema/` | o motor; o analista não precisa abrir |

Pastas que começam com `nome-da` são modelos prontos: duplica-se e renomeia.

## 3. Dentro de um dashboard

| Pasta | Quem usa | Para quê |
|---|---|---|
| `1-seu-pedido/` | o analista | `PEDIDO.md` (objetivo, perguntas, regras de negócio, visuais que quer) e `anexos/` |
| `2-power-bi/` | o analista | o `.pbip`, que abre com dois cliques no Power BI Desktop |
| `3-entrega/` | o analista | o `.pbit` final para publicar |
| `trabalho-da-ia/` | a IA | consultas, desenho, conferência, histórico; não precisa abrir |

Mostre o exemplo pronto: `dashboards/acme/financeiro/contas-a-receber/aging-de-titulos/`.

## 4. Como um dashboard nasce

1. O analista preenche o pedido.
2. A IA desenha as páginas e gera o protótipo; o analista abre no Power BI e aprova (aprovação 1).
3. A IA constrói consultas, medidas e gráficos.
4. O analista atualiza no Power BI e confere os números (aprovação 2).
5. O analista exporta o `.pbit` para `3-entrega/` e publica.

## 5. Identidade visual

Uma vez por empresa: renomear `identidade-visual/nome-da-empresa`, colocar logo, manual e cores em
`1-cole-aqui/` e pedir "crie a identidade visual da empresa". Vale para todos os dashboards dela,
inclusive os futuros.

## 6. Comandos

Quase sempre a IA roda. Os que o analista pode querer usar (no PowerShell, com `.\` antes):

| Comando | O que faz |
|---|---|
| `pbw abrir <dashboard>` | abre o dashboard no Power BI Desktop |
| `pbw novo "Empresa/Área/Subárea/Dashboard"` | cria um dashboard pelo terminal |
| `pbw validar` | confere se está tudo certo |
| `pbw boas-vindas` | mostra por onde começar |

Lista completa: `guias/comandos.md`.

## 7. A skill Power BI Architect

O repositório diz onde e quando; a skill ensina a IA a fazer no nível de um especialista e mantém um
mapa dos dashboards para responder mais rápido. Se não estiver instalada (`.claude/skills/`,
`.github/skills/` ou `.agents/skills/` sem `powerbi-architect`), explique como instalar:
`guias/ia-no-vscode.md`.

## 8. Próximo passo

Pergunte o que o analista quer fazer agora: criar a identidade da empresa, pedir o primeiro dashboard
ou refazer um antigo. Se ele já tinha feito um pedido na primeira mensagem, volte a ele.
