#!/usr/bin/env python3
"""
クリケア訪問看護ステーション サイト管理画面（ローカル専用）

  python3 admin/server.py

http://localhost:8080 で管理画面が開きます。
・ページの文言編集（日本語のラベルつき）
・写真・イラストの差し替え、アップロード、並べ替え
・ブログ／採用記事の作成・編集・削除
・点検とプレビュー

このサーバーは自分のパソコンの中だけで動きます。インターネットには公開されません。
"""
from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
import sys
import urllib.parse
import webbrowser
from datetime import datetime, timedelta, timezone
import socket
import threading
from functools import partial
from http.server import BaseHTTPRequestHandler, SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ADMIN = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
IMAGES = ROOT / "assets" / "images"
DIST = ROOT / "dist"
PORT = 8080
PREVIEW_PORT = 8000          # 実際に空いていたポートを main() で入れ直します
PREVIEW_URL = "http://localhost:8000/"
JST = timezone(timedelta(hours=9))

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ADMIN))
sys.path.insert(0, str(ROOT / "tools"))
import build as builder  # noqa: E402
import labels as L  # noqa: E402
import fetch_instagram as ig  # noqa: E402

IMAGE_EXT = {".webp", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".avif"}


def esc(v) -> str:
    return html.escape("" if v is None else str(v))


# ------------------------------------------- インスタグラムから画像を取り込む
# アクセストークンは、このパソコンの中だけに保存します（.gitignore 済み）。
SECRETS = ADMIN / ".secrets.json"
IG_DIR = IMAGES / "instagram"


def read_secrets() -> dict:
    try:
        return json.loads(SECRETS.read_text(encoding="utf-8"))
    except Exception:
        return {}


def ig_token() -> str:
    return str(read_secrets().get("instagram_token") or "").strip()


def ig_save_token(token: str) -> None:
    data = read_secrets()
    data["instagram_token"] = token.strip()
    SECRETS.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ig_get(path: str, **params) -> dict:
    params["access_token"] = ig_token()
    return ig.get_json("https://graph.instagram.com/" + path + "?" + urllib.parse.urlencode(params))


def ig_recent(limit: int = 24) -> list:
    """最近の投稿を、写真つきで一覧にする。"""
    out = []
    for post in (ig_get("me/media", fields=ig.FIELDS, limit=limit).get("data") or []):
        src = ig.picture_of(post)
        if not src:
            continue
        out.append({
            "id": str(post.get("id", "")),
            "thumb": src,
            "caption": ig.tidy_caption(post.get("caption", "")),
            "date": str(post.get("timestamp", ""))[:10],
        })
    return out


def ig_message(e: Exception) -> str:
    """API のエラーを、読んで分かる日本語にする。"""
    text = str(e)
    if "400" in text or "401" in text or "190" in text:
        return "カギ（アクセストークン）が正しくないか、期限切れです。取り直して登録し直してください。"
    if "timed out" in text.lower() or "urlopen" in text.lower():
        return "インスタグラムに接続できませんでした。通信環境をご確認ください。"
    return f"取得できませんでした（{type(e).__name__}）"


def ig_import(media_id: str) -> str:
    """指定した投稿の写真を取り込み、サイト内のパスを返す。"""
    post = ig_get(str(media_id), fields=ig.FIELDS)
    src = ig.picture_of(post)
    if not src:
        raise ValueError("この投稿から写真を取り出せませんでした")
    name = re.sub(r"\W", "", str(post.get("id", "")))[:32] + ig.extension_of(src)
    dest = IG_DIR / name
    if not dest.exists() and not ig.download(src, dest):
        raise ValueError("写真を取り込めませんでした")
    return "/assets/images/instagram/" + name


# 「ページ」ではないが同じフォームで編集できるファイル
SPECIAL_PAGES = {
    "_site": (lambda: CONTENT / "site.json", "サイト全体の設定"),
}


def page_path(name: str):
    if name in SPECIAL_PAGES:
        return SPECIAL_PAGES[name][0]()
    return CONTENT / "pages" / f"{name}.json"


# ---------------------------------------------- HTML を「やさしい表記」に変換
# 元データは <span class="accent">…</span> と <br> しか使っていないので、
# 編集画面では [[…]] と改行で書けるようにする。
ACCENT_OPEN = '<span class="accent">'


def html_to_simple(value: str) -> str | None:
    """HTML → やさしい表記。想定外のタグが混ざっていたら None（生のまま編集）。"""
    text = value.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
    text = text.replace(ACCENT_OPEN, "[[").replace("</span>", "]]")
    return None if re.search(r"<[^>]+>", text) else text


def simple_to_html(value: str) -> str:
    """やさしい表記 → HTML。"""
    text = str(value).replace("\r\n", "\n")
    text = re.sub(r"\[\[(.+?)\]\]", lambda m: ACCENT_OPEN + m.group(1) + "</span>", text, flags=re.S)
    return text.replace("\n", "<br>")


