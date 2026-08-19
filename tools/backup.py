#!/usr/bin/env python3
"""
コンテンツのバックアップを取る

  python3 tools/backup.py

content/ と assets/ をまとめて backups/YYYY-MM-DD_HHMM.zip に保存します。
古いものは 20 世代を残して自動で削除します。
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent.parent
BACKUPS = ROOT / "backups"
KEEP = 20
JST = timezone(timedelta(hours=9))

def main() -> None:
    BACKUPS.mkdir(exist_ok=True)
    stamp = datetime.now(JST).strftime("%Y-%m-%d_%H%M")
    target = BACKUPS / f"{stamp}.zip"

    count = 0
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        for folder in ("content", "assets", "templates"):
            for path in sorted((ROOT / folder).rglob("*")):
                if path.is_file() and "_trash" not in path.parts:
                    z.write(path, path.relative_to(ROOT))
                    count += 1
        for name in ("build.py", "README.md"):
            if (ROOT / name).exists():
                z.write(ROOT / name, name)
                count += 1

    size = target.stat().st_size / 1024 / 1024
    print(f"✅ バックアップを作成しました: backups/{target.name}（{count}ファイル / {size:.1f}MB）")

    olds = sorted(BACKUPS.glob("*.zip"), reverse=True)[KEEP:]
    for old in olds:
        old.unlink()
        print(f"🗑  古いバックアップを削除: {old.name}")

if __name__ == "__main__":
    main()
