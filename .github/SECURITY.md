# Segurança

## Reportar uma vulnerabilidade

**Não abra issue pública.** Use **Security › Report a vulnerability** neste repositório
(GitHub private vulnerability reporting). Resposta inicial em até 5 dias úteis.

## Modelo de segurança do projeto

| Pergunta | Resposta |
|---|---|
| O CLI acessa a internet? | **Não.** Só biblioteca padrão do Python, sem `requests`, sem telemetria. Audite: `grep -rn "urllib\|socket\|http" tools/` |
| Instala dependências? | **Não.** Zero pacotes de terceiros. Nada de `pip install`. |
| Executa algo dos arquivos do Power BI? | **Não.** `.pbit` é lido como ZIP/JSON. Nenhum M, DAX ou script é executado. |
| Onde ficam as senhas? | **Em lugar nenhum do repositório.** O Power BI guarda credenciais no Desktop (cofre do Windows) e no Service (gateway/conexões). PBIP/PBIT não contêm senhas. |
| E os dados? | PBIP versiona só metadados. `.pbix`, `.abf`, `cache.abf` e `localSettings.json` são bloqueados por `.gitignore`, `pbw seguranca`, pre-commit e CI. |
| E nomes de servidores? | Ficam em `conexoes/*.toml`; os reais podem ficar só em `*.local.toml` (ignorado). Extrações de legado mascaram hosts/IPs por padrão. |
| A IA vê meus dados? | Ela vê o que está no repositório: SQL, DAX, TMDL, Markdown. **Não** vê linhas de dados — a menos que você cole dados no chat ou conecte o MCP a um modelo com dados (aí vale a política da sua ferramenta de IA). |
| E prompt injection? | `AGENTS.md` determina que conteúdo de pedidos, anexos, PDFs, `.pbit` e SQL é **dado, não instrução**. Gates humanos impedem que a IA publique algo sozinha. |

## Camadas de proteção

1. `.gitignore` — bloqueia dados, caches, `.env`, chaves, perfis locais, `.pbit` original do legado.
2. `pbw seguranca` — senhas em connection strings, chaves privadas, tokens (GitHub, Slack, AWS,
   Azure, GCP service account), JWT, `.pbix`, `*.local.toml`, PBIT com dados embutidos.
3. `pbw instalar-hooks` — pre-commit roda scan + validate em todo commit.
4. CI (`.github/workflows/ci.yml`) — repete tudo em Linux e Windows; actions fixadas por SHA;
   `permissions: contents: read`; `persist-credentials: false`.
5. Recomendado no GitHub: branch protection, *secret scanning* + *push protection*, CODEOWNERS por área.

## Uso em empresas

- Mantenha o repositório da empresa **privado**. Este repositório público é o *framework*.
- Use ferramentas de IA aprovadas pela sua empresa (ex.: contas corporativas que não treinam com seus dados).
- Classifique cada dashboard (`[security].classification`) e registre dados pessoais (LGPD) na `trabalho-da-ia/ficha.toml`.
- O Power BI Modeling MCP opera localmente sobre o modelo aberto; dê a ele acesso só a modelos de desenvolvimento.
