@echo off
chcp 65001 > nul
cd /d "%~dp0.."
title クリケア ホームページ 編集画面
cls
echo ======================================
echo   クリケア ホームページ 編集画面
echo ======================================
echo.

call "%~dp0_python.bat"
if errorlevel 1 goto :end

rem すでに動いている編集画面があれば止めてから起動する
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*admin*server.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" > nul 2>&1
timeout /t 1 /nobreak > nul

echo ブラウザが自動で開きます。
echo 編集が終わったら、この黒い画面を閉じてください。
echo.
%PY% admin\server.py

:end
echo.
pause
