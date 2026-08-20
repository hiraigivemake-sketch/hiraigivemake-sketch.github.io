#!/bin/zsh
cd "$(dirname "$0")"
clear
echo "======================================"
echo "  変更をGitHubに送って公開します"
echo "======================================"
echo ""

if [ ! -d .git ] || ! git remote get-url origin > /dev/null 2>&1; then
  echo "⚠ まだGitHubと連携していません。"
  echo "  GitHub Desktop で「Publish repository」を先に行ってください。"
  echo ""
  read "?Enterキーを押すと閉じます..."
  exit 1
fi

HAS_CHANGE=""
[ -n "$(git status --porcelain)" ] && HAS_CHANGE=1

# まだ送っていないコミットがあるか（前回、記録だけして送信できなかった場合など）
git fetch --quiet origin 2>/dev/null
UNPUSHED=$(git rev-list --count @{u}..HEAD 2>/dev/null || echo 0)

if [ -z "$HAS_CHANGE" ] && [ "$UNPUSHED" = "0" ]; then
  echo "変更はありません。すでに最新の状態です。"
  echo ""
  read "?Enterキーを押すと閉じます..."
  exit 0
fi

# 新しい変更があるときは、点検してから記録する
if [ -n "$HAS_CHANGE" ]; then
  echo "▼ 今回の変更"
  git status --short
  echo ""
  echo "点検しています…"
  python3 build.py > /dev/null
  if ! python3 tools/check.py > /tmp/kuricare_check.txt 2>&1; then
    echo ""
    echo "⚠ 点検で問題が見つかりました。直してからもう一度実行してください。"
    echo ""
    cat /tmp/kuricare_check.txt
    echo ""
    read "?Enterキーを押すと閉じます..."
    exit 1
  fi
  echo "✅ 点検OK"
  echo ""
  git add -A
  git commit -m "サイト更新 $(date '+%Y-%m-%d %H:%M')" > /dev/null
  UNPUSHED=$(git rev-list --count @{u}..HEAD 2>/dev/null || echo 1)
fi

echo "GitHubへ送信中…（未送信 ${UNPUSHED} 件）"
if git push; then
  echo ""
  echo "✅ 送信しました。1〜2分でホームページに反映されます。"
  echo "   進み具合は GitHub の「Actions」タブで確認できます。"
else
  echo ""
  echo "⚠ 送信できませんでした。"
  echo "  GitHub Desktop を開いて「Push origin」を押してみてください。"
  echo "  （記録はすでに済んでいるので、内容が失われることはありません）"
fi
echo ""
read "?Enterキーを押すと閉じます..."
