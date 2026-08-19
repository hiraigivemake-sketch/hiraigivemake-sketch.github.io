#!/usr/bin/env python3
"""
サイトの定期点検スクリプト

  python3 tools/check.py            … リンク切れ・画像欠け・JSON エラーを点検
  python3 tools/check.py --external … 外部リンクの生存確認も行う（時間がかかります）

問題が 1 件でもあれば終了コード 1 を返すので、自動実行にも使えます。
"""
from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
CONTENT = ROOT / "content"
ASSETS = ROOT / "assets"

problems: list[str] = []
notes: list[str] = []


def add(msg: str) -> None:
    problems.append(msg)


# ------------------------------------------------------------------ 1. JSON
def check_json() -> None:
    for path in sorted(CONTENT.rglob("*.json")):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            add(f"[JSON] {path.relative_to(ROOT)} の書式が壊れています（{e.lineno}行目付近）: {e.msg}")


# ------------------------------------------------------------------ 2. 記事
def check_posts() -> None:
    for kind in ("blog", "recruit"):
        for path in sorted((CONTENT / kind).glob("*.md")):
            text = path.read_text(encoding="utf-8")
            if not text.startswith("---"):
                add(f"[記事] {path.relative_to(ROOT)} に先頭のメタ情報（---）がありません")
                continue
            head = text[3 : text.find("\n---", 3)]
            meta = dict(
                (k.strip(), v.strip().strip('"'))
                for k, _, v in (l.partition(":") for l in head.strip().split("\n"))
                if k.strip()
            )
            if not meta.get("title"):
                add(f"[記事] {path.relative_to(ROOT)} にタイトルがありません")
            date = meta.get("date", "")
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
                add(f"[記事] {path.relative_to(ROOT)} の日付が YYYY-MM-DD 形式ではありません: 「{date}」")
            if not meta.get("thumbnail"):
                notes.append(f"[記事] {path.relative_to(ROOT)} にサムネイル画像が設定されていません")


# ------------------------------------------------------------------ 3. 出力物
def check_dist() -> None:
    if not DIST.exists():
        add("[ビルド] dist フォルダがありません。先に python3 build.py を実行してください")
        return

    pages = list(DIST.rglob("*.html"))
    internal: set[str] = set()
    assets: set[str] = set()

    for path in pages:
        html = path.read_text(encoding="utf-8")
        where = path.relative_to(DIST)

        if "{{" in html:
            add(f"[テンプレート] {where} に未展開の記法 {{{{ …}}}} が残っています")

        for href in re.findall(r'href="(/[^"#?]*)"', html) + re.findall(r'src="(/[^"#?]*)"', html):
            (assets if re.search(r"\.\w{2,5}$", href) else internal).add(href)

    for href in sorted(internal):
        target = DIST / href.strip("/") / "index.html"
        if not target.exists() and not (DIST / href.strip("/")).exists():
            add(f"[リンク切れ] サイト内リンク {href} の先にページがありません")

    for src in sorted(assets):
        if not (DIST / src.lstrip("/")).exists():
            add(f"[画像・ファイル欠け] {src} が見つかりません")

    notes.append(f"[集計] HTML {len(pages)}ページ／内部リンク {len(internal)}種／ファイル参照 {len(assets)}種")


# ------------------------------------------------------------------ 4. 未使用画像
def check_unused_images() -> None:
    if not DIST.exists():
        return
    used = set()
    for path in DIST.rglob("*.html"):
        used |= set(re.findall(r"/assets/images/([^\"'\s)]+)", path.read_text(encoding="utf-8")))
    for path in (ASSETS / "images").iterdir():
        if path.is_file() and path.name not in used:
            notes.append(f"[未使用] assets/images/{path.name} はどのページからも参照されていません")


# ------------------------------------------------------------------ 5. 外部リンク
def check_external() -> None:
    urls = set()
    for path in DIST.rglob("*.html"):
        urls |= set(re.findall(r'href="(https?://[^"]+)"', path.read_text(encoding="utf-8")))
    print(f"外部リンク {len(urls)} 件を確認します…")
    for url in sorted(urls):
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req, timeout=12) as res:
                if res.status >= 400:
                    add(f"[外部リンク] {url} が {res.status} を返しました")
        except urllib.error.HTTPError as e:
            if e.code not in (403, 405, 429):  # 自動アクセスを弾くサイトは除外
                add(f"[外部リンク] {url} が {e.code} を返しました")
        except Exception as e:
            add(f"[外部リンク] {url} に接続できません（{type(e).__name__}）")


def main() -> None:
    print("=" * 60)
    print("クリケアサイト 点検レポート")
    print("=" * 60)

    check_json()
    check_posts()
    check_dist()
    check_unused_images()
    if "--external" in sys.argv:
        check_external()

    if problems:
        print(f"\n❌ 要対応 {len(problems)}件")
        for msg in problems:
            print("  ・" + msg)
    else:
        print("\n✅ 問題は見つかりませんでした。")

    if notes:
        print(f"\nℹ️ 参考情報 {len(notes)}件")
        for msg in notes[:40]:
            print("  ・" + msg)
        if len(notes) > 40:
            print(f"  …ほか {len(notes) - 40}件")

    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
