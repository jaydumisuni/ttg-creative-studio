@echo off
setlocal
cd /d "%~dp0\.."
call scripts\test_alpha.cmd || exit /b 1
call scripts\build_creative_studio.cmd || exit /b 1
echo Core build completed. Compile installer\creative_studio_core.iss with Inno Setup to create the small installer.
