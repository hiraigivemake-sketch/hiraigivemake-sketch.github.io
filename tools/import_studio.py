#!/usr/bin/env python3
"""STUDIO に残っている新しいブログ記事を、こちらのサイトへ取り込みます。

STUDIO をまだ解約していないあいだ、あちらで書かれた記事をこちらへ持ってくるための道具です。
記事の文章・写真・動画をすべてこちらのフォルダへ保存するので、
取り込みが終われば STUDIO がなくなっても表示され続けます。

    python3 tools/import_studio.py            # 新しい記事があれば取り込む
    python3 tools/import_studio.py --dry-run  # 何が取り込まれるか見るだけ

※ ドメインの切り替え後は STUDIO のサーバーに直接つなぐ必要があるため、
   --ip でそのアドレスを指定します（既定値は切り替え前に記録したものです）。
"""

from __future__ import annotations

import argparse
import html as html_mod
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BLOG = ROOT / "content" / "blog"
IMAGES = ROOT / "assets" / "images"
VIDEOS = ROOT / "assets" / "video"

DOMAIN = "giveandmake-c.com"
STUDIO_IP = "34.111.141.225"


# --------------------------------------------------------------- 取得まわり
def fetch(url: str, ip: str | None = None) -> bytes:
    """URL を取ってくる。ip を指定すると、その住所のサーバーに直接つなぐ。"""
    cmd = ["curl", "-sS", "--max-time", "60"]
    if ip:
        cmd += ["--resolve", f"{DOMAIN}:443:{ip}"]
    cmd.append(url)
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"取得に失敗しました: {url}\n{r.stderr.decode()[:200]}")
    return r.stdout


def studio_slugs(ip: str) -> list[str]:
    """STUDIO のサイトマップから、ブログ記事の一覧を新しい順で取り出す。"""
    index = fetch(f"https://{DOMAIN}/sitemap.xml", ip).decode("utf-8", "replace")
    rows: list[tuple[str, str]] = []
    for loc in re.findall(r"<loc>(.*?)</loc>", index):
        if "sitemap-dynamic" not in loc:
            continue
        body = fetch(loc, ip).decode("utf-8", "replace")
        for item in re.findall(r"<url>(.*?)</url>", body, re.S):
            u = re.search(r"<loc>(.*?)</loc>", item)
            m = re.search(r"<lastmod>(.*?)</lastmod>", item)
            if u and "/blog/" in u.group(1):
                rows.append((m.group(1) if m else "", u.group(1).rstrip("/").split("/")[-1]))
    rows.sort(reverse=True)
    return [slug for _, slug in rows]


def payload(page_html: str) -> list:
    """STUDIO のページに埋め込まれたデータのかたまりを取り出す。"""
    m = re.search(r'id="__NUXT_DATA__"[^>]*>(.*?)</script>', page_html, re.S)
    if not m:
        raise RuntimeError("ページの中にデータが見つかりませんでした")
    return json.loads(m.group(1))


def resolve(data: list, i, depth: int = 0):
    """データのかたまりは番号で参照し合っているので、実際の値に戻す。"""
    if depth > 6:
        return None
    v = data[i] if isinstance(i, int) and 0 <= i < len(data) else i
    if isinstance(v, dict):
        return {k: resolve(data, x, depth + 1) for k, x in v.items()}
    if isinstance(v, list):
        return [resolve(data, x, depth + 1) for x in v]
    return v


def find_post(data: list) -> dict | None:
    """記事そのものを表すかたまりを探す。"""
    for i, v in enumerate(data):
        if isinstance(v, dict) and {"title", "slug", "body"} <= set(v.keys()):
            return resolve(data, i)
    return None


# ------------------------------------------------------------- 変換まわり
def save_asset(url: str, dest_dir: Path, suffix: str = "") -> str | None:
    """写真や動画をこちらのフォルダへ保存し、サイト内での置き場所を返す。"""
    base = url.split("/")[-1].split("?")[0]
    if suffix:
        stem = base.rsplit(".", 1)[0]
        name = f"{stem}{suffix}"
        url = url.rsplit(".", 1)[0] + suffix
    else:
        name = base

    dest = dest_dir / name
    folder = "images" if dest_dir == IMAGES else "video"
    if dest.exists():
        return f"/assets/{folder}/{name}"

    try:
        blob = fetch(url)
    except RuntimeError:
        return None
    if len(blob) < 500 or blob[:20].lstrip().startswith(b"<"):
        return None  # エラーページが返ってきている

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(blob)
    return f"/assets/{folder}/{name}"


