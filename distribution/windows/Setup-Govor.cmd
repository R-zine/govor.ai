@echo off
setlocal
for %%I in ("%~dp0.") do set "GOVOR_INSTALL_ROOT=%%~fI"
set "PYTHONPATH=%GOVOR_INSTALL_ROOT%\app\apps\launcher\src;%GOVOR_INSTALL_ROOT%\app\packages\gateway_security\src"
"%GOVOR_INSTALL_ROOT%\runtime\python\python.exe" -m govor_launcher.cli --install-root "%GOVOR_INSTALL_ROOT%" doctor
if errorlevel 1 goto failure
rem --doctor-only is used by the release packager to exercise this exact learner entry point.
if /I "%~1"=="--doctor-only" exit /b 0
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%GOVOR_INSTALL_ROOT%\Install-Prerequisites.ps1" -InstallRoot "%GOVOR_INSTALL_ROOT%"
if errorlevel 1 goto failure
"%GOVOR_INSTALL_ROOT%\runtime\python\python.exe" -m govor_launcher.cli --install-root "%GOVOR_INSTALL_ROOT%" install-models
if errorlevel 1 goto failure
echo.
echo Setup completed. You may disconnect this PC from the internet and run Start-Govor.cmd.
pause
exit /b 0
:failure
echo.
echo Setup failed. No unverified model file was installed.
pause
exit /b 1
