#!/usr/bin/env python3
"""
公開時刻が来たばかりの記事があるか調べる

  python3 tools/due_check.py

予約投稿を公開するために、サイトを作り直す必要があるかどうかを判定します。
「直近 WINDOW 分のあいだに公開時刻を迎えた記事」があれば yes を返します。

自動実行を 15 分ごとに回しても、ほとんどの回はここで終わるため、
無駄な公開処理が走りません。
"""
from __future__ import annotations

import os
import sys
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import build as b  # noqa: E402

WINDOW = 40          # 何分前までを「公開時刻が来たばかり」とみなすか

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> None:
    from datetime import datetime

    now = datetime.now(b.JST)
    since = (now - timedelta(minutes=WINDOW)).strftime("%Y-%m-%d %H:%M")
    until = now.strftime("%Y-%m-%d %H:%M")

    due = []
    for kind in ("blog", "recruit"):
        for path in sorted((ROOT / "content" / kind).glob("*.md")):
            meta, _ = b.parse_front_matter(path.read_text(encoding="utf-8"))
            at = b.publish_at(meta.get("date", ""), meta.get("time", ""))
            if since < at <= until:
                due.append((at, meta.get("title", path.stem)))

    if due:
        print(f"公開時刻を迎えた記事が {len(due)} 件あります。サイトを作り直します。")
        for at, title in due:
            print(f"   {at}  {title}")
    else:
        print(f"{since} 〜 {until} に公開時刻を迎えた記事はありません。")

    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"publish={'true' if due else 'false'}\n")


if __name__ == "__main__":
    main()
