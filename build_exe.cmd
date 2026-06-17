@echo off
setlocal

set "PROJECT_ROOT=%~dp0"
if "%PROJECT_ROOT:~-1%"=="\" set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"

set "SPEC_FILE=%PROJECT_ROOT%\Background Remover.spec"
set "DIST_EXE=%PROJECT_ROOT%\dist\TheTechGuy Image Editor.exe"
set "DIST_BACKEND_EXE=%PROJECT_ROOT%\dist\TheTechGuy Image Editor Backend.exe"
set "DIST_MODELS_DIR=%PROJECT_ROOT%\dist\models"
set "BUILD_DIR=%PROJECT_ROOT%\build\TheTechGuy Image Editor"
set "BACKEND_BUILD_DIR=%PROJECT_ROOT%\build\TheTechGuy Image Editor Backend"
set "LOGO_PNG=%PROJECT_ROOT%\resources\logo.png"
set "APP_ICON=%PROJECT_ROOT%\build_icon.ico"
set "SOURCE_MODELS_DIR=%PROJECT_ROOT%\models"

if exist "%LOGO_PNG%" (
    echo Generating build_icon.ico from resources\logo.png...
    python "%PROJECT_ROOT%\generate_build_icon.py"
    if errorlevel 1 (
        echo Icon generation failed.
        exit /b 1
    )
)

taskkill /F /T /IM "TheTechGuy Image Editor.exe" >nul 2>&1
taskkill /F /T /IM "TheTechGuy Image Editor Backend.exe" >nul 2>&1
taskkill /F /T /IM "Background Remover.exe" >nul 2>&1
taskkill /F /T /IM "Background Remover Backend.exe" >nul 2>&1
taskkill /F /T /IM "pyinstaller.exe" >nul 2>&1
if exist "%PROJECT_ROOT%\dist\Background Remover.exe" (
    del /F /Q "%PROJECT_ROOT%\dist\Background Remover.exe" >nul 2>&1
)
if exist "%PROJECT_ROOT%\dist\Background Remover Backend.exe" (
    del /F /Q "%PROJECT_ROOT%\dist\Background Remover Backend.exe" >nul 2>&1
)
if exist "%DIST_EXE%" (
    del /F /Q "%DIST_EXE%" >nul 2>&1
)
if exist "%DIST_BACKEND_EXE%" (
    del /F /Q "%DIST_BACKEND_EXE%" >nul 2>&1
)
if exist "%PROJECT_ROOT%\build\Background Remover" (
    rmdir /S /Q "%PROJECT_ROOT%\build\Background Remover" >nul 2>&1
)
if exist "%PROJECT_ROOT%\build\Background Remover Backend" (
    rmdir /S /Q "%PROJECT_ROOT%\build\Background Remover Backend" >nul 2>&1
)
if exist "%BUILD_DIR%" (
    rmdir /S /Q "%BUILD_DIR%" >nul 2>&1
)
if exist "%BACKEND_BUILD_DIR%" (
    rmdir /S /Q "%BACKEND_BUILD_DIR%" >nul 2>&1
)
if exist "%DIST_MODELS_DIR%" (
    rmdir /S /Q "%DIST_MODELS_DIR%" >nul 2>&1
)

echo Building EXE from:
echo %SPEC_FILE%
echo.

pushd "%PROJECT_ROOT%" || goto :pushd_error
call pyinstaller --noconfirm --clean "%SPEC_FILE%"
if errorlevel 1 goto :build_error
popd

if exist "%SOURCE_MODELS_DIR%" (
    xcopy "%SOURCE_MODELS_DIR%\*" "%DIST_MODELS_DIR%\" /E /I /Y >nul
)

echo.
if exist "%DIST_EXE%" if exist "%DIST_BACKEND_EXE%" (
    echo EXEs created:
    echo %DIST_EXE%
    echo %DIST_BACKEND_EXE%
    exit /b 0
)

echo PyInstaller finished but the EXE outputs were not found at:
echo %DIST_EXE%
echo %DIST_BACKEND_EXE%
exit /b 1

:build_error
set "EXIT_CODE=%ERRORLEVEL%"
popd
if exist "%DIST_EXE%" if exist "%DIST_BACKEND_EXE%" (
    echo PyInstaller returned exit code %EXIT_CODE%, but the EXE was created:
    echo %DIST_EXE%
    echo %DIST_BACKEND_EXE%
    exit /b 0
)
echo Build failed with exit code %EXIT_CODE%.
exit /b %EXIT_CODE%

:pushd_error
echo Could not open project directory: %PROJECT_ROOT%
exit /b 1
