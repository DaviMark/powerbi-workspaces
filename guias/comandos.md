# Comandos

Na maior parte do tempo, quem roda os comandos é a IA. Eles estão aqui para quando você quiser
fazer algo direto.

Abra o terminal do VS Code na pasta do repositório. No PowerShell, escreva `.\pbw`; no macOS, no
Linux ou no Git Bash, `./pbw`. Onde aparece `<dashboard>`, use o nome da pasta do dashboard (ex.:
`aging-de-titulos`).

| Comando | O que faz |
|---|---|
| `pbw novo "<Empresa>/<Área>/<Subárea>/<Dashboard>"` | cria um dashboard, já pronto para abrir |
| `pbw abrir <dashboard>` | abre o dashboard no Power BI Desktop |
| `pbw prototipo <dashboard>` | redesenha as páginas de rascunho a partir do desenho aprovado |
| `pbw refatorar` | traz os `.pbit` da pasta `refatorar/` para `dashboards/` |
| `pbw identidade <empresa>` | aplica a identidade visual da empresa em todos os dashboards dela |
| `pbw conexoes` | lista as conexões configuradas |
| `pbw conectar <dashboard> -c <conexão>` | troca a fonte de dados de um dashboard |
| `pbw sincronizar-sql <dashboard>` | grava as consultas SQL no modelo |
| `pbw documentar` | atualiza o dicionário de cada dashboard e o catálogo |
| `pbw validar` | confere as regras, inclusive se cada dashboard abre |
| `pbw seguranca` | procura senhas e arquivos com dados antes de enviar ao Git |
| `pbw diagnostico` | confere o ambiente |
| `pbw boas-vindas` | mostra por onde começar |
| `pbw instalar-hooks` | ativa a verificação automática a cada commit |

Os nomes em inglês também funcionam (`new`, `open`, `validate`…). Todos os comandos aceitam `--help`.
As regras do `pbw validar` estão em [governanca.md](governanca.md).
