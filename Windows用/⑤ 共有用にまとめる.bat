@echo off
chcp 65001 > nul
cd /d "%~dp0.."
title クリケア ホームページ 共有用の書き出し
cls
echo ======================================
echo   他のパソコンへ渡すファイルを作ります
echo ======================================
echo.
call "%~dp0_python.bat"
if errorlevel 1 goto :end
%PY% tools\export.py
:end
echo.
pause