# ================================================================= 画面の骨組み
def shell(title: str, body: str, active: str = "") -> bytes:
    pages = sorted((CONTENT / "pages").glob("*.json"))
    links = []
    for p in pages:
        data = json.loads(p.read_text(encoding="utf-8"))
        cls = " class=\"is-active\"" if active == "page:" + p.stem else ""
        links.append(f'<a href="/page/{p.stem}"{cls}>{esc(data.get("title", p.stem))}</a>')

    def count(kind: str) -> int:
        return len(list((CONTENT / kind).glob("*.md")))

    def item(href: str, label: str, key: str, badge: str = "") -> str:
        cls = " class=\"is-active\"" if active == key else ""
        b = f'<span class="sidebar__count">{badge}</span>' if badge else ""
        return f'<a href="{href}"{cls}>{label}{b}</a>'

    sidebar = f"""
<aside class="sidebar">
  <div class="sidebar__group">
    <p class="sidebar__title">ページ</p>
    {''.join(links)}
  </div>
  <div class="sidebar__group">
    <p class="sidebar__title">記事</p>
    {item('/list/blog', 'ブログ', 'list:blog', str(count('blog')))}
    {item('/list/recruit', '採用情報', 'list:recruit', str(count('recruit')))}
  </div>
  <div class="sidebar__group">
    <p class="sidebar__title">素材・設定</p>
    {item('/images', '画像ライブラリ', 'images')}
    {item('/page/_site', 'サイト全体の設定', 'page:_site')}
  </div>
  <div class="sidebar__group">
    <p class="sidebar__title">メンテナンス</p>
    {item('/check', '点検する', 'check')}
  </div>
</aside>"""

    modal = """
<div class="modal" id="imgModal" role="dialog" aria-modal="true" aria-label="画像を選ぶ">
  <div class="modal__panel">
    <div class="modal__head">
      <span class="modal__title">画像を選ぶ</span>
      <label class="btn btn--primary">
        パソコンからアップロード
        <input type="file" id="pickUpload" accept="image/*" multiple hidden>
      </label>
      <button class="btn" type="button" id="pickIg">インスタから選ぶ</button>
      <button class="btn" type="button" id="pickLib" hidden>画像ライブラリに戻る</button>
      <button class="btn btn--ghost" type="button" id="pickClose">閉じる</button>
    </div>
    <div class="modal__search"><input type="search" id="pickSearch" placeholder="ファイル名で絞り込む"></div>
    <div class="modal__body">
      <div class="pickgrid" id="pickGrid"></div>
      <div class="igsetup" id="igSetup" hidden>
        <p class="igsetup__lead">インスタグラムの投稿から写真を選べるようにします。<br>
          最初に一度だけ、読み取り用のカギ（アクセストークン）を登録してください。</p>
        <input type="password" id="igToken" placeholder="ここにカギを貼り付けます" autocomplete="off">
        <button class="btn btn--primary" type="button" id="igSave">登録する</button>
        <p class="igsetup__note">このカギは、このパソコンの中だけに保存されます。<br>
          GitHub には送られません。</p>
        <p class="igsetup__error" id="igError"></p>
      </div>
    </div>
  </div>
</div>"""

    return f"""<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}｜クリケア サイト管理</title>
<link rel="stylesheet" href="/static/admin.css">
</head><body>
<header class="topbar">
  <span class="topbar__brand">クリケア サイト管理</span>
  <div class="topbar__actions">
    <a class="btn" href="{PREVIEW_URL}" target="_blank">サイトを見る</a>
    <a class="btn" href="/">ホーム</a>
  </div>
</header>
<div class="layout">{sidebar}<div class="content"><div class="content__inner">{body}</div></div></div>
{modal}
<script src="/static/admin.js" defer></script>
</body></html>""".encode("utf-8")


# ================================================================= フォーム描画
def field_text(path: str, key: str, value, long: bool = False) -> str:
    label = L.label_for(key)
    if long or L.is_long(key) or (isinstance(value, str) and (len(value) > 70 or "\n" in value)):
        rows = max(3, min(18, str(value).count("\n") + 3))
        control = (
            f'<textarea data-path="{esc(path)}" rows="{rows}">{esc(value)}</textarea>'
        )
    else:
        control = f'<input type="text" data-path="{esc(path)}" value="{esc(value)}">'
    hint = ""
    if isinstance(value, str) and "<br>" in value:
        hint = '<p class="field__hint">&lt;br&gt; と書いたところで改行されます。</p>'
    return f'<div class="field"><label class="field__label">{esc(label)}</label>{control}{hint}</div>'


def field_rich(path: str, key: str, simple: str) -> str:
    """色つき文字と改行が使える入力欄。"""
    rows = max(2, min(10, simple.count("\n") + 2))
    return f'''
<div class="field">
  <label class="field__label">{esc(L.label_for(key))}</label>
  <textarea data-path="{esc(path)}" data-rich="1" rows="{rows}">{esc(simple)}</textarea>
  <p class="field__hint">
    改行したいところで <b>Enter</b> を押してください。<br>
    オレンジ色にしたい文字は <code>[[ ]]</code> で囲みます（例：<code>[[確かな看護]]と</code>）。
  </p>
</div>'''


