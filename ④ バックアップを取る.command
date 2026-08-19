#!/bin/zsh
cd "$(dirname "$0")"
clear
python3 tools/backup.py
echo ""
echo "backups フォルダに保存しました。"
read "?Enterキーを押すと閉じます..."
