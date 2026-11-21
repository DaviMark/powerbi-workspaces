# Governança

## Ciclo de vida (`trabalho-da-ia/ficha.toml › status`)

`draft` → `development` → `review` → `production` → `deprecated`

- **review/production** exigem `business_owner` e perfil de conexão real (não `*.example`).
- Só um humano muda para `production` (regra do `AGENTS.md`).
- Versão SemVer: MAJOR quebra uso (página/métrica removida), MINOR nova análise, PATCH ajuste.

## Gates

| Gate | Quando | Quem aprova | Evidência |
|---|---|---|---|
| 1 · Desenho + protótipo | antes de qualquer SQL/medida/visual real | dono do negócio (abre o `.pbip` e vê as páginas de protótipo) | `trabalho-da-ia/desenho.md › Aprovação` |
| 2 · Números | antes de `review` | dono do negócio | `trabalho-da-ia/conferencia.md` preenchido |

## Regras do `pbw validar`

| Regra | Nível | O que verifica |
|---|---|---|
| PBW001 | erro | estrutura de pastas, nada solto, pastas obrigatórias |
| PBW002 | erro | nomes de pasta em slug |
| PBW003 | erro | `trabalho-da-ia/ficha.toml` válido, `id` = caminho, status, dono em review/produção |
| PBW004 | erro | perfil de conexão existe; não usar exemplo em review/produção |
| PBW006 | aviso | `LEIA-ME.md` com seções obrigatórias, `trabalho-da-ia/historico.md`, desenho completo |
| PBW007 | erro | **o `.pbip` abre**: exatamente um `.pbip` na pasta do dashboard, relatório e modelo existem e se apontam, todo JSON válido, `pages.json` coerente, TMDL legível |
| PBW008 | erro | servidor/projeto fixo no Power Query (use parâmetros) |
| PBW009 | aviso | etapas e transformações no Power Query |
| PBW010–012 | aviso | medidas/tabelas sem descrição, formato ou pasta |
| PBW013 | aviso | tabelas de fonte acima do limite (`max_tables`) |
| PBW014 | erro | página de documentação ausente, JSON inválido, formato PBIR-Legacy |
| PBW015 | aviso | auto date/time ligado |
| PBW016 | aviso | relacionamentos bidirecionais ou muitos-para-muitos |
| PBW017 | aviso | visual customizado sem decisão registrada |
| PBW018 | erro/aviso | classificação inválida; confidencial sem RLS |
| PBW019 | erro/aviso | colunas calculadas (erro em fatos) |
| PBW020 | aviso | SQL ↔ TMDL fora de sincronia (tabelas e colunas) |
| PBW023 | erro | tabela de fonte sem colunas declaradas |
| PBW024 | info/erro | páginas ainda em protótipo (erro em review/produção) |
| SEC* | erro | segredos, `.pbix`, `.abf`, perfis locais, PBIT com dados embutidos |
| PBW030 | info | itens aguardando em `refatorar/` |

Ajuste limites em `workspaces.toml › [governance]`. Use `--strict` para tratar avisos como erros.

## No GitHub

- Branch protection em `main`: PR obrigatório + check `governance` verde.
- `CODEOWNERS` por área (`/dashboards/<empresa>/financeiro/ @time-financeiro`).
- Secret scanning + push protection ligados.
