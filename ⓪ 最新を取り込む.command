#!/bin/zsh
cd "$(dirname "$0")"
clear
echo "======================================"
echo "  GitHubから最新を取り込みます"
echo "  （ほかのパソコンでの変更を受け取る）"
echo "======================================"
echo ""
python3 tools/pull_from_github.py
echo ""
read "?Enterキーを押すと閉じます..."
