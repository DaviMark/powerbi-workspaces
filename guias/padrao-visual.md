# Padrão visual

Todo dashboard segue este padrão, com as cores, fontes e logo da empresa (`identidade-visual/<empresa>/`).
Nada de visual genérico: o relatório deve parecer um produto feito para aquela empresa.

## 1. A moldura (igual em todas as páginas)

```
┌──────────────┬───────────────────────────────────────────────────────────────────┐
│ EMPRESA      │ Relatório  ›  Página                       [ Período ▾ ] [ Filtros ] │  barra superior, 52 px, branca
│              ├───────────────────────────────────────────────────────────────────┤
│ RELATÓRIO    │ Título da página (conclusão)                         Atualizado em │
│ ▌Visão geral │ subtítulo: período e escopo                                        │
│  Clientes    │ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐            │  cartões de KPI
│  Cancelam.   │ │ Rótulo    │ │           │ │           │ │           │            │
│              │ │ R$ 486 mil│ │           │ │           │ │           │            │
│ APOIO        │ │ +4,3% vs. │ │           │ │           │ │           │            │
│  Documentação│ └───────────┘ └───────────┘ └───────────┘ └───────────┘            │
│              │ ┌──────────────────────────┐ ┌──────────────────────────┐          │  cartões de gráfico
│ ┌──────────┐ │ │ Título         [A | B]   │ │ Título                   │          │
│ │ Alerta   │ │ │ legenda                  │ │                          │          │
│ │ [Abrir]  │ │ └──────────────────────────┘ └──────────────────────────┘          │
└──────────────┴───────────────────────────────────────────────────────────────────┘
  barra lateral 200 px na cor mais escura da marca
```

- **Barra lateral** (200 px, cor `sidebar` da identidade): nome ou logo da empresa no topo; seção
  RELATÓRIO com as páginas (navegador de páginas, página ativa com fundo `sidebar_active`); seção APOIO
  com Documentação. Opcional: um cartão de alerta no rodapé que leva a uma página (ex.: "Assinantes em
  risco").
- **Barra superior** (52 px, branca): caminho `Relatório › Página` à esquerda; à direita, no máximo dois
  controles: período (segmentação em lista suspensa) e um botão Filtros que abre o painel de filtros.
- **Conteúdo**: fundo `canvas`, margem de 20 px, espaço de 16 px entre cartões, tudo em múltiplos de 8 px.
- **Capa** (opcional, só na página inicial): faixa de 112 px com imagem da marca, saudação e "Atualizado em".

O protótipo (`pbw prototipo`) já desenha a moldura. Na construção real, a navegação vira clicável
(navegador de páginas ou botões) e os controles de período e filtros viram segmentação e botão de verdade.

## 2. Componentes

**Cartão de KPI** — rótulo (10 pt, cor `text_muted`), valor (24 pt seminegrito), linha fina, variação
contra o período anterior: seta em quadrado + percentual + "vs. mês anterior". Verde = bom, vermelho = ruim,
segundo o sentido da métrica (cancelamento subindo é vermelho). Sempre 4 cartões por linha, no máximo 6.

**Cartão de gráfico** — título à esquerda (12 pt seminegrito) que diz o que se vê; legenda logo abaixo do
título, à esquerda; alternador à direita quando o mesmo gráfico tem duas leituras (ex.: Receita |
Assinantes, por parâmetro de campo); rótulos de dados no lugar de eixos; sem linhas de grade.

**Cores nos gráficos** — a escala `ramp` da marca: a série principal no tom mais escuro, as demais em
tons mais claros. Comparação (ex.: canceladas × novas) em cinza neutro. Verde e vermelho só para bom e ruim.
Linha de meta tracejada em cinza com rótulo ("Meta: 3,5%").

**Barras de ranking** — ordenadas do maior para o menor; o item em foco no tom escuro, os outros no tom
mais claro da escala; valor no fim da barra.

**Mapa de calor** (matriz) — formatação condicional de fundo com a escala `ramp`; texto branco nas
células escuras.

**Tabela de acompanhamento** — sem grade vertical, linhas alternadas suaves, status em texto colorido
(vermelho "Última tentativa", âmbar "Nova tentativa", verde "Paga"), no máximo 6 colunas.

## 3. O que nunca aparece

- Paleta padrão do Power BI, fundo cinza do Power BI, fonte DIN genérica.
- Títulos de eixo, linhas de grade, bordas pesadas, sombras, 3D, gradientes.
- Pizza com mais de 3 fatias, legenda à direita, segmentações empilhadas na página.
- Visuais desalinhados ou de alturas diferentes na mesma linha.
- Mais de 8 visuais de dados por página.

## 4. De onde vem cada cor

| Token da identidade | Onde aparece |
|---|---|
| `sidebar`, `sidebar_text`, `sidebar_muted`, `sidebar_active` | barra lateral |
| `canvas` | fundo da página |
| `surface`, `border` | cartões |
| `text`, `text_muted` | títulos, valores, rótulos |
| `ramp` | séries, mapas de calor, rankings |
| `positive`, `negative`, `warning` | variações e status |

Para mudar as cores de todos os dashboards de uma empresa, atualize a identidade visual e peça à IA:
"aplique a identidade visual da empresa" (`pbw identidade <empresa>`).
