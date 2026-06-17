@echo off
setlocal
cd /d "%~dp0\.."
python scripts\validate_repository.py || exit /b 1
python scripts\selftest_creative_engine.py || exit /b 1
python scripts\smoke_test_engine.py || exit /b 1
python scripts\test_editing_actions.py || exit /b 1
python scripts\test_history.py || exit /b 1
python scripts\test_property_and_selection.py || exit /b 1
python scripts\capability_report.py docs\CAPABILITIES.md || exit /b 1
echo TTG Creative Studio alpha tests passed.