def field_bool(path: str, key: str, value) -> str:
    checked = " checked" if value else ""
    return (
        f'<label class="check"><input type="checkbox" data-path="{esc(path)}"{checked}>'
        f"<span>{esc(L.label_for(key))}</span></label>"
    )


def field_number(path: str, key: str, value) -> str:
    return (
        f'<div class="field"><label class="field__label">{esc(L.label_for(key))}</label>'
        f'<input type="number" data-path="{esc(path)}" value="{esc(value)}"></div>'
    )


def field_image(path: str, key: str, value) -> str:
    """1枚の画像を差し替えるための入力欄。"""
    style = f' style="background-image:url(&quot;/asset{esc(value)}&quot;)"' if value else ""
    inner = "" if value else "画像なし"
    return f"""
<div class="field">
  <label class="field__label">{esc(L.label_for(key))}</label>
  <div class="imgfield">
    <div class="imgfield__preview"{style}>{inner}</div>
    <div class="imgfield__side">
      <input type="hidden" data-path="{esc(path)}" value="{esc(value)}">
      <div class="imgfield__buttons">
        <button class="btn btn--sm btn--primary" type="button" data-act="pick-image">画像を選ぶ</button>
        <button class="btn btn--sm" type="button" data-act="clear-image">外す</button>
      </div>
      <p class="imgfield__path">{esc(value) or "（未設定）"}</p>
    </div>
  </div>
</div>"""


def field_image_list(path: str, key: str, values: list, show_label: bool = True) -> str:
    items = []
    for i, v in enumerate(values):
        items.append(f"""
<div class="imglist__item">
  <img src="/asset{esc(v)}" alt="" loading="lazy">
  <input type="hidden" data-path="{esc(path)}[{i}]" value="{esc(v)}">
  <div class="imglist__tools">
    <button type="button" data-act="imglist-left" title="左へ">←</button>
    <button type="button" data-act="imglist-del" title="外す">✕</button>
    <button type="button" data-act="imglist-right" title="右へ">→</button>
  </div>
</div>""")
    label = (
        f'<label class="field__label">{esc(L.label_for(key))}（{len(values)}枚・左から順に並びます）</label>'
        if show_label else '<p class="field__hint" style="margin:0 0 8px">左から順に並びます。</p>'
    )
    return f"""
<div class="field">
  {label}
  <div class="imglist" data-base="{esc(path)}">
    {''.join(items)}
    <button class="imglist__add" type="button" data-act="imglist-add">＋ 追加</button>
  </div>
</div>"""


def field_lines(path: str, key: str, values: list, show_label: bool = True) -> str:
    label = f'<label class="field__label">{esc(L.label_for(key))}</label>' if show_label else ""
    return f"""
<div class="field">
  {label}
  <textarea data-path="{esc(path)}" data-lines="1" rows="{max(3, min(14, len(values) + 1))}">{esc(chr(10).join(str(v) for v in values))}</textarea>
  <p class="field__hint">1行に1件ずつ書きます。行を増やせば項目が増えます。</p>
</div>"""


def render_value(key: str, value, path: str) -> str:
    """値の種類に応じた入力欄を返す。"""
    if isinstance(value, bool):
        return field_bool(path, key, value)
    if isinstance(value, (int, float)):
        return field_number(path, key, value)
    if isinstance(value, str):
        if L.is_image(key):
            return field_image(path, key, value)
        if key.endswith("_html"):
            simple = html_to_simple(value)
            if simple is not None:
                return field_rich(path, key, simple)
        return field_text(path, key, value)
    if isinstance(value, list):
        if not value:
            return field_lines(path, key, [])
        if all(isinstance(v, str) for v in value):
            if L.is_image(key) or all(v.startswith("/assets/") for v in value):
                return field_image_list(path, key, value)
            return field_lines(path, key, value)
        return render_repeat(key, value, path)
    if isinstance(value, dict):
        return render_group(key, value, path)
    return ""


def render_group(key: str, data: dict, path: str) -> str:
    """入れ子のまとまり（小見出しつきの枠）。"""
    inner = "".join(
        render_value(k, v, f"{path}.{k}") for k, v in data.items() if k not in L.HIDDEN_KEYS
    )
    return (
        f'<div class="subsection"><p class="subsection__title">{esc(L.label_for(key))}</p>{inner}</div>'
    )


