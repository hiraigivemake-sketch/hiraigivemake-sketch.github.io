@echo off
chcp 65001 > nul
cd /d "%~dp0.."
title クリケア ホームページ 編集画面
echo ======================================
echo   クリケア ホームページ 編集画面
echo ======================================
echo.

where py >nul 2>nul
if %errorlevel%==0 (set PY=py -3) else (set PY=python)

%PY% --version >nul 2>nul
if errorlevel 1 (
  echo Python が見つかりませんでした。
  echo Microsoft Store で「Python 3」を検索してインストールしてください。
  echo.
  pause
  exit /b
)

echo ブラウザが自動で開きます。
echo 編集が終わったら、この黒い画面を閉じてください。
echo.
%PY% admin\server.py
pause
