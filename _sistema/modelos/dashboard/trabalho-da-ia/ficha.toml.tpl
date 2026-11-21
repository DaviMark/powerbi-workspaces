# Ficha do dashboard — lida pelo CLI, pela IA e pelo catálogo. Sem senhas aqui.

[dashboard]
id = "{{id}}"                       # = caminho da pasta (empresa.área.subárea.dashboard)
name = "{{name}}"
description = ""                    # 1 frase: que decisão este dashboard apoia?
status = "draft"                    # draft (rascunho) | development | review (revisão) | production | deprecated
version = "0.1.0"                   # 1.0.0 = primeira entrega; 1.1.0 = nova análise; 1.0.1 = ajuste
created = "{{date}}"
origin = "{{origin}}"               # new (novo) | refactor (refatorado de um legado)

[ownership]
company = "{{company}}"
area = "{{area}}"
subarea = "{{subarea}}"
business_owner = ""                 # quem responde pelas regras de negócio (obrigatório em review/production)
technical_owner = ""
audience = ""                       # quem usa: diretoria, analistas, operação...

[data]
connection = "{{connection}}"       # perfil em conexoes/  →  pbw conexoes
storage_mode = "import"             # import | directquery | composite
refresh = ""                        # ex.: "diário 06:00", "a cada 1h em horário comercial"
incremental_refresh = false

[security]
classification = "internal"         # public | internal | confidential | restricted
contains_pii = false                # dados pessoais (LGPD)? Se sim, documente base legal e mascaramento
rls = false                         # Row-Level Security (cada pessoa vê só o que pode)
rls_rule = ""                       # ex.: "gestor vê apenas a própria filial"

[design]
brand = "{{brand}}"                 # identidade visual = a da empresa (identidade-visual/<empresa>/), automática
pages = []                          # preenchido pela IA a partir de desenho.md
custom_visuals = []                 # só com justificativa em desenho.md (Decisões)

[publish]
workspace = ""                      # workspace do Power BI Service / Fabric
app = ""
