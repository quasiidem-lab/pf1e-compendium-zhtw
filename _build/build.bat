@echo off
rem PF1 Foundry compendium zh-TW build. verify must PASS before shipping.
setlocal
set "PYTHONIOENCODING=utf-8"
cd /d "%~dp0"
echo [1/2] build_compendium.py
python build_compendium.py || goto fail
echo [2/2] verify_compendium.py
python verify_compendium.py || goto fail
echo.
echo Done.
goto :eof
:fail
echo.
echo FAILED. Do not ship the output.
exit /b 1
