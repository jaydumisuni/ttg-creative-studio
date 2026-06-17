@echo off
setlocal

set "PROJECT_ROOT=%~dp0"
if "%PROJECT_ROOT:~-1%"=="\" set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"

call "%PROJECT_ROOT%\build_exe.cmd"
if errorlevel 1 exit /b %ERRORLEVEL%

echo.
call "%PROJECT_ROOT%\build_installer.cmd"
exit /b %ERRORLEVEL%
