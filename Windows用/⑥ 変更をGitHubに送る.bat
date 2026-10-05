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

rem ------------------------------------------------------------------
rem   1) GitHubの最新を確認する
rem ------------------------------------------------------------------
%GIT% fetch --quiet origin > nul 2>&1

rem ------------------------------------------------------------------
rem   2) このパソコンの変更を先に記録する（受け取りで失わないため）
rem ------------------------------------------------------------------
%GIT% status --porcelain > "%TEMP%\kuricare_status.txt" 2>&1
set NEWCHANGE=1
for %%A in ("%TEMP%\kuricare_status.txt") do if %%~zA equ 0 set NEWCHANGE=

if "%NEWCHANGE%"=="" goto :receive
echo 今回の変更
%GIT% status --short
echo.
%GIT% add -A
for /f "tokens=1-3 delims=/ " %%a in ("%date%") do set D=%%a-%%b-%%c
%GIT% commit -m "サイト更新 %D% %time:~0,5%" > nul

rem ------------------------------------------------------------------
rem   3) ほかのパソコンの変更を受け取る
rem ------------------------------------------------------------------
:receive
set INCOMING=0
for /f %%N in ('%GIT% rev-list --count HEAD..@{u} 2^>nul') do set INCOMING=%%N
if "%INCOMING%"=="0" goto :checkstep

echo ほかのパソコンの変更 %INCOMING% 件を受け取ります...
%GIT% merge --no-edit @{u} > "%TEMP%\kuricare_merge.txt" 2>&1
if errorlevel 1 goto :mergefail
echo 受け取りました。
echo.

rem ------------------------------------------------------------------
rem   4) 受け取った内容もあわせて点検する
rem ------------------------------------------------------------------
:checkstep
%PY% build.py > nul
%PY% tools\check.py > "%TEMP%\kuricare_check.txt" 2>&1
if errorlevel 1 (
  echo 点検で問題が見つかりました。直してからもう一度実行してください。
  echo （このパソコンの変更は記録済みです。失われていません）
  echo.
  type "%TEMP%\kuricare_check.txt"
  goto :end
)

rem ------------------------------------------------------------------
rem   5) GitHubへ送る
rem ------------------------------------------------------------------
set UNPUSHED=0
for /f %%N in ('%GIT% rev-list --count @{u}..HEAD 2^>nul') do set UNPUSHED=%%N
if "%UNPUSHED%"=="0" (
  echo 送るものはありません。すでに最新の状態です。
  goto :end
)

echo GitHubへ送信中...
%GIT% push
if errorlevel 1 (
  echo.
  echo 送信できませんでした。
  echo GitHub Desktop を開いて「Push origin」を押してみてください。
  echo （記録はすでに済んでいるので、内容が失われることはありません）
) else (
  echo.
  echo 送信しました。1〜2分でホームページに反映されます。
  echo 進み具合は GitHub の「Actions」タブで確認できます。
)
goto :end

:mergefail
%GIT% merge --abort > nul 2>&1
echo.
echo 受け取りを中断しました。送信はしていません。
echo.
echo 同じ場所を2台のパソコンで変更したため、自動でまとめられませんでした。
echo このパソコンの変更は記録済みで、失われていません。
echo このままの状態で、サポートにご相談ください。
echo.
type "%TEMP%\kuricare_merge.txt"

:end
echo.
pause