def render_repeat(key: str, items: list, path: str, show_label: bool = True) -> str:
    """同じ形の項目が並ぶもの（スタッフ・FAQ・表の行など）。追加と削除ができる。"""
    host_id = "rep_" + re.sub(r"\W", "_", path)
    cards = []
    for i, item in enumerate(items):
        body = "".join(
            render_value(k, v, f"{path}[{i}].{k}")
            for k, v in item.items()
            if k not in L.HIDDEN_KEYS
        )
        cards.append(f"""
<div class="repeat-item">
  <div class="repeat-item__head">
    <span class="repeat-item__no">{i + 1}</span>
    <div class="repeat-item__tools">
      <button class="btn btn--sm" type="button" data-act="repeat-up" title="上へ">↑</button>
      <button class="btn btn--sm" type="button" data-act="repeat-down" title="下へ">↓</button>
      <button class="btn btn--sm btn--danger" type="button" data-act="repeat-del">削除</button>
    </div>
  </div>
  {body}
</div>""")
    add = L.ADD_LABELS.get(key, "項目を追加")
    label = (
        f'<label class="field__label">{esc(L.label_for(key))}（{len(items)}件）</label>'
        if show_label else ""
    )
    return f"""
<div class="field">
  {label}
  <div id="{host_id}" data-base="{esc(path)}">{''.join(cards)}</div>
  <div class="repeat-add">
    <button class="btn btn--sm" type="button" data-act="repeat-add" data-host="#{host_id}">＋ {esc(add)}</button>
  </div>
</div>"""


def render_page_form(data: dict) -> str:
    """ページ全体のフォーム。上部に基本設定、以降はセクションごとの折りたたみ。"""
    basics, sections = {}, {}
    for k, v in data.items():
        if k in L.HIDDEN_KEYS:
            continue
        (sections if isinstance(v, (dict, list)) else basics).__setitem__(k, v)

    out = []
    if basics:
        inner = "".join(render_value(k, v, k) for k, v in basics.items())
        out.append(
            '<details class="section" open><summary>ページの基本設定'
            "（タイトル・検索結果の説明）</summary>"
            f'<div class="section__body">{inner}</div></details>'
        )

    for i, (k, v) in enumerate(sections.items()):
        # セクションの見出しと中身の見出しが二重にならないようにする
        if isinstance(v, dict):
            inner = "".join(
                render_value(k2, v2, f"{k}.{k2}") for k2, v2 in v.items() if k2 not in L.HIDDEN_KEYS
            )
            badge = ""
        elif isinstance(v, list) and v and all(isinstance(x, dict) for x in v):
            inner = render_repeat(k, v, k, show_label=False)
            badge = f"（{len(v)}件）"
        elif isinstance(v, list) and all(isinstance(x, str) for x in v):
            if L.is_image(k) or (v and all(x.startswith("/assets/") for x in v)):
                inner = field_image_list(k, k, v, show_label=False)
                badge = f"（{len(v)}枚）"
            else:
                inner = field_lines(k, k, v, show_label=False)
                badge = f"（{len(v)}件）"
        else:
            inner = render_value(k, v, k)
            badge = ""

        open_attr = " open" if i == 0 else ""
        out.append(
            f'<details class="section"{open_attr}><summary>{esc(L.label_for(k))}{badge}</summary>'
            f'<div class="section__body">{inner}</div></details>'
        )
    return "".join(out)


def savebar(url: str, note: str = "") -> str:
    return f"""
<div class="savebar">
  <button class="btn btn--primary" type="button" id="saveBtn" data-url="{esc(url)}">保存する</button>
  <span class="savebar__msg">{esc(note) or "保存すると、その場でサイトに反映されます。"}</span>
</div>"""


# ================================================================= 記事
def post_files(kind: str) -> list[Path]:
    return sorted((CONTENT / kind).glob("*.md"), reverse=True)


def read_post(path: Path):
    return builder.parse_front_matter(path.read_text(encoding="utf-8"))


def write_post(path: Path, meta: dict, body: str) -> None:
    lines = ["---"]
    for key, value in meta.items():
        safe = str(value).replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'{key}: "{safe}"')
    lines += ["---", ""]
    path.write_text("\n".join(lines) + body.replace("\r\n", "\n").strip() + "\n", encoding="utf-8")


def run_build():
    try:
        # 手元のプレビューでは、公開予定の記事もあわせて見えるようにする
        s = builder.build(include_future=True)
        return True, f"保存しました（ページ{s['pages']}件／ブログ{s['blog']}件／採用{s['recruit']}件）"
    except Exception as e:
        return False, f"保存はできましたが、サイト生成でエラーが出ました: {e}"


# ================================================================= 各画面
def view_home() -> str:
    blog = post_files("blog")
    recent = []
    for p in blog[:5]:
        meta, _ = read_post(p)
        thumb = meta.get("thumbnail", "")
        img = f'<img class="list__thumb" src="/asset{esc(thumb)}" alt="">' if thumb else '<div class="list__thumb"></div>'
        recent.append(f"""
<div class="list__row">
  {img}
  <div class="list__main">
    <div class="list__title">{esc(meta.get("title", p.stem))}</div>
    <div class="list__meta">{esc(meta.get("date", ""))}</div>
  </div>
  <a class="btn btn--sm" href="/post/blog/{urllib.parse.quote(p.name)}">編集</a>
</div>""")

    return f"""
<h1 class="page-title">こんにちは</h1>
<p class="page-note">左のメニューから、直したいページや記事を選んでください。</p>

<div class="toolbar">
  <a class="btn btn--primary" href="/new/blog">＋ ブログを書く</a>
  <a class="btn" href="/page/home">トップページを編集</a>
  <a class="btn" href="/images">画像ライブラリ</a>
  <a class="btn" href="{PREVIEW_URL}" target="_blank">サイトを見る</a>
</div>

<h2 style="font-size:15px;margin:28px 0 12px">最近のブログ</h2>
<div class="list">{''.join(recent)}</div>

<div class="section" style="margin-top:26px">
  <div class="section__body" style="border-top:0;padding-top:20px">
    <p style="margin:0 0 8px;font-weight:700">写真やイラストを差し替えるには</p>
    <p style="margin:0;color:#6e5a47;font-size:14px">
      各ページの編集画面で、画像の横にある「画像を選ぶ」ボタンを押してください。
      その場でパソコンから新しい写真をアップロードすることもできます。
    </p>
  </div>
</div>"""


