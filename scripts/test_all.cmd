@echo off
setlocal
cd /d "%~dp0\.."
python scripts\validate_repository.py || exit /b 1
python scripts\release_check.py || exit /b 1
python scripts\selftest_creative_engine.py || exit /b 1
python scripts\smoke_test_engine.py || exit /b 1
echo TTG Creative Studio tests passed.
