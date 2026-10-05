@echo off
chcp 65001 > nul
cd /d "%~dp0.."
title Kuricare - Send to GitHub
cls

call "%~dp0_python.bat"
if errorlevel 1 goto :end

%PY% tools\send_to_github.py

:end
echo.
pause
