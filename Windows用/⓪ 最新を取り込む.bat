@echo off
chcp 65001 > nul
cd /d "%~dp0.."
title Kuricare - Pull from GitHub
cls

call "%~dp0_python.bat"
if errorlevel 1 goto :end

%PY% tools\pull_from_github.py

:end
echo.
pause
