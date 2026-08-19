@echo off
chcp 65001 > nul
cd /d "%~dp0.."
title クリケア ホームページ 点検
cls
call "%~dp0_python.bat"
if errorlevel 1 goto :end
%PY% build.py
echo.
%PY% tools\check.py
:end
echo.
echo --------------------------------------
echo 確認が終わったら、この画面を閉じてください。
pause
