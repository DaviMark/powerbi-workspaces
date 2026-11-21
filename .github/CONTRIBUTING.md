# Contribuindo

Obrigado! Toda contribuição é bem-vinda: conectores, regras de governança, templates, traduções, docs.

1. Faça um fork e crie uma branch: `git checkout -b feat/conector-redshift`.
2. Mantenha **zero dependências** e **zero rede** no CLI (só biblioteca padrão do Python 3.11+).
3. Rode antes do PR:
   ```bash
   python -m unittest discover -s _sistema/testes -v
   pbw seguranca
   pbw validar --strict
   ```
4. Exemplos sempre fictícios — nunca dados, hosts ou nomes reais de empresas.
5. Arquivos para IA (`AGENTS.md`, instruções) em inglês; documentação para pessoas em português (+ `guias/README.en.md`).
6. Descreva o *porquê* no PR. Mudanças em regras de governança precisam de teste.

Novo conector: adicione em `_sistema/workspaces/connectors.py` (`CONNECTORS`), um `*.example.toml` em
`conexoes/`, uma linha na tabela de `conexoes/LEIA-ME.md` e um teste.
