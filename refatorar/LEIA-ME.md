# refatorar

Para refazer no padrão um dashboard antigo.

1. No Power BI Desktop, abra o `.pbix` antigo: **Arquivo › Exportar › Modelo do Power BI** e salve o `.pbit`.
2. Renomeie as pastas `nome-da-empresa/nome-da-area/nome-da-subarea/nome-do-dashboard` para o caminho
   que o dashboard deve ter (ex.: `acme/financeiro/contas-a-receber/aging`) e coloque o `.pbit` dentro.
   Notas, prints e consultas podem ir junto.
3. Peça à IA: **"refatore os dashboards de refatorar"**.

O dashboard novo aparece em `dashboards/`, no mesmo caminho, já pronto para abrir. Nada desta pasta vai
para o Git.

## Detalhes

Para rodar sem a IA:

```bash
pbw refatorar --listar   # o que está esperando
pbw refatorar          # move, extrai e prepara o plano
```

O CLI lê o `.pbit` **sem abrir o Power BI e sem ler dados**, e cria, dentro do novo dashboard:

| Arquivo | Conteúdo |
|---|---|
| `trabalho-da-ia/legado/extracao/summary.md` | diagnóstico: etapas de Power Query, colunas sem uso, auto date/time, relacionamentos bidirecionais, colunas calculadas em fatos, medidas sem descrição |
| `trabalho-da-ia/legado/extracao/model.md` | tabelas, colunas, relacionamentos (diagrama), RLS |
| `trabalho-da-ia/legado/extracao/measures.md` | todas as medidas DAX |
| `trabalho-da-ia/legado/extracao/power-query.md` | todo o M (hosts e IPs mascarados) |
| `trabalho-da-ia/legado/extracao/report.md` | páginas, visuais e campos usados |
| `trabalho-da-ia/legado/extracao/extraction.json` | tudo acima, estruturado para a IA |
| `trabalho-da-ia/legado/PLANO.md` | checklist da refatoração |

Notas, prints e consultas que estavam junto do `.pbit` vão para `1-seu-pedido/anexos/`.

A IA então segue o fluxo **REFACTOR** do `AGENTS.md`: reconstrói as perguntas de negócio, escreve o
desenho e o protótipo (você abre, ajusta e aprova), move toda a lógica para SQL, reescreve as medidas
com paridade numérica e redesenha as páginas com a identidade visual da empresa.

## Como gerar o arquivo .pbit

1. Abra o `.pbix` no **Power BI Desktop**.
2. **Arquivo › Exportar › Modelo do Power BI** (*File › Export › Power BI template*).
3. Escreva uma descrição curta (opcional) › **OK** › salve como `<Nome>.pbit`.

O `.pbit` guarda modelo, medidas, Power Query e layout — **sem as linhas de dados**. Atenção:
tabelas criadas com **"Inserir dados"** ficam embutidas no arquivo; o `pbw seguranca` avisa quando encontra.

> Alternativa: **Arquivo › Salvar como › Projeto do Power BI (.pbip)** e coloque a pasta do projeto
> aqui (`pbw extrair` lê `.pbit`; para `.pbip` a IA lê os arquivos do modelo e do relatório diretamente).
