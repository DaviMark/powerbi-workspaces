@echo off
rem Atalho do Power BI Workspaces. Prompt: pbw <comando>   PowerShell: .\pbw <comando>
where py >nul 2>nul || goto python
py -3 "%~dp0_sistema\pbw.py" %*
exit /b %errorlevel%
:python
python "%~dp0_sistema\pbw.py" %*
exit /b %errorlevel%