def view_page(name: str) -> str:
    path = page_path(name)
    data = json.loads(path.read_text(encoding="utf-8"))
    title = SPECIAL_PAGES[name][1] if name in SPECIAL_PAGES else data.get("title", name)
    note = data.get("_comment", "")
    return (
        f'<h1 class="page-title">{esc(title)}</h1>'
        f'<p class="page-note">{esc(note)}</p>'
        + render_page_form(data)
        + savebar(f"/api/page/{name}")
    )


def view_list(kind: str) -> str:
    heading = "ブログ" if kind == "blog" else "採用情報"
    rows = []
    for p in post_files(kind):
        meta, _ = read_post(p)
        thumb = meta.get("thumbnail", "")
        img = f'<img class="list__thumb" src="/asset{esc(thumb)}" alt="">' if thumb else '<div class="list__thumb"></div>'
        waiting = builder.is_scheduled(meta.get("date", ""), meta.get("time", ""))
        badge = '<span class="badge badge--wait">公開予定</span>' if waiting else ""
        rows.append(f"""
<div class="list__row" data-search="{esc(meta.get('title',''))} {esc(meta.get('date',''))}">
  {img}
  <div class="list__main">
    <div class="list__title">{esc(meta.get("title", p.stem))}{badge}</div>
    <div class="list__meta">{esc(meta.get("date", ""))}</div>
  </div>
  <a class="btn btn--sm" href="/post/{kind}/{urllib.parse.quote(p.name)}">編集</a>
</div>""")
    waiting_count = sum(
        1 for q in post_files(kind) if builder.is_scheduled(read_post(q)[0].get("date", ""), read_post(q)[0].get("time", ""))
    )
    waiting_note = (
        f"　うち{waiting_count}件は公開予定です（その日が来ると自動で公開されます）。"
        if waiting_count else ""
    )
    return f"""
<h1 class="page-title">{heading}</h1>
<p class="page-note">{len(rows)}件あります。新しい順に並んでいます。{waiting_note}</p>
<div class="toolbar">
  <a class="btn btn--primary" href="/new/{kind}">＋ 新しく追加</a>
  <input type="search" id="listFilter" placeholder="タイトルで探す">
</div>
<div class="list">{''.join(rows)}</div>"""


META_LABELS = {
    "title": "タイトル", "date": "公開日（未来の日付にすると、その日まで公開されません）",
    "time": "公開時刻（15分ごとに確認し、その時刻を過ぎたら公開します）", "thumbnail": "サムネイル画像",
    "slug": "URLの文字（変えると記事のアドレスが変わります）", "description": "検索結果に出る説明文",
    "office": "事業所", "job_type": "職種", "employment": "雇用形態",
    "salary_summary": "給与（概要）", "location": "勤務地",
}


