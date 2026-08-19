@echo off
chcp 65001 > nul
cd /d "%~dp0.."
title クリケア ホームページ プレビュー
cls
echo ======================================
echo   クリケア ホームページ プレビュー
echo ======================================
echo.

call "%~dp0_python.bat"
if errorlevel 1 goto :end

rem すでに編集画面が動いていれば、そのプレビューをそのまま開く
curl -s -o nul -m 2 http://localhost:8000/ > nul 2>&1
if not errorlevel 1 (
  echo すでに開いているプレビューを表示します。
  echo   http://localhost:8000
  start "" http://localhost:8000
  timeout /t 3 /nobreak > nul
  exit /b
)

%PY% build.py
echo.
echo ブラウザで確認できます  http://localhost:8000
echo 見終わったら、この黒い画面を閉じてください。
echo.
start "" http://localhost:8000
%PY% -m http.server 8000 --directory dist

:end
echo.
pause
