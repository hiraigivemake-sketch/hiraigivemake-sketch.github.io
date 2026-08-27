#!/usr/bin/env python3
"""
クリケア訪問看護ステーション サイトビルダー

  python3 build.py          … dist/ に静的サイトを生成
  python3 build.py --serve  … 生成してからローカルサーバーで確認

外部ライブラリは一切不要（Python 3.9+ の標準ライブラリのみ）。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
TEMPLATES = ROOT / "templates"
ASSETS = ROOT / "assets"
DIST = ROOT / "dist"

JST = timezone(timedelta(hours=9))

# Windows の黒い画面が Shift-JIS のとき、絵文字入りのメッセージで止まらないようにする
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------- テンプレート
class Template:
    """依存ゼロの Mustache 風テンプレートエンジン。

    {{ name }}        … HTML エスケープして差し込む
    {{{ name }}}      … エスケープせずそのまま差し込む（HTML 断片用）
    {{# name }}…{{/ name }}
                      … 配列ならループ、真値なら 1 回だけ描画、偽値なら描画しない
    {{^ name }}…{{/ name }}
                      … 偽値のときだけ描画
    {{> partial }}    … templates/partial.html を差し込む
    {{ a.b.c }}       … ドットでネストした値を参照。「.」は現在の値そのもの
    """

    _TOKEN = re.compile(
        r"\{\{\{\s*(?P<raw>[\w.]+)\s*\}\}\}"
        r"|\{\{\s*(?P<sigil>[#^/>])?\s*(?P<name>[\w./-]+)\s*\}\}"
    )

    def __init__(self, text: str, loader=None):
        self.loader = loader
        self.nodes = self._parse(text)

    # -- パース ------------------------------------------------------------
    def _parse(self, text: str):
        pos, stack = 0, [[]]
        names: list[str] = []
        for m in self._TOKEN.finditer(text):
            if m.start() > pos:
                stack[-1].append(("text", text[pos : m.start()]))
            pos = m.end()

            if m.group("raw"):
                stack[-1].append(("raw", m.group("raw")))
                continue

            sigil, name = m.group("sigil"), m.group("name")
            if sigil == "#" or sigil == "^":
                stack.append([])
                names.append(name if sigil == "#" else "^" + name)
            elif sigil == "/":
                body = stack.pop()
                opened = names.pop()
                inverted = opened.startswith("^")
                stack[-1].append(
                    ("section", opened.lstrip("^"), body, inverted)
                )
            elif sigil == ">":
                stack[-1].append(("partial", name))
            else:
                stack[-1].append(("var", name))
        if pos < len(text):
            stack[-1].append(("text", text[pos:]))
        if names:
            raise ValueError(f"閉じられていないセクション: {names}")
        return stack[0]

    # -- 描画 --------------------------------------------------------------
    def render(self, ctx: dict) -> str:
        return self._render(self.nodes, [ctx])

    def _lookup(self, name: str, scopes: list):
        if name == ".":
            scope = scopes[-1]
            # 文字列だけの配列をループしているときは "." に値そのものが入っている
            if isinstance(scope, dict) and "." in scope:
                return scope["."]
            return scope
        for scope in reversed(scopes):
            cur = scope
            ok = True
            for part in name.split("."):
                if isinstance(cur, dict) and part in cur:
                    cur = cur[part]
                else:
                    ok = False
                    break
            if ok:
                return cur
        return ""

    def _render(self, nodes, scopes) -> str:
        out = []
        for node in nodes:
            kind = node[0]
            if kind == "text":
                out.append(node[1])
            elif kind == "var":
                out.append(esc(self._lookup(node[1], scopes)))
            elif kind == "raw":
                val = self._lookup(node[1], scopes)
                out.append("" if val is None else str(val))
            elif kind == "partial":
                if not self.loader:
                    raise ValueError("partial にはローダーが必要です")
                out.append(self.loader(node[1]).render(scopes[-1]))
            elif kind == "section":
                _, name, body, inverted = node
                val = self._lookup(name, scopes)
                truthy = bool(val) and val != ""
                if inverted:
                    if not truthy:
                        out.append(self._render(body, scopes))
                elif isinstance(val, list):
                    for i, item in enumerate(val):
                        scope = dict(item) if isinstance(item, dict) else {".": item}
                        scope["_index"] = i
                        scope["_number"] = i + 1
                        scope["_first"] = i == 0
                        scope["_last"] = i == len(val) - 1
                        out.append(self._render(body, scopes + [scope]))
                elif truthy:
                    scope = val if isinstance(val, dict) else {}
                    out.append(self._render(body, scopes + [scope]))
        return "".join(out)


_TPL_CACHE: dict[str, Template] = {}


def load_template(name: str) -> Template:
    if name not in _TPL_CACHE:
        path = TEMPLATES / f"{name}.html"
        if not path.exists():
            raise FileNotFoundError(f"テンプレートが見つかりません: {path}")
        _TPL_CACHE[name] = Template(path.read_text(encoding="utf-8"), load_template)
    return _TPL_CACHE[name]


def esc(value) -> str:
    if value is None or value is False:
        return ""
    s = str(value)
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


# ---------------------------------------------------------------- Markdown
_INLINE = [
    (re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)"), r'<img src="\2" alt="\1" loading="lazy">'),
    (re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)"), r'<a href="\2" target="_blank" rel="noopener">\1</a>'),
    (re.compile(r"\*\*([^*]+)\*\*"), r"<strong>\1</strong>"),
    (re.compile(r"(?<!\*)\*([^*\n]+)\*(?!\*)"), r"<em>\1</em>"),
]


def markdown(text: str) -> str:
    """記事本文用の最小 Markdown。見出し・段落・リスト・画像・リンク・引用に対応。"""
    html, buf, mode = [], [], None

    def flush():
        nonlocal buf, mode
        if not buf:
            mode = None
            return
        if mode == "p":
            html.append("<p>" + "<br>".join(buf) + "</p>")
        elif mode == "ul":
            html.append("<ul>" + "".join(f"<li>{x}</li>" for x in buf) + "</ul>")
        elif mode == "ol":
            html.append("<ol>" + "".join(f"<li>{x}</li>" for x in buf) + "</ol>")
        elif mode == "quote":
            html.append("<blockquote>" + "<br>".join(buf) + "</blockquote>")
        buf, mode = [], None

    for raw_line in text.replace("\r\n", "\n").split("\n"):
        line = raw_line.rstrip()
        stripped = line.strip()

        if not stripped:
            flush()
            continue
        if stripped.startswith("<"):  # 生の HTML 行はそのまま通す
            flush()
            html.append(stripped)
            continue

        inline = esc(stripped)
        for pattern, repl in _INLINE:
            inline = pattern.sub(repl, inline)

        m = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if m:
            flush()
            level = len(m.group(1)) + 1  # 記事内の最上位は h2
            body = esc(m.group(2))
            for pattern, repl in _INLINE:
                body = pattern.sub(repl, body)
            html.append(f"<h{level}>{body}</h{level}>")
            continue
        if re.match(r"^(-{3,}|\*{3,})$", stripped):
            flush()
            html.append("<hr>")
            continue
        if stripped.startswith("> "):
            if mode != "quote":
                flush()
                mode = "quote"
            buf.append(inline[2:])
            continue
        if re.match(r"^[-*]\s+", stripped):
            if mode != "ul":
                flush()
                mode = "ul"
            buf.append(re.sub(r"^[-*]\s+", "", inline))
            continue
        if re.match(r"^\d+\.\s+", stripped):
            if mode != "ol":
                flush()
                mode = "ol"
            buf.append(re.sub(r"^\d+\.\s+", "", inline))
            continue

        if mode not in ("p", None):
            flush()
        mode = "p"
        buf.append(inline)

    flush()
    return "\n".join(html)


# ---------------------------------------------------------------- コンテンツ
def nl2p(text: str) -> str:
    """改行区切りの平文を段落 HTML にする。空行で段落、単独改行は <br>。"""
    blocks = [b.strip() for b in str(text).split("\n\n") if b.strip()]
    if not blocks:
        return ""
    return "".join("<p>" + "<br>".join(esc(l) for l in b.split("\n")) + "</p>" for b in blocks)


def enrich(node):
    """コンテンツ JSON を描画しやすい形に整える。

    - `xxx_md`   → `xxx_html`（Markdown を HTML 化）
    - `text`/`a` → `text_html`/`a_html`（改行を段落・<br> に）
    - `title`/`value` に改行があれば `title_html`/`value_html` を追加
    - フォーム項目には is_text / is_select などの判定フラグを付与
    """
    if isinstance(node, list):
        return [enrich(v) for v in node]
    if not isinstance(node, dict):
        return node

    out = {k: enrich(v) for k, v in node.items()}

    for key, value in list(out.items()):
        if key.endswith("_md") and isinstance(value, str):
            out[key[:-3] + "_html"] = markdown(value)

    for key in ("text", "a", "answer"):
        if isinstance(out.get(key), str) and out[key]:
            out[key + "_html"] = nl2p(out[key])

    for key in ("title", "value", "heading", "catch", "name"):
        if isinstance(out.get(key), str) and "\n" in out[key]:
            out[key + "_html"] = "<br>".join(esc(l) for l in out[key].split("\n"))
    for key in ("title", "value"):
        if isinstance(out.get(key), str) and key + "_html" not in out:
            out[key + "_html"] = esc(out[key])

    # 会社情報の表で、電話番号の行はタップで発信できるようにする
    if out.get("key") in ("電話番号", "TEL", "tel") and isinstance(out.get("value"), str):
        digits = re.sub(r"[^0-9+]", "", out["value"])
        if len(digits) >= 10:
            out["is_tel"] = True
            out["tel_href"] = digits

    # フォーム項目のフラグと送信先フィールド名
    if "key" in out and "label" in out and "type" in out:
        kind = out["type"]
        out["is_textarea"] = kind == "textarea"
        out["is_select"] = kind == "select"
        out["is_radio"] = kind == "radio"
        out["is_text"] = kind in ("text", "tel", "email")

    return out


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"JSON の書式エラー: {path}\n  {e}")


def parse_front_matter(text: str) -> tuple[dict, str]:
    """--- で囲んだ YAML 風ヘッダ（key: value のみ）と本文に分ける。"""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    meta: dict = {}
    for line in text[3:end].strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        value = value.strip().strip('"').strip("'")
        if value.startswith("[") and value.endswith("]"):
            items = [v.strip().strip('"').strip("'") for v in value[1:-1].split(",")]
            meta[key.strip()] = [v for v in items if v]
        else:
            meta[key.strip()] = value
    return meta, text[end + 4 :].lstrip("\n")


def today_jst() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d")


def clean_time(value) -> str:
    """時刻を HH:MM にそろえる。空や書式違いは空文字にする。"""
    m = re.match(r"^\s*(\d{1,2})\s*[:：]\s*(\d{1,2})", str(value or ""))
    if not m:
        return ""
    h, mi = int(m.group(1)), int(m.group(2))
    return f"{h:02d}:{mi:02d}" if 0 <= h <= 23 and 0 <= mi <= 59 else ""


def publish_at(date, time="") -> str:
    """並べ替えと公開判定に使う「日付＋時刻」。時刻なしは 00:00 として扱う。"""
    return f"{str(date or '')[:10]} {clean_time(time) or '00:00'}"


def is_scheduled(date, time="") -> bool:
    """公開日時がまだ来ていなければ「予約投稿」。"""
    if not date:
        return False
    return publish_at(date, time) > datetime.now(JST).strftime("%Y-%m-%d %H:%M")


def load_posts(folder: Path, kind: str, include_future: bool = False) -> list[dict]:
    posts = []
    for path in sorted(folder.glob("*.md")):
        meta, body = parse_front_matter(path.read_text(encoding="utf-8"))
        slug = meta.get("slug") or path.stem
        date = meta.get("date", "")
        time = clean_time(meta.get("time", ""))
        # 公開日時がまだ来ていない記事は、公開サイトには出さない
        if is_scheduled(date, time) and not include_future:
            continue
        posts.append(
            {
                **meta,
                "kind": kind,
                "slug": slug,
                "url": f"/{kind}/{slug}/",
                "date": date,
                "time": time,
                "date_display": format_date(date),
                "is_scheduled": is_scheduled(date, time),
                "publish_at": publish_at(date, time),
                "body_md": body,
                "body_html": markdown(body),
                "source_file": str(path.relative_to(ROOT)),
            }
        )
    posts.sort(key=lambda p: (p.get("publish_at", ""), p["slug"]), reverse=True)
    return posts


def format_date(value: str) -> str:
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            d = datetime.strptime(value, fmt)
            return f"{d.year}/{d.month}/{d.day}"
        except ValueError:
            continue
    return value


# ---------------------------------------------------------------- ビルド
def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_writable(path: Path) -> None:
    """「読み取り専用」を外す。ほかの権限はそのまま残す（Linux でも安全に動かすため）。"""
    try:
        os.chmod(path, os.stat(path).st_mode | stat.S_IWRITE)
    except OSError:
        pass


def remove_path(path: Path, tries: int = 5) -> None:
    """ファイル／フォルダを消す。

    OneDrive はフォルダに「読み取り専用」属性をつけることがあり、そのままだと
    Windows では削除できない（アクセスが拒否されました）。属性を外してから消す。
    一瞬つかまれているだけのこともあるので、少し待って数回やり直す。
    """
    for attempt in range(tries):
        try:
            if path.is_dir() and not path.is_symlink():
                for child in path.iterdir():
                    remove_path(child, tries)
                make_writable(path)
                path.rmdir()
            elif path.exists():
                make_writable(path)
                path.unlink()
            return
        except PermissionError:
            if attempt == tries - 1:
                raise
            time.sleep(0.3 * (attempt + 1))


def clean_dist() -> None:
    """dist/ の生成物を消す。assets/ は残し、sync_assets() で差分更新する。

    以前は dist/ をまるごと rmtree していたが、OneDrive 同期フォルダの中では
    削除が途中で PermissionError になることがある。そうなると画像や CSS だけが
    消えた壊れた dist/ が残り、サイトのレイアウトが崩れてしまう。
    """
    DIST.mkdir(parents=True, exist_ok=True)
    for child in DIST.iterdir():
        if child.name == "assets":
            continue
        remove_path(child)


def sync_assets() -> None:
    """assets/ を dist/assets/ へ差分コピーする。

    毎回まるごとコピーし直すと 40MB 超・数百ファイルの削除と作成が毎回発生し、
    OneDrive の同期とぶつかる。中身が変わったものだけ入れ替える。
    """
    dest_root = DIST / "assets"
    dest_root.mkdir(parents=True, exist_ok=True)

    wanted = set()
    for src in ASSETS.rglob("*"):
        if src.is_dir() or src.name == ".DS_Store":
            continue
        rel = src.relative_to(ASSETS)
        wanted.add(rel)
        dest = dest_root / rel
        if dest.exists():
            s, d = src.stat(), dest.stat()
            if s.st_size == d.st_size and abs(s.st_mtime - d.st_mtime) <= 2:
                continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)

    # assets/ から消したファイルは dist/ からも消す
    for dest in list(dest_root.rglob("*")):
        if dest.is_file() and dest.relative_to(dest_root) not in wanted:
            remove_path(dest)


def build(include_future: bool = False) -> dict:
    """include_future=True のときは、公開予定日が未来の記事もあわせて生成する
    （手元でのプレビュー用。公開サイトの生成では使わない）。"""
    site = read_json(CONTENT / "site.json")
    pages = {p.stem: enrich(read_json(p)) for p in sorted((CONTENT / "pages").glob("*.json"))}

    # フォームの各項目に、送信先（Google フォーム）の entry.xxx を割り当てる
    for page in pages.values():
        entries = (page.get("google_form") or {}).get("entries") or {}
        for field in page.get("fields") or []:
            field["entry_name"] = entries.get(field["key"]) or field["key"]
    blog = load_posts(CONTENT / "blog", "blog", include_future)
    recruit = load_posts(CONTENT / "recruit", "recruit", include_future)

    # --- インスタグラム欄 -------------------------------------------------
    # 表示のオン・オフは site.json の home_bottom、投稿の中身は instagram.json。
    # 将来「自動で取ってくる」仕組みを足すときも、instagram.json を書き換えるだけでよい。
    bottom = site.get("home_bottom") or {}
    ig_file = CONTENT / "instagram.json"
    ig_all = (read_json(ig_file).get("posts") or []) if ig_file.exists() else []
    ig_posts = [x for x in ig_all if x.get("image")][: bottom.get("instagram_count", 4)]
    ig_block = {
        "posts": ig_posts,
        "profile_url": (site.get("social") or {}).get("instagram", ""),
    }
    show_ig = bool(bottom.get("show_instagram")) and bool(ig_posts)
    ig_first = bool(bottom.get("instagram_first"))

    clean_dist()

    site["build_time"] = datetime.now(JST).strftime("%Y-%m-%d %H:%M")
    site["year"] = datetime.now(JST).year

    # デザインファイル（CSS・JS）の中身から短い番号を作り、読み込み先に付ける。
    # これがないと、更新してもブラウザが古いデザインを覚えたままになることがある。
    fingerprint = hashlib.sha1()
    for rel in ("css/style.css", "js/main.js"):
        f = ASSETS / rel
        if f.exists():
            fingerprint.update(f.read_bytes())
    site["asset_version"] = fingerprint.hexdigest()[:8]

    def base_ctx(page: dict, extra: dict | None = None) -> dict:
        ctx = {
            "site": site,
            "page": page,
            "blog": blog,
            "recruit": recruit,
            "blog_latest": blog[: site.get("blog_home_count", 4)],
            # トップページのスタッフ欄は、スタッフ紹介ページの内容をそのまま使う
            "staff_members": (pages.get("staff") or {}).get("members", []),
            "show_blog": bottom.get("show_blog", True),
            "instagram_top": ig_block if (show_ig and ig_first) else None,
            "instagram_bottom": ig_block if (show_ig and not ig_first) else None,
        }
        if extra:
            ctx.update(extra)
        return ctx

    written: list[str] = []

    def emit(url_path: str, template: str, ctx: dict) -> None:
        html = load_template(template).render(ctx)
        out = DIST / (url_path.strip("/") + "/index.html") if url_path != "/" else DIST / "index.html"
        write(out, html)
        written.append(url_path)

    # --- 固定ページ -------------------------------------------------------
    for key, page in pages.items():
        page.setdefault("slug", key)
        url = "/" if key == "home" else f"/{key}/"
        page["url"] = url
        template = page.get("template", "page")
        emit(url, template, base_ctx(page, {"page_key": key}))

    # --- 記事一覧・詳細 ---------------------------------------------------
    for kind, posts in (("blog", blog), ("recruit", recruit)):
        list_page = pages.get(kind, {"title": kind})
        for i, post in enumerate(posts):
            # 記事ごとに固有のタイトル・説明文を持たせる（一覧ページのものを引き継がない）
            seo_title = f"{post['title']}｜{site['name']}（奈良県香芝市）"
            post_ctx = base_ctx(
                {**list_page, **post, "url": post["url"],
                 "seo_title": seo_title,
                 "description": post.get("description") or list_page.get("description", "")},
                {
                    "post": post,
                    "prev_post": posts[i + 1] if i + 1 < len(posts) else None,
                    "next_post": posts[i - 1] if i > 0 else None,
                    "related": [p for p in posts if p["slug"] != post["slug"]][:4],
                },
            )
            emit(post["url"], f"{kind}-post", post_ctx)

    # --- 静的ファイル -----------------------------------------------------
    sync_assets()
    # static/ の中身は、そのまま公開フォルダの直下へ置く
    # （robots.txt、独自ドメイン用の CNAME など）
    static_dir = ROOT / "static"
    if static_dir.exists():
        for src in static_dir.rglob("*"):
            if src.is_file() and src.name != ".DS_Store":
                dest = DIST / src.relative_to(static_dir)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(src, dest)

    write(DIST / "sitemap.xml", build_sitemap(site, written))
    write(DIST / "404.html", load_template("404").render(base_ctx({"title": "ページが見つかりません"})))

    return {"pages": len(written), "blog": len(blog), "recruit": len(recruit)}


def build_sitemap(site: dict, urls: list[str]) -> str:
    base = site.get("base_url", "").rstrip("/")
    today = datetime.now(JST).strftime("%Y-%m-%d")
    items = "".join(
        f"<url><loc>{base}{u}</loc><lastmod>{today}</lastmod></url>" for u in sorted(set(urls))
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"{items}</urlset>"
    )


def main() -> None:
    stats = build()
    print(
        f"✅ ビルド完了  ページ {stats['pages']}件 / "
        f"ブログ {stats['blog']}件 / 採用 {stats['recruit']}件  → {DIST}"
    )
    if "--serve" in sys.argv:
        import http.server
        import socketserver

        port = 8000
        handler = lambda *a, **kw: http.server.SimpleHTTPRequestHandler(
            *a, directory=str(DIST), **kw
        )
        with socketserver.TCPServer(("", port), handler) as httpd:
            print(f"🌐 http://localhost:{port} で確認できます（Ctrl+C で終了）")
            httpd.serve_forever()


if __name__ == "__main__":
    main()
