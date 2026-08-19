@echo off
chcp 65001 > nul
cd /d "%~dp0.."
title クリケア ホームページ バックアップ
cls
call "%~dp0_python.bat"
if errorlevel 1 goto :end
%PY% tools\backup.py
echo.
echo backups フォルダに保存しました。
:end
echo.
pause
