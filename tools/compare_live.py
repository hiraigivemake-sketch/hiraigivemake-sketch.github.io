#!/usr/bin/env python3
"""
公開中の STUDIO サイトと、この手元のサイトの文章を見比べる

  python3 tools/compare_live.py            … 主要ページを比較
  python3 tools/compare_live.py /service/  … ページを指定して比較

STUDIO 側だけを更新してしまったときに、取り込み漏れを見つけるためのツールです。
文章（テキスト）だけを比較します。レイアウトの違いは検出しません。
"""
from html.parser import HTMLParser
from pathlib import Path
import difflib
import re
import sys
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
LIVE = "https://giveandmake-c.com"
PAGES = ["/", "/service/", "/aboutus/", "/staff/", "/recruit/", "/privacypolicy/"]


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "svg"):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "svg"):
            self.skip = max(0, self.skip - 1)

    def handle_data(self, data):
        if not self.skip and data.strip():
            self.parts.append(data.strip())


def to_lines(html: str) -> list[str]:
    p = Text()
    p.feed(html)
    seen, out = set(), []
    for line in p.parts:
        line = re.sub(r"\s+", " ", line)
        if len(line) < 4 or line in seen:
            continue
        seen.add(line)
        out.append(line)
    return out


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def main() -> None:
    targets = sys.argv[1:] or PAGES
    total = 0
    for path in targets:
        local_file = DIST / (path.strip("/") + "/index.html" if path != "/" else "index.html")
        if not local_file.exists():
            print(f"⚠ {path}: 手元にビルド結果がありません")
            continue
        try:
            live_html = fetch(LIVE + path)
        except Exception as e:
            print(f"⚠ {path}: 公開サイトを取得できません（{type(e).__name__}）")
            continue

        live = to_lines(live_html)
        mine = to_lines(local_file.read_text(encoding="utf-8"))
        only_live = [l for l in live if l not in mine]

        print(f"\n── {path} ──")
        if not only_live:
            print("  ✅ 公開サイトにあって手元にない文章はありません")
        else:
            total += len(only_live)
            print(f"  ⚠ 公開サイトにだけある文章 {len(only_live)}件（取り込み漏れの可能性）")
            for line in only_live[:15]:
                print("    ＋ " + line[:100])
            if len(only_live) > 15:
                print(f"    …ほか {len(only_live) - 15}件")

    print(f"\n合計 {total} 件の差分候補が見つかりました。")
    print("※ STUDIO は文字を細かく分割して出力するため、実際には同じ文章でも差分に出ることがあります。")


if __name__ == "__main__":
    main()
