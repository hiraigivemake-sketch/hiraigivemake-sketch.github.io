#!/bin/zsh
cd "$(dirname "$0")"
clear
echo "======================================"
echo "  変更をGitHubに送って公開します"
echo "======================================"
echo ""

if [ ! -d .git ]; then
  echo "⚠ まだGitHubと連携していません。"
  echo "  先に GitHub Desktop で「Publish repository」を行ってください。"
  echo ""
  read "?Enterキーを押すと閉じます..."
  exit 1
fi

if ! git remote get-url origin > /dev/null 2>&1; then
  echo "⚠ まだGitHubに登録されていません。"
  echo "  GitHub Desktop を開いて「Publish repository」を押してください。"
  echo ""
  read "?Enterキーを押すと閉じます..."
  exit 1
fi

# 念のため、送る前に点検する
python3 build.py > /dev/null
if ! python3 tools/check.py > /tmp/kuricare_check.txt 2>&1; then
  echo "⚠ 点検で問題が見つかりました。直してからもう一度実行してください。"
  echo ""
  cat /tmp/kuricare_check.txt
  echo ""
  read "?Enterキーを押すと閉じます..."
  exit 1
fi

if [ -z "$(git status --porcelain)" ]; then
  echo "変更はありません。すでに最新の状態です。"
  echo ""
  read "?Enterキーを押すと閉じます..."
  exit 0
fi

echo "▼ 今回の変更"
git status --short
echo ""

git add -A
git commit -m "サイト更新 $(date '+%Y-%m-%d %H:%M')" > /dev/null
echo "GitHubへ送信中…"
if git push; then
  echo ""
  echo "✅ 送信しました。1〜2分でホームページに反映されます。"
  echo "   進み具合は GitHub の「Actions」タブで確認できます。"
else
  echo ""
  echo "⚠ 送信できませんでした。GitHub Desktop を開いて「Push origin」を押してみてください。"
fi
echo ""
read "?Enterキーを押すと閉じます..."