def post_form(kind: str, filename: str | None, meta: dict, body: str) -> str:
    is_new = filename is None
    fields = []
    fixed = ("title", "date", "time", "thumbnail")
    order = list(fixed) + [k for k in meta if k not in fixed]
    for key in order:
        if key not in meta and key not in fixed:
            continue
        value = meta.get(key, "")
        label = META_LABELS.get(key, key)
        if key == "thumbnail":
            style = f' style="background-image:url(&quot;/asset{esc(value)}&quot;)"' if value else ""
            fields.append(f"""
<div class="field">
  <label class="field__label">{esc(label)}</label>
  <div class="imgfield">
    <div class="imgfield__preview"{style}>{"" if value else "画像なし"}</div>
    <div class="imgfield__side">
      <input type="hidden" data-path="meta.thumbnail" value="{esc(value)}">
      <div class="imgfield__buttons">
        <button class="btn btn--sm btn--primary" type="button" data-act="pick-image">画像を選ぶ</button>
        <button class="btn btn--sm" type="button" data-act="clear-image">外す</button>
      </div>
      <p class="imgfield__path">{esc(value) or "（未設定）"}</p>
    </div>
  </div>
</div>""")
        elif key == "time":
            fields.append(
                f'<div class="field"><label class="field__label">{esc(label)}</label>'
                f'<input type="time" data-path="meta.time" value="{esc(builder.clean_time(value))}">'
                f'<p class="field__hint">空のままなら、その日の 0:00 に公開されます。</p></div>'
            )
        elif key == "description":
            fields.append(
                f'<div class="field"><label class="field__label">{esc(label)}</label>'
                f'<textarea data-path="meta.{key}" rows="2">{esc(value)}</textarea></div>'
            )
        else:
            fields.append(
                f'<div class="field"><label class="field__label">{esc(label)}</label>'
                f'<input type="text" data-path="meta.{key}" value="{esc(value)}"></div>'
            )

    title = "新しい記事" if is_new else "記事の編集"
    url = f"/api/new/{kind}" if is_new else f"/api/post/{kind}/{urllib.parse.quote(filename)}"
    delete = "" if is_new else f"""
<div class="section" style="margin-top:24px">
  <div class="section__body" style="border-top:0;padding-top:18px">
    <form method="post" action="/delete/{kind}/{urllib.parse.quote(filename)}"
          onsubmit="window.onbeforeunload=null;return confirm('この記事を削除します。よろしいですか？\\n（content/_trash に移動するので後から戻せます）')">
      <button class="btn btn--danger" type="submit">この記事を削除する</button>
    </form>
  </div>
</div>"""

    return f"""
<h1 class="page-title">{title}</h1>
<p class="page-note">{esc(filename or "新しく作成します")}</p>

<details class="section" open>
  <summary>記事の情報</summary>
  <div class="section__body">{''.join(fields)}</div>
</details>

<details class="section" open>
  <summary>本文</summary>
  <div class="section__body">
    <div class="field">
      <div class="toolbar" style="margin-bottom:8px">
        <button class="btn btn--sm btn--primary" type="button" data-act="insert-image" data-target="#bodyArea">
          本文に画像を入れる
        </button>
        <span style="font-size:12px;color:#6e5a47">カーソルの位置に写真が入ります</span>
      </div>
      <textarea id="bodyArea" class="tall" data-path="body">{esc(body)}</textarea>
      <p class="field__hint">
        改行はそのまま改行として表示されます。<br>
        見出しは行頭に <code>## </code>、箇条書きは <code>- </code>、リンクは <code>[表示する文字](URL)</code> と書きます。
      </p>
    </div>
  </div>
</details>
{delete}
{savebar(url)}"""


def view_post(kind: str, filename: str) -> str:
    meta, body = read_post(CONTENT / kind / filename)
    return post_form(kind, filename, meta, body)


def view_new(kind: str) -> str:
    today = datetime.now(JST).strftime("%Y-%m-%d")
    if kind == "blog":
        meta = {"title": "", "date": today, "time": "", "thumbnail": "", "description": ""}
    else:
        meta = {"title": "", "date": today, "time": "", "thumbnail": "", "office": "", "job_type": "",
                "employment": "", "salary_summary": "", "location": "", "description": ""}
    return post_form(kind, None, meta, "")


def list_images() -> list[str]:
    files = [p for p in IMAGES.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXT]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return ["/assets/images/" + p.name for p in files]


def view_images() -> str:
    used = set()
    if DIST.exists():
        for p in DIST.rglob("*.html"):
            used |= set(re.findall(r"/assets/images/([^\"'\s)]+)", p.read_text(encoding="utf-8")))

    cards = []
    for path in list_images():
        name = path.split("/")[-1]
        tag = "" if name in used else '<span style="color:#c0392b">未使用</span>　'
        cards.append(f"""
<figure data-search="{esc(name)}">
  <img src="/asset{esc(path)}" alt="" loading="lazy">
  <figcaption>{tag}{esc(name)}</figcaption>
  <div class="gallery__tools">
    <button class="btn btn--sm" type="button" data-copy="{esc(path)}">パスをコピー</button>
    <button class="btn btn--sm btn--danger" type="button" data-delete-image="{esc(path)}">削除</button>
  </div>
</figure>""")

    return f"""
<h1 class="page-title">画像ライブラリ</h1>
<p class="page-note">サイトで使う写真・イラストの置き場です。{len(cards)}点あります。</p>

<div class="dropzone" id="dropzone">
  <p style="margin:0 0 6px;font-weight:700">ここに写真をドラッグ＆ドロップ</p>
  <p style="margin:0;font-size:13px">またはクリックしてパソコンから選ぶ（複数まとめて可）</p>
  <input type="file" id="dropInput" accept="image/*" multiple hidden>
</div>

<div class="toolbar"><input type="search" id="listFilter" placeholder="ファイル名で探す"></div>
<div class="gallery">{''.join(cards)}</div>"""


def view_check() -> str:
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "check.py")],
        capture_output=True, text=True, cwd=ROOT,
    )
    return f"""
<h1 class="page-title">点検</h1>
<p class="page-note">リンク切れ・表示されない写真・記事の書式ミスを自動でチェックしました。</p>
<pre class="log">{esc(result.stdout + result.stderr)}</pre>"""