def to_markdown(body: str) -> tuple[str, list[str]]:
    """STUDIO の本文（HTML）を、こちらの記事の書き方へ直す。"""
    lines: list[str] = []
    saved: list[str] = []

    blocks = re.finditer(
        r"<figure.*?</figure>|<div[^>]*data-type=\"video_block\".*?</div>|<p[^>]*>.*?</p>",
        body,
        re.S,
    )
    for b in blocks:
        chunk = b.group(0)

        if chunk.startswith("<figure"):
            src = re.search(r'<img[^>]*src="([^"]+)"', chunk)
            if src:
                path = save_asset(src.group(1), IMAGES, "_middle.webp") or save_asset(src.group(1), IMAGES)
                if path:
                    saved.append(path)
                    lines += ["", f"![]({path})", ""]
            cap = re.search(r"<figcaption[^>]*>(.*?)</figcaption>", chunk, re.S)
            if cap:
                text = html_mod.unescape(re.sub(r"<[^>]+>", "", cap.group(1))).strip()
                if text:
                    lines += [text, ""]
            continue

        if chunk.startswith("<div"):
            src = re.search(r'<video[^>]*src="([^"]+)"', chunk)
            if src:
                path = save_asset(src.group(1), VIDEOS)
                if path:
                    saved.append(path)
                    lines += ["", f'<video src="{path}" controls playsinline preload="metadata"></video>', ""]
            continue

        inner = re.sub(r"<br\s*/?>", "\n", chunk)
        text = html_mod.unescape(re.sub(r"<[^>]+>", "", inner)).strip()
        if text:
            lines.append(text)

    out: list[str] = []
    for ln in lines:  # 空行が続かないように整える
        if ln == "" and out and out[-1] == "":
            continue
        out.append(ln)
    return "\n".join(out).strip() + "\n", saved


def describe(markdown_body: str) -> str:
    """一覧に出す短い紹介文（本文の書き出し110文字）を作る。"""
    plain = [
        ln.strip()
        for ln in markdown_body.split("\n")
        if ln.strip() and not ln.strip().startswith(("![", "<"))
    ]
    return " ".join(plain)[:110]


def post_date(meta: dict) -> str:
    for key in ("publishedAt", "createdAt", "updatedAt"):
        v = meta.get(key)
        if isinstance(v, list) and len(v) == 2 and isinstance(v[1], str):
            return v[1][:10]
        if isinstance(v, str) and len(v) >= 10:
            return v[:10]
    return ""


# ------------------------------------------------------------------- 本体
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ip", default=STUDIO_IP, help="STUDIO のサーバーの住所")
    ap.add_argument("--dry-run", action="store_true", help="取り込まず、内容の確認だけ行う")
    ap.add_argument("--slug", action="append", help="この記事だけ取り込む（何度でも指定可）")
    args = ap.parse_args()

    have = {p.stem.split("-", 3)[-1] for p in BLOG.glob("*.md")}

    if args.slug:
        targets = args.slug
    else:
        print("STUDIO の記事一覧を確認しています…")
        targets = [s for s in studio_slugs(args.ip) if s not in have]

    if not targets:
        print("✅ 新しい記事はありません。すべて取り込み済みです。")
        return 0

    print(f"\n取り込む記事: {len(targets)}件\n")
    added = 0
    for slug in targets:
        page = fetch(f"https://{DOMAIN}/blog/{slug}", args.ip).decode("utf-8", "replace")
        post = find_post(payload(page))
        if not post:
            print(f"  ✗ {slug}: 記事の中身が見つかりませんでした")
            continue

        meta = post.get("_meta") or {}
        date = post_date(meta)
        title = (post.get("title") or "").strip()
        body_md, saved = to_markdown(post.get("body") or "")

        cover = post.get("cover") or ""
        thumb = ""
        if isinstance(cover, str) and cover.startswith("http"):
            thumb = save_asset(cover, IMAGES, "_middle.webp") or save_asset(cover, IMAGES) or cover

        dest = BLOG / f"{date}-{slug}.md"
        text = (
            "---\n"
            f'title: "{title}"\n'
            f'slug: "{slug}"\n'
            f'date: "{date}"\n'
            f'thumbnail: "{thumb}"\n'
            f'description: "{describe(body_md)}"\n'
            "---\n"
            + body_md
        )

        print(f"  {date}  {title}")
        print(f"      画像・動画 {len(saved)}点 / {dest.name}")
        if args.dry_run:
            continue
        dest.write_text(text, encoding="utf-8")
        added += 1

    if args.dry_run:
        print("\n（確認のみ。ファイルは作成していません）")
    else:
        print(f"\n✅ {added}件を取り込みました。つづけて build.py を実行してください。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
