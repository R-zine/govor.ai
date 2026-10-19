@echo off
setlocal
for %%I in ("%~dp0.") do set "GOVOR_INSTALL_ROOT=%%~fI"
set "PYTHONPATH=%GOVOR_INSTALL_ROOT%\app\apps\launcher\src;%GOVOR_INSTALL_ROOT%\app\packages\gateway_security\src"
rem Keep learner-facing startup and pairing details immediately visible when output is redirected
rem by the clean-machine acceptance harness or a support log collector.
set "PYTHONUNBUFFERED=1"
rem --doctor-only is used by the release packager to exercise this exact learner entry point.
if /I not "%~1"=="--doctor-only" goto start
"%GOVOR_INSTALL_ROOT%\runtime\python\python.exe" -m govor_launcher.cli --install-root "%GOVOR_INSTALL_ROOT%" doctor
exit /b %ERRORLEVEL%
:start
rem Forward optional launcher arguments. The M8 clean-VM fixture uses --smoke-seconds so it can
rem exercise this learner-facing entry point and still prove deterministic process teardown.
"%GOVOR_INSTALL_ROOT%\runtime\python\python.exe" -m govor_launcher.cli --install-root "%GOVOR_INSTALL_ROOT%" start %*
if errorlevel 1 (
  echo.
  echo govor.ai could not start. Review the message above and logs under %%LOCALAPPDATA%%\govor.ai\logs.
  pause
)
