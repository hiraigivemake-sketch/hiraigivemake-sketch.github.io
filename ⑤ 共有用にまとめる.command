#!/bin/zsh
cd "$(dirname "$0")"
clear
echo "======================================"
echo "  他のパソコンへ渡すファイルを作ります"
echo "======================================"
echo ""
python3 tools/export.py
echo ""
read "?Enterキーを押すと閉じます..."
