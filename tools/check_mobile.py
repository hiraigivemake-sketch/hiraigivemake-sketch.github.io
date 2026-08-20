#!/usr/bin/env python3
"""
スマートフォン・タブレット表示の点検

  python3 tools/check_mobile.py

主要ページを 320 / 375 / 390 / 768 / 1024px の画面幅で表示し、次を自動で調べます。

  ・横スクロールが起きていないか（画面からはみ出す要素がないか）
  ・文字が小さすぎないか（13px 未満）
  ・指で押す部分が小さすぎないか（ボタン・メニューは 40px 以上）

Google Chrome を使って実際に描画して調べるため、Chrome が必要です。
問題があれば終了コード 1 を返すので、自動実行にも使えます。
"""
from __future__ import annotations

import http.server
import json
import re
import shutil
import socket
import socketserver
import subprocess
import sys
import threading
import html as H
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "google-chrome",
    "chromium",
]

PAGES = [
    "/", "/service/", "/aboutus/", "/staff/", "/blog/", "/recruit/",
    "/contact/", "/entry/", "/privacypolicy/", "/sitemap/",
]
WIDTHS = [320, 375, 390, 768, 1024]

AUDIT_PAGE = """<!doctype html><meta charset="utf-8"><title>checking</title>
<style>body{margin:0}iframe{border:0}</style><div id="host"></div>
<script>
var PAGES = __PAGES__, WIDTHS = __WIDTHS__, out = [], queue = [];
WIDTHS.forEach(function(w){ PAGES.forEach(function(p){ queue.push([w,p]); }); });
function check(w, path, done) {
  var f = document.createElement("iframe");
  f.style.width = w + "px"; f.style.height = "900px"; f.src = path;
  f.onload = function () {
    setTimeout(function () {
      try {
        var d = f.contentDocument, win = f.contentWindow;
        var vw = d.documentElement.clientWidth, over = [], tiny = [], small = [];
        d.querySelectorAll("*").forEach(function (el) {
          if (el.classList.contains("skip-link") || el.closest(".mobile-menu")) return;
          var r = el.getBoundingClientRect();
          if (r.width > 0 && r.right > vw + 1)
            over.push(el.tagName.toLowerCase() + "." + (typeof el.className === "string" ? el.className.split(" ")[0] : "") + " w=" + Math.round(r.width));
        });
        d.querySelectorAll("p,li,td,th,figcaption,.post-card__title").forEach(function (el) {
          if (!el.textContent.trim()) return;
          var fs = parseFloat(win.getComputedStyle(el).fontSize);
          if (fs < 13) tiny.push(el.tagName.toLowerCase() + "=" + fs + "px");
        });
        d.querySelectorAll("a,button,input,select,textarea,summary,label").forEach(function (el) {
          if (el.closest(".mobile-menu")) return;
          if (el.tagName === "LABEL" && !el.querySelector("input")) return;
          if (el.tagName === "INPUT" && el.closest("label")) return;
          var r = el.getBoundingClientRect();
          if (r.width === 0 || r.height === 0) return;
          var cs = win.getComputedStyle(el);
          if (cs.display === "none" || cs.visibility === "hidden") return;
          var inlineText = el.tagName === "A" && (el.closest("p") || el.closest(".prose li") || el.closest(".article__body"));
          if (r.height < (inlineText ? 28 : 40))
            small.push(el.tagName.toLowerCase() + "[" + (el.textContent || "").trim().slice(0, 12) + "]=" + Math.round(r.width) + "x" + Math.round(r.height));
        });
        out.push({w:w, p:path, vw:vw, sw:d.documentElement.scrollWidth, over:over.slice(0,4),
                  tiny:Array.from(new Set(tiny)).slice(0,3), small:Array.from(new Set(small)).slice(0,5)});
      } catch (e) { out.push({w:w, p:path, err:e.message}); }
      f.remove(); done();
    }, 320);
  };
  document.getElementById("host").appendChild(f);
}
function next(){ if(!queue.length){document.title="DONE";document.getElementById("host").innerHTML="<pre id='r'>"+JSON.stringify(out)+"</pre>";return;} var j=queue.shift(); check(j[0],j[1],next); }
next();
</script>"""


