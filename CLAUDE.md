# CLAUDE.md

@AGENTS.md

The full operating contract is in `AGENTS.md` (imported above). Load the `powerbi-architect` skill
for any Power BI work. Slash commands live in `.claude/commands/`.

At the start of EVERY session, before anything else (even if the first message is a request), run `python _sistema/pbw.py boas-vindas --verificar`; if it prints `PERGUNTAR`, your first reply is exactly: "Quer que eu te explique como o repositório funciona primeiro? Comandos, o que fica em cada pasta e tudo mais?" (details: `AGENTS.md › Session start`).
