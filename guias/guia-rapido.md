# Guia rápido

Para analistas de dados. Você não precisa programar: escreve o pedido, abre o Power BI para ver e
aprova. A IA faz o resto e roda os comandos.

## 0. O que instalar

| Ferramenta | Para quê |
|---|---|
| **Power BI Desktop** (Windows, versão recente) | abrir o `.pbip`, atualizar, conferir, exportar o `.pbit` |
| **VS Code** + uma IA | conversar com a IA: GitHub Copilot (modo agente), Claude Code, Cursor, Codex… |
| **Python 3.11+** ([python.org](https://www.python.org/downloads/)) | rodar o `pbw` (marque *Add Python to PATH* na instalação) |
| **Git** | guardar o histórico e compartilhar com o time |
| *Opcional:* Power BI Modeling MCP | a IA edita e testa o modelo dentro do Desktop |

No Power BI Desktop: **Arquivo › Opções › Recursos em versão prévia** → ative *Opção de salvamento do
Projeto do Power BI (.pbip)* e *Armazenar relatórios usando o formato de metadados aprimorado (PBIR)*
(nas versões recentes já vêm ligados).

## 1. Prepare o repositório

No GitHub, botão **Use this template** → crie um repositório **privado** da empresa e clone no VS Code
numa **pasta curta**, como `C:\pbw`. Evite a Área de Trabalho, o OneDrive e pastas sincronizadas do
SharePoint: o caminho fica comprido demais para o Power BI Desktop (limite de 260 caracteres do Windows)
e a sincronização disputa os arquivos com o Git.

```powershell
git config --global core.longpaths true
git clone https://github.com/<sua-empresa>/<seu-repositorio>.git C:\pbw
```

Depois, no terminal do VS Code (**Terminal › Novo terminal**), dentro da pasta:

```powershell
.\pbw diagnostico        # confere o ambiente (e se a pasta é curta o bastante)
.\pbw instalar-hooks     # impede que dados e senhas entrem no Git
.\pbw skill              # mostra como instalar a skill powerbi-architect (recomendado)
```

> No macOS, Linux ou Git Bash, troque `.\pbw` por `./pbw`.

## 2. Diga onde estão os dados

```powershell
copy conexoes\sqlserver.example.toml conexoes\erp.toml
# abra conexoes\erp.toml e preencha servidor e banco (nunca a senha)
.\pbw conexoes
```

Em `workspaces.toml`, use `[defaults] connection = "erp"`. Detalhes: [`conexoes/LEIA-ME.md`](../conexoes/LEIA-ME.md).

## 3. Identidade visual (uma vez por empresa)

1. Em `identidade-visual/`, renomeie `nome-da-empresa` para o nome da sua empresa — o mesmo que vai
   usar em `dashboards/` (ex.: `minha-empresa`).
2. Coloque o logo em `1-cole-aqui/logo/`, o manual em `1-cole-aqui/manual-da-marca/`, cores e fontes
   em `1-cole-aqui/cores-e-fontes/`.
3. Peça à IA: **"crie a identidade visual da empresa minha-empresa"**.

Todo dashboard dessa empresa passa a usar essas cores — os que já existem e os próximos.

## 4. Primeiro dashboard

```powershell
.\pbw novo "Minha Empresa/Financeiro/Contas a Receber/Aging de Títulos"
.\pbw abrir aging-de-titulos
```

O Power BI Desktop abre o projeto — ainda com uma página de rascunho. Agora:

1. **Preencha o formulário** `dashboards/…/aging-de-titulos/1-seu-pedido/PEDIDO.md`. É o único arquivo
   que você escreve:
   - **seção 3** — as perguntas que o dashboard responde;
   - **seção 4 — Regras de negócio** — como cada número é calculado e o que não entra;
   - **seção 5 — Visuais que eu quero** — uma linha por coisa que você quer ver (o tipo de gráfico é opcional).

   SQL que você já usa, prints e PDFs vão em `1-seu-pedido/anexos/`. Cores e logo **não** vão aqui:
   vêm da identidade da empresa (passo 3).
2. **Peça à IA:** *"crie o dashboard aging-de-titulos"*.
3. **Gate 1 — protótipo.** A IA transforma o seu pedido em um desenho (modelo, métricas, páginas),
   resume no chat e desenha o protótipo. Feche e reabra no Power BI (`.\pbw abrir aging-de-titulos`): cada página mostra
   caixas cinza com o visual planejado. Quer mudar algo? Diga à IA (*"troque o gráfico de pizza por
   barras"*, *"junte as duas primeiras páginas"*) — ela atualiza o desenho e o protótipo. Quando estiver
   bom, diga **"aprovado"**.
4. **A IA constrói:** SQL, modelo, medidas e páginas reais, no lugar das caixas cinza.
5. **Gate 2 — números.** Abra de novo, informe a credencial do banco quando o Power BI pedir, clique em
   **Atualizar** e confira os números que a IA lista no chat. Estando certos, diga
   **"números conferidos"**.
6. **Entrega:** **Arquivo › Exportar › Modelo do Power BI** → salve em `3-entrega/AgingDeTitulos.pbit`.
   Para publicar, veja [publicacao.md](publicacao.md).

> Feche o projeto no Power BI Desktop enquanto a IA edita os arquivos e reabra depois. Se você editar
> no Desktop, salve (**Ctrl+S**) antes de pedir mudanças à IA.

## 5. Refazer um dashboard antigo

No Power BI Desktop, abra o `.pbix` antigo › **Arquivo › Exportar › Modelo do Power BI**. Coloque o
`.pbit` em `refatorar/<empresa>/<área>/<subárea>/<dashboard>/` e peça:
**"refatore os dashboards de refatorar/"**. Detalhes em [`refatorar/LEIA-ME.md`](../refatorar/LEIA-ME.md).

## Precisa de ajuda?

- `.\pbw --help` lista todos os comandos; `.\pbw validar` diz o que falta em cada dashboard.
- Perguntas frequentes: [faq.md](faq.md) · Regras: [governanca.md](governanca.md).