def find_chrome() -> str | None:
    for c in CHROME_CANDIDATES:
        if Path(c).exists():
            return c
        found = shutil.which(c)
        if found:
            return found
    return None


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main() -> None:
    print("=" * 60)
    print("スマートフォン・タブレット表示の点検")
    print("=" * 60)

    chrome = find_chrome()
    if not chrome:
        print("\n⚠ Google Chrome が見つかりませんでした。")
        print("  この点検には Chrome が必要です。インストールしてから再度お試しください。")
        sys.exit(0)

    if not DIST.exists():
        print("\n⚠ dist フォルダがありません。先に python3 build.py を実行してください。")
        sys.exit(1)

    # 記事ページも1つだけ確認対象に加える
    pages = list(PAGES)
    for kind in ("blog", "recruit"):
        found = sorted((DIST / kind).glob("*/index.html"))
        if found:
            pages.append("/" + kind + "/" + found[0].parent.name + "/")

    audit = (AUDIT_PAGE
             .replace("__PAGES__", json.dumps(pages))
             .replace("__WIDTHS__", json.dumps(WIDTHS)))
    audit_file = DIST / "_mobile_audit.html"
    audit_file.write_text(audit, encoding="utf-8")

    port = free_port()
    handler_cls = type("Quiet", (http.server.SimpleHTTPRequestHandler,), {"log_message": lambda *a: None})
    server = socketserver.TCPServer(
        ("127.0.0.1", port),
        lambda *a, **kw: handler_cls(*a, directory=str(DIST), **kw),
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()

    print(f"\n{len(pages)}ページ × {len(WIDTHS)}種類の画面幅 = {len(pages)*len(WIDTHS)}件を確認します…")

    try:
        result = subprocess.run(
            [chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
             f"--virtual-time-budget={max(30000, len(pages)*len(WIDTHS)*900)}",
             "--window-size=1100,1000", "--dump-dom",
             f"http://127.0.0.1:{port}/_mobile_audit.html"],
            capture_output=True, text=True, timeout=300,
        )
    finally:
        server.shutdown()
        audit_file.unlink(missing_ok=True)

    m = re.search(r"<pre id=\"r\">(.*?)</pre>", result.stdout, re.S)
    if not m:
        print("\n⚠ 結果を取得できませんでした。Chrome の起動に失敗した可能性があります。")
        sys.exit(1)

    data = json.loads(H.unescape(m.group(1)))
    problems = []
    for r in data:
        issues = []
        if r.get("err"):
            issues.append("読み込みエラー: " + r["err"])
        if r.get("sw", 0) > r.get("vw", 0) + 1:
            issues.append(f"横スクロールが発生（画面 {r['vw']}px に対して中身 {r['sw']}px）")
        if r.get("over"):
            issues.append("画面からはみ出す要素: " + ", ".join(r["over"]))
        if r.get("tiny"):
            issues.append("文字が小さすぎる: " + ", ".join(r["tiny"]))
        if r.get("small"):
            issues.append("指で押しにくい大きさ: " + ", ".join(r["small"]))
        if issues:
            problems.append((r, issues))

    if problems:
        print(f"\n❌ 要対応 {len(problems)}件 / 全{len(data)}件")
        for r, issues in problems:
            print(f"\n■ 画面幅 {r['w']}px　{r['p']}")
            for i in issues:
                print("   ・" + i)
        sys.exit(1)

    print(f"\n✅ 全{len(data)}件、問題は見つかりませんでした。")
    print("   横スクロールなし／文字サイズ十分／タップ領域十分")


if __name__ == "__main__":
    main()
