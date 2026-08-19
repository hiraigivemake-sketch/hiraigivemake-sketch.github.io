@echo off
chcp 65001 > nul
cd /d "%~dp0.."
title クリケア ホームページ プレビュー
where py >nul 2>nul
if %errorlevel%==0 (set PY=py -3) else (set PY=python)
%PY% build.py
echo.
echo ブラウザで確認できます → http://localhost:8000
echo 見終わったら、この黒い画面を閉じてください。
echo.
start "" http://localhost:8000
%PY% -m http.server 8000 --directory dist
pause
