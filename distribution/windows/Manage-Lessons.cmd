@echo off
setlocal
for %%I in ("%~dp0.") do set "GOVOR_INSTALL_ROOT=%%~fI"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%GOVOR_INSTALL_ROOT%\Import-Lessons.ps1" -InstallRoot "%GOVOR_INSTALL_ROOT%"
exit /b %ERRORLEVEL%
