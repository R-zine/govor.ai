@echo off
setlocal
for %%I in ("%~dp0.") do set "GOVOR_INSTALL_ROOT=%%~fI"
if /I "%~1"=="--doctor-only" goto doctor
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%GOVOR_INSTALL_ROOT%\Apply-Govor-Patch.ps1" -InstallRoot "%GOVOR_INSTALL_ROOT%"
if errorlevel 1 goto failure
echo.
echo The application patch completed successfully.
pause
exit /b 0
:failure
echo.
echo The application patch was not installed. Review the message above; failed changes were rolled back.
pause
exit /b 1
:doctor
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%GOVOR_INSTALL_ROOT%\Apply-Govor-Patch.ps1" -InstallRoot "%GOVOR_INSTALL_ROOT%" -DoctorOnly
exit /b %ERRORLEVEL%
