@echo off
setlocal

set "PROJECT_ROOT=%~dp0"
if "%PROJECT_ROOT:~-1%"=="\" set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"

set "ISS_FILE=%PROJECT_ROOT%\installer.iss"
set "DIST_EXE=%PROJECT_ROOT%\dist\TheTechGuy Image Editor.exe"
set "INSTALLER_EXE=%PROJECT_ROOT%\installer\TheTechGuy Image Editor Setup.exe"

if not exist "%DIST_EXE%" (
    echo Missing EXE. Build it first: %DIST_EXE%
    exit /b 1
)

echo Preparing bundled AI models...
python "%PROJECT_ROOT%\prepare_models.py"
if errorlevel 1 (
    echo Model preparation failed.
    exit /b 1
)

echo Preparing installer prerequisites...
python "%PROJECT_ROOT%\prepare_prereqs.py"
if errorlevel 1 (
    echo Prerequisite preparation failed.
    exit /b 1
)

set "ISCC="
for %%F in (
    "%ProgramFiles%\Inno Setup 6\ISCC.exe"
    "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
    "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
) do (
    if not defined ISCC if exist "%%~F" set "ISCC=%%~F"
)

if not defined ISCC (
    echo Could not find ISCC.exe for Inno Setup 6.
    exit /b 1
)

echo Using Inno Setup compiler:
echo %ISCC%
echo.

pushd "%PROJECT_ROOT%" || goto :pushd_error
call "%ISCC%" "%ISS_FILE%"
if errorlevel 1 goto :build_error
popd

echo.
if exist "%INSTALLER_EXE%" (
    echo Installer created:
    echo %INSTALLER_EXE%
    exit /b 0
)

echo Installer build finished but the output file was not found at %INSTALLER_EXE%
exit /b 1

:build_error
set "EXIT_CODE=%ERRORLEVEL%"
popd
echo Installer build failed with exit code %EXIT_CODE%.
exit /b %EXIT_CODE%

:pushd_error
echo Could not open project directory: %PROJECT_ROOT%
exit /b 1
