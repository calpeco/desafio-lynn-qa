@echo off
rem Windows (cmd ou duplo clique): roda o setup.ps1 sem depender da politica de execucao do PowerShell.
rem Aceita os mesmos parametros: setup.cmd -SkipBrowser | -Recreate | -SystemSitePackages
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1" %*
exit /b %ERRORLEVEL%
