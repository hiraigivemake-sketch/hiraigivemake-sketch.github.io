#!/usr/bin/env python3
"""
インスタグラムの最新投稿を取り込む

  python3 tools/fetch_instagram.py

環境変数 IG_TOKEN（インスタグラムのアクセストークン）を使って最新の投稿を取得し、
・写真を assets/images/instagram/ に保存
・一覧を content/instagram.json に書き出し
します。手で登録したときと同じ形なので、表示のしかたは今までどおり
「サイト全体の設定」→「ホーム下部の表示」で切り替えられます。

IG_TOKEN が無いときは、何もせず正常終了します（設定前でも動かせるようにするため）。
外部ライブラリは不要です。
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
IG_DIR = ROOT / "assets" / "images" / "instagram"
IG_JSON = CONTENT / "instagram.json"
SITE = CONTENT / "site.json"

API = "https://graph.instagram.com/me/media"
FIELDS = "id,caption,media_type,media_url,thumbnail_url,permalink,timestamp"
TIMEOUT = 60

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "kuricare-site"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
        return json.loads(res.read().decode("utf-8"))


def how_many() -> int:
    """ホームに並べる件数（サイト全体の設定より）。"""
    try:
        bottom = json.loads(SITE.read_text(encoding="utf-8")).get("home_bottom") or {}
        return max(1, min(12, int(bottom.get("instagram_count", 4))))
    except Exception:
        return 4


def tidy_caption(text: str) -> str:
    """写真の下に出す短い説明文を作る。ハッシュタグと余分な行は落とす。"""
    if not text:
        return ""
    first = ""
    for line in str(text).replace("\r\n", "\n").split("\n"):
        line = re.sub(r"#\S+", "", line).strip()
        if line:
            first = line
            break
    return first if len(first) <= 60 else first[:59].rstrip() + "…"


def picture_of(post: dict) -> str:
    """投稿から写真のURLを取り出す。動画・リールはサムネイルを使う。"""
    if post.get("media_type") == "VIDEO":
        return post.get("thumbnail_url") or post.get("media_url") or ""
    return post.get("media_url") or post.get("thumbnail_url") or ""


def extension_of(url: str) -> str:
    ext = Path(urllib.parse.urlparse(url).path).suffix.lower()
    return ext if ext in {".jpg", ".jpeg", ".png", ".webp"} else ".jpg"


def download(url: str, dest: Path) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "kuricare-site"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
            data = res.read()
        if len(data) < 1000:          # 壊れた画像を掴まないための最低限の確認
            return False
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return True
    except Exception as e:
        print(f"   写真を取得できませんでした（{type(e).__name__}）: {url[:60]}")
        return False


def main() -> None:
    token = (os.environ.get("IG_TOKEN") or "").strip()
    if not token:
        print("IG_TOKEN が設定されていないため、取り込みを行いませんでした。")
        return

    limit = how_many()
    url = f"{API}?{urllib.parse.urlencode({'fields': FIELDS, 'limit': limit * 2, 'access_token': token})}"

    try:
        data = get_json(url)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:300]
        print(f"インスタグラムから取得できませんでした（HTTP {e.code}）: {body}")
        sys.exit(1)
    except Exception as e:
        print(f"インスタグラムから取得できませんでした（{type(e).__name__}）")
        sys.exit(1)

    posts_in = data.get("data") or []
    print(f"インスタグラムから {len(posts_in)} 件を受け取りました。上位 {limit} 件を使います。")

    posts_out: list[dict] = []
    keep: set[str] = set()

    for post in posts_in:
        if len(posts_out) >= limit:
            break
        src = picture_of(post)
        if not src:
            continue

        name = re.sub(r"\W", "", str(post.get("id", "")))[:32] + extension_of(src)
        dest = IG_DIR / name

        # すでに同じ投稿の写真があれば取得し直さない
        if not dest.exists() and not download(src, dest):
            continue

        keep.add(name)
        posts_out.append({
            "image": "/assets/images/instagram/" + name,
            "caption": tidy_caption(post.get("caption", "")),
            "post_url": post.get("permalink", ""),
            "date": str(post.get("timestamp", ""))[:10],
        })

    if not posts_out:
        print("表示できる投稿がありませんでした。ファイルは変更しません。")
        return

    # 使わなくなった写真を片づける
    if IG_DIR.exists():
        for old in IG_DIR.iterdir():
            if old.is_file() and not old.name.startswith(".") and old.name not in keep:
                old.unlink()
                print(f"   古い写真を削除: {old.name}")

    original = json.loads(IG_JSON.read_text(encoding="utf-8")) if IG_JSON.exists() else {}
    original["posts"] = posts_out
    IG_JSON.write_text(json.dumps(original, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"取り込み完了: {len(posts_out)} 件を content/instagram.json に書き出しました。")
    for p in posts_out:
        print(f"   {p['date']}  {p['caption'][:30]}")


if __name__ == "__main__":
    main()
