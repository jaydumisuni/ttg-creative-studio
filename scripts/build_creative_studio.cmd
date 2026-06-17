@echo off
setlocal
cd /d "%~dp0\.."
python -m PyInstaller --noconfirm --name "TTG Creative Studio" --windowed --paths src scripts\launch_creative_studio.py
if errorlevel 1 exit /b 1
echo Built TTG Creative Studio.
