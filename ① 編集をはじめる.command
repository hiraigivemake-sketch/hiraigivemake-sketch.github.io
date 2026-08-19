#!/bin/zsh
cd "$(dirname "$0")"
clear
echo "======================================"
echo "  クリケア ホームページ 編集画面"
echo "======================================"
echo ""
# すでに動いている編集画面があれば止めてから起動する
pkill -f "admin/server.py" 2>/dev/null
sleep 1
echo "ブラウザが自動で開きます。"
echo "編集が終わったら、この黒い画面を閉じてください。"
echo ""
python3 admin/server.py
