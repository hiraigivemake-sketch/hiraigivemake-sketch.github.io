#!/usr/bin/env python3
"""
他のパソコンへ渡すためのZIPを作る

  python3 tools/export.py

デスクトップに「kuricare-site_共有用_日付.zip」を作ります。
そのままコピーしても動きますが、生成物（dist）やバックアップを除くので軽くなります。
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent.parent
JST = timezone(timedelta(hours=9))

# 渡す必要のないフォルダ・ファイル（受け取った側で自動的に作られます）
SKIP_DIRS = {"dist", "backups", "_trash", "__pycache__", ".git", ".DS_Store"}
SKIP_NAMES = {".DS_Store"}


def include(path: Path) -> bool:
    parts = set(path.relative_to(ROOT).parts)
    if parts & SKIP_DIRS:
        return False
    return path.name not in SKIP_NAMES


def main() -> None:
    stamp = datetime.now(JST).strftime("%Y-%m-%d")
    target = Path.home() / "Desktop" / f"kuricare-site_共有用_{stamp}.zip"

    files = [p for p in sorted(ROOT.rglob("*")) if p.is_file() and include(p)]
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        for p in files:
            z.write(p, Path("kuricare-site") / p.relative_to(ROOT))

    size = target.stat().st_size / 1024 / 1024
    print(f"✅ できました: デスクトップ / {target.name}")
    print(f"   {len(files)}ファイル / {size:.0f}MB")
    print()
    print("【渡しかた】")
    print("  このZIPを、AirDrop・USBメモリ・ギガファイル便などで相手に渡してください。")
    print("  受け取った人は、ZIPを展開してデスクトップに置き、")
    print("  Mac  → 「① 編集をはじめる.command」")
    print("  Win  → 「Windows用」フォルダの「① 編集をはじめる.bat」")
    print("  をダブルクリックすれば、そのまま使えます。")


if __name__ == "__main__":
    main()
