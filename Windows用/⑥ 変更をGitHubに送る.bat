@echo off
chcp 65001 > nul
cd /d "%~dp0.."
title クリケア ホームページ GitHubへ送信
cls
echo ======================================
echo   変更をGitHubに送って公開します
echo ======================================
echo.

call "%~dp0_python.bat"
if errorlevel 1 goto :end

rem git を探す（GitHub Desktop に同梱されているものも探します）
set GIT=git
where git > nul 2>&1
if errorlevel 1 (
  set GIT=
  for /d %%D in ("%LOCALAPPDATA%\GitHubDesktop\app-*") do (
    if exist "%%D\resources\app\git\cmd\git.exe" set GIT="%%D\resources\app\git\cmd\git.exe"
  )
)

if "%GIT%"=="" (
  echo git が見つかりませんでした。
  echo.
  echo かわりに GitHub Desktop を使ってください。
  echo   1. GitHub Desktop を開く
  echo   2. 左下に一言（例：サイト更新）を入れて「Commit to main」
  echo   3. 上の「Push origin」を押す
  echo.
  goto :end
)

if not exist ".git" (
  echo まだGitHubと連携していません。
  echo GitHub Desktop で「Publish repository」を先に行ってください。
  goto :end
)

%GIT% remote get-url origin > nul 2>&1
if errorlevel 1 (
  echo まだGitHubに登録されていません。
  echo GitHub Desktop を開いて「Publish repository」を押してください。
  goto :end
)

rem 送る前に点検する
%PY% build.py > nul
%PY% tools\check.py > "%TEMP%\kuricare_check.txt" 2>&1
if errorlevel 1 (
  echo 点検で問題が見つかりました。直してからもう一度実行してください。
  echo.
  type "%TEMP%\kuricare_check.txt"
  goto :end
)

rem 変更があるか調べる（結果をファイルに出して、中身が空かどうかで判断）
%GIT% status --porcelain > "%TEMP%\kuricare_status.txt" 2>&1
for %%A in ("%TEMP%\kuricare_status.txt") do if %%~zA equ 0 (
  echo 変更はありません。すでに最新の状態です。
  goto :end
)
echo 今回の変更
%GIT% status --short
echo.
%GIT% add -A
for /f "tokens=1-3 delims=/ " %%a in ("%date%") do set D=%%a-%%b-%%c
%GIT% commit -m "サイト更新 %D% %time:~0,5%" > nul
echo GitHubへ送信中...
%GIT% push
if errorlevel 1 (
  echo.
  echo 送信できませんでした。
  echo GitHub Desktop を開いて「Push origin」を押してみてください。
) else (
  echo.
  echo 送信しました。1〜2分でホームページに反映されます。
  echo 進み具合は GitHub の「Actions」タブで確認できます。
)

:end
echo.
pause
