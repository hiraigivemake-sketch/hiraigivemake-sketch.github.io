@echo off
rem Python の場所を探して %PY% に入れる共通処理（直接ダブルクリックしないでください）
set PY=

where py > nul 2>&1
if not errorlevel 1 (
  py -3 --version > nul 2>&1
  if not errorlevel 1 set PY=py -3
)

if "%PY%"=="" (
  where python > nul 2>&1
  if not errorlevel 1 (
    python --version > nul 2>&1
    if not errorlevel 1 set PY=python
  )
)

if "%PY%"=="" (
  echo ======================================
  echo   Python が見つかりませんでした
  echo ======================================
  echo.
  echo このホームページを動かすには Python が必要です。
  echo 一度だけインストールしてください（無料・5分ほど）。
  echo.
  echo   1. スタートメニューから「Microsoft Store」を開く
  echo   2. 検索欄に「Python 3」と入力
  echo   3. 「Python 3.12」など新しいものを選んで「入手」を押す
  echo   4. 終わったら、このファイルをもう一度ダブルクリック
  echo.
  exit /b 1
)

exit /b 0
