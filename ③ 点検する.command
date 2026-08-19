#!/bin/zsh
cd "$(dirname "$0")"
clear
python3 build.py
echo ""
python3 tools/check.py
echo ""
echo "--------------------------------------"
echo "確認が終わったら、この画面を閉じてください。"
read "?Enterキーを押すと閉じます..."
