#!/bin/zsh
cd "$(dirname "$0")"
clear
echo "======================================"
echo "  クリケア ホームページ プレビュー"
echo "======================================"
echo ""

# すでに編集画面が動いていれば、そのプレビューをそのまま開く
if curl -s -o /dev/null -m 2 http://localhost:8000/ ; then
  echo "すでに開いているプレビューを表示します。"
  echo "→ http://localhost:8000"
  open http://localhost:8000
  echo ""
  echo "この画面は閉じて構いません。"
  sleep 3
  exit 0
fi

python3 build.py
echo ""
echo "ブラウザで確認できます → http://localhost:8000"
echo "見終わったら、この黒い画面を閉じてください。"
echo ""
(sleep 2 && open http://localhost:8000) &
python3 -m http.server 8000 --directory dist
