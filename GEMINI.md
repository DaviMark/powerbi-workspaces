# GEMINI.md

Read and follow `AGENTS.md` in the repository root — it is the operating contract for every AI agent
in this repository. Load the `powerbi-architect` skill (in `.agents/skills/` or `.gemini/skills/`) for
any Power BI work.

At the start of EVERY session, before anything else (even if the first message is a request), run `python _sistema/pbw.py boas-vindas --verificar`; if it prints `PERGUNTAR`, your first reply is exactly: "Quer que eu te explique como o repositório funciona primeiro? Comandos, o que fica em cada pasta e tudo mais?" (details: `AGENTS.md › Session start`).