# ================================================================= HTTP
class Handler(BaseHTTPRequestHandler):
    server_version = "KuricareAdmin"

    def log_message(self, *a):
        pass

    # -- 送出 -----------------------------------------------------------
    def send_html(self, body: bytes, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, obj, status: int = 200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def redirect(self, location: str):
        self.send_response(303)
        self.send_header("Location", location)
        self.end_headers()

    def send_file(self, path: Path):
        if not path.is_file():
            return self.send_html(shell("見つかりません", "<p>ファイルがありません。</p>"), 404)
        types = {
            ".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
            ".js": "text/javascript; charset=utf-8", ".json": "application/json",
            ".webp": "image/webp", ".png": "image/png", ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg", ".gif": "image/gif", ".svg": "image/svg+xml",
            ".avif": "image/avif", ".pdf": "application/pdf", ".ico": "image/x-icon",
            ".xml": "application/xml", ".txt": "text/plain; charset=utf-8",
        }
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", types.get(path.suffix.lower(), "application/octet-stream"))
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    # -- GET ------------------------------------------------------------
    def do_GET(self):
        p = urllib.parse.unquote(urllib.parse.urlparse(self.path).path)
        try:
            if p == "/":
                return self.send_html(shell("ホーム", view_home()))
            if p.startswith("/static/"):
                return self.send_file(ADMIN / "static" / p[len("/static/"):])
            if p == "/images":
                return self.send_html(shell("画像ライブラリ", view_images(), "images"))
            if p == "/check":
                return self.send_html(shell("点検", view_check(), "check"))
            if p == "/api/images":
                return self.send_json({"images": list_images()})
            if p == "/api/instagram/media":
                if not ig_token():
                    return self.send_json({"configured": False, "items": []})
                try:
                    return self.send_json({"configured": True, "items": ig_recent()})
                except Exception as e:
                    return self.send_json({"configured": True, "items": [],
                                           "error": ig_message(e)})
            if p.startswith("/page/"):
                name = p[6:]
                return self.send_html(shell("編集", view_page(name), "page:" + name))
            if p.startswith("/list/"):
                kind = p[6:]
                return self.send_html(shell("一覧", view_list(kind), "list:" + kind))
            if p.startswith("/new/"):
                kind = p[5:]
                return self.send_html(shell("新規作成", view_new(kind), "list:" + kind))
            if p.startswith("/post/"):
                _, _, kind, name = p.split("/", 3)
                return self.send_html(shell("記事の編集", view_post(kind, name), "list:" + kind))
            if p.startswith("/asset/"):
                return self.send_file(ROOT / p[len("/asset/"):])
            if p.startswith("/preview"):
                # プレビューは別ポートのサーバーが担当する（CSS や画像のパスを本番と同じにするため）
                return self.redirect(PREVIEW_URL + p[len("/preview"):].lstrip("/"))
        except Exception as e:
            return self.send_html(shell("エラー", f'<pre class="log">{esc(e)}</pre>'), 500)
        self.send_html(shell("見つかりません", "<p>ページがありません。</p>"), 404)

    # -- POST -----------------------------------------------------------
    def body_bytes(self) -> bytes:
        return self.rfile.read(int(self.headers.get("Content-Length") or 0))

    def body_json(self):
        return json.loads(self.body_bytes().decode("utf-8"))

    def do_POST(self):
        p = urllib.parse.unquote(urllib.parse.urlparse(self.path).path)
        try:
            # --- ページ保存 -------------------------------------------
            if p.startswith("/api/page/"):
                name = p[len("/api/page/"):]
                path = page_path(name)
                original = json.loads(path.read_text(encoding="utf-8"))
                posted = restore_html(self.body_json())
                merged = dict(original)
                merged.update(posted)
                # 画面に出していない項目は元の値を残す
                for key in L.HIDDEN_KEYS:
                    if key in original:
                        merged[key] = original[key]
                path.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                ok, msg = run_build()
                return self.send_json({"ok": True, "message": msg} if ok else {"ok": False, "error": msg})

            # --- 記事保存 ---------------------------------------------
            if p.startswith("/api/post/") or p.startswith("/api/new/"):
                data = self.body_json()
                meta = {k: v for k, v in (data.get("meta") or {}).items()}
                body = data.get("body", "")
                if p.startswith("/api/new/"):
                    kind = p[len("/api/new/"):]
                    if not meta.get("title"):
                        return self.send_json({"ok": False, "error": "タイトルを入れてください"})
                    date = meta.get("date") or datetime.now(JST).strftime("%Y-%m-%d")
                    slug = meta.get("slug") or make_slug(meta["title"], kind)
                    meta["slug"] = slug
                    meta["date"] = date
                    filename = f"{date}-{slug}.md"
                    target = CONTENT / kind / filename
                    if target.exists():
                        return self.send_json({"ok": False, "error": "同じ名前の記事がすでにあります"})
                    redirect = f"/post/{kind}/{urllib.parse.quote(filename)}"
                else:
                    _, _, _, kind, filename = p.split("/", 4)
                    target = CONTENT / kind / filename
                    old_meta, _ = read_post(target)
                    meta = {**old_meta, **meta}
                    redirect = None
                write_post(target, meta, body)
                ok, msg = run_build()
                res = {"ok": ok, "message": msg} if ok else {"ok": False, "error": msg}
                if ok and redirect:
                    res["redirect"] = redirect
                return self.send_json(res)

            # --- 画像アップロード -------------------------------------
            if p == "/api/upload":
                return self.send_json({"paths": self.save_uploads()})

            if p == "/api/instagram/token":
                token = str(self.body_json().get("token", "")).strip()
                if not token:
                    return self.send_json({"ok": False, "error": "文字列が空です"})
                ig_save_token(token)
                try:
                    ig_recent(1)
                except Exception as e:
                    ig_save_token("")
                    return self.send_json({"ok": False, "error": ig_message(e)})
                return self.send_json({"ok": True})

            if p == "/api/instagram/import":
                try:
                    return self.send_json({"ok": True,
                                           "path": ig_import(self.body_json().get("id", ""))})
                except Exception as e:
                    return self.send_json({"ok": False, "error": ig_message(e)})

            # --- 画像削除 ---------------------------------------------
            if p == "/api/delete-image":
                rel = (self.body_json() or {}).get("path", "")
                name = Path(rel).name
                src = IMAGES / name
                if not src.is_file():
                    return self.send_json({"ok": False, "error": "見つかりませんでした"})
                trash = ROOT / "assets" / "_trash"
                trash.mkdir(exist_ok=True)
                shutil.move(str(src), str(trash / name))
                run_build()
                return self.send_json({"ok": True})

            # --- 記事削除 ---------------------------------------------
            if p.startswith("/delete/"):
                _, _, kind, filename = p.split("/", 3)
                target = CONTENT / kind / filename
                trash = CONTENT / "_trash"
                trash.mkdir(exist_ok=True)
                if target.exists():
                    shutil.move(str(target), str(trash / filename))
                run_build()
                return self.redirect(f"/list/{kind}")
        except Exception as e:
            return self.send_json({"ok": False, "error": str(e)}, 500)
        self.send_json({"ok": False, "error": "不明な操作です"}, 404)

    # -- アップロード処理 ------------------------------------------------
    def save_uploads(self) -> list[str]:
        ctype = self.headers.get("Content-Type", "")
        m = re.search(r"boundary=([^;]+)", ctype)
        if not m:
            raise ValueError("アップロード形式が不正です")
        boundary = ("--" + m.group(1).strip('"')).encode()
        data = self.body_bytes()
        saved = []
        for part in data.split(boundary):
            if b"filename=" not in part:
                continue
            header, _, content = part.partition(b"\r\n\r\n")
            fname = re.search(rb'filename="([^"]*)"', header)
            if not fname or not fname.group(1):
                continue
            raw = fname.group(1).decode("utf-8", "replace")
            safe = re.sub(r"[^\w.\-]", "_", Path(raw).name)
            if not safe or Path(safe).suffix.lower() not in IMAGE_EXT:
                continue
            target = IMAGES / safe
            i = 1
            while target.exists():
                target = IMAGES / f"{Path(safe).stem}-{i}{Path(safe).suffix}"
                i += 1
            target.write_bytes(content.rstrip(b"\r\n--"))
            saved.append("/assets/images/" + target.name)
        return saved


def restore_html(node):
    """やさしい表記で送られてきた *_html の項目を HTML に戻す。"""
    if isinstance(node, dict):
        return {
            k: (simple_to_html(v) if k.endswith("_html") and isinstance(v, str) else restore_html(v))
            for k, v in node.items()
        }
    if isinstance(node, list):
        return [restore_html(v) for v in node]
    return node


def make_slug(title: str, kind: str) -> str:
    """日本語タイトルからでも使える URL 用の文字列を作る。"""
    slug = re.sub(r"[^\w\-]+", "-", title, flags=re.ASCII).strip("-").lower()
    if not slug:
        slug = kind + "-" + datetime.now(JST).strftime("%H%M%S")
    return slug[:40]


def free_port(start: int = 8000, tries: int = 20) -> int:
    """空いているポートを探す。"""
    for port in range(start, start + tries):
        with socket.socket() as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return start


def start_preview_server() -> None:
    """dist/ をそのまま配信するサーバーを別ポートで動かす。

    本番と同じ「/」始まりのパスで CSS・画像・リンクが解決できるようにするため、
    管理画面（8080）とは別のポートを使います。
    """
    global PREVIEW_PORT, PREVIEW_URL
    PREVIEW_PORT = free_port(8000)
    PREVIEW_URL = f"http://localhost:{PREVIEW_PORT}/"

    handler = partial(SimpleHTTPRequestHandler, directory=str(DIST))
    server = ThreadingHTTPServer(("127.0.0.1", PREVIEW_PORT), handler)
    server.RequestHandlerClass.log_message = lambda *a, **kw: None
    threading.Thread(target=server.serve_forever, daemon=True).start()


def main() -> None:
    run_build()
    start_preview_server()
    url = f"http://localhost:{PORT}/"
    print(f"🛠  管理画面: {url}")
    print(f"👀 サイトのプレビュー: {PREVIEW_URL}")
    print("   終了するには Ctrl+C を押してください。")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
