@echo off
chcp 65001 > nul
cd /d "%~dp0.."
title クリケア ホームページ バックアップ
where py >nul 2>nul
if %errorlevel%==0 (set PY=py -3) else (set PY=python)
%PY% tools\backup.py
echo.
pause
