#!/usr/bin/env python3
"""
変更をGitHubに送って公開する

  python3 tools/send_to_github.py

次の順に行います。
  1. このパソコンの変更を記録する（先に記録するので、受け取りで失われません）
  2. ほかのパソコンの変更を受け取る
  3. 受け取った内容もあわせて点検する
  4. GitHubへ送る

「⑥ 変更をGitHubに送る」から呼ばれます。日本語の案内はすべてここにあります
（バッチファイルに日本語を書くと、Windows が行の途中で読み違えることがあるため）。

編集画面（admin/server.py）も、保存のたびに同じ手順 send() を裏で呼んで自動で送ります。
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JST = timezone(timedelta(hours=9))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def find_git() -> str | None:
    """git を探す。GitHub Desktop に同梱されているものも探す。"""
    found = shutil.which("git")
    if found:
        return found
    local = os.environ.get("LOCALAPPDATA", "")
    if local:
        for app in sorted(Path(local).glob("GitHubDesktop/app-*"), reverse=True):
            exe = app / "resources" / "app" / "git" / "cmd" / "git.exe"
            if exe.exists():
                return str(exe)
    return None


GIT = find_git()


def git(*args, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run([GIT, *args], cwd=ROOT, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", check=check)


def count(rng: str) -> int:
    r = git("rev-list", "--count", rng)
    try:
        return int((r.stdout or "0").strip())
    except ValueError:
        return 0


def python_run(*args) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", env=env)


def bye(message: str, code: int = 1) -> None:
    print(message)
    sys.exit(code)


class SendFailed(Exception):
    """途中で止めた理由。message はそのまま画面に出せる日本語、detail は詳しい記録。"""

    def __init__(self, message: str, detail: str = ""):
        super().__init__(message)
        self.message = message
        self.detail = detail.strip()


def check_with_build() -> tuple[bool, str]:
    """公開サイトと同じ中身を作って点検する（⑥から実行したとき用）。

    点検のあとは、手元の表示を「公開予定の記事も見える状態」に戻す。
    """
    try:
        python_run("build.py", "--public")
        checked = python_run("tools/check.py")
        return checked.returncode == 0, (checked.stdout or "") + (checked.stderr or "")
    finally:
        python_run("build.py")


def unsent() -> bool:
    """このパソコンに、まだGitHubへ送っていない変更があるか。"""
    if not GIT:
        return False
    if git("status", "--porcelain").stdout.strip():
        return True
    return count("@{u}..HEAD") > 0


def send(say=print, check=check_with_build) -> tuple[bool, str]:
    """このパソコンの変更を記録し、ほかのパソコンの変更を受け取り、点検してから送る。

    戻り値は（送ったか, 案内文）。途中で止めたときは SendFailed を投げる。
    check は（点検に通ったか, 点検の記録）を返す関数。
    """
    if not GIT:
        raise SendFailed("git が見つかりませんでした。\n\n"
                         "かわりに GitHub Desktop を使ってください。\n"
                         "  1. GitHub Desktop を開く\n"
                         "  2. 左下に一言（例：サイト更新）を入れて「Commit to main」\n"
                         "  3. 上の「Push origin」を押す")

    if not (ROOT / ".git").exists() or git("remote", "get-url", "origin").returncode != 0:
        raise SendFailed("まだGitHubと連携していません。\n"
                         "GitHub Desktop で「Publish repository」を先に行ってください。")

    # 1) GitHubの最新を確認し、このパソコンの変更を先に記録する
    git("fetch", "--quiet", "origin")

    changed = git("status", "--porcelain").stdout.strip()
    if changed:
        say("今回の変更")
        say(git("status", "--short").stdout.rstrip())
        say("")
        git("add", "-A")
        stamp = datetime.now(JST).strftime("%Y-%m-%d %H:%M")
        git("commit", "-m", f"サイト更新 {stamp}")

    # 2) ほかのパソコンの変更を受け取る
    incoming = count("HEAD..@{u}")
    if incoming:
        say(f"ほかのパソコンの変更 {incoming} 件を受け取ります...")
        merged = git("merge", "--no-edit", "@{u}")
        if merged.returncode != 0:
            git("merge", "--abort")
            raise SendFailed("受け取りを中断しました。送信はしていません。\n\n"
                             "同じ場所を2台のパソコンで変更したため、自動でまとめられませんでした。\n"
                             "このパソコンの変更は記録済みで、失われていません。\n"
                             "このままの状態で、サポートにご相談ください。",
                             (merged.stdout or "") + (merged.stderr or ""))
        say("受け取りました。")
        say("")

    # 3) 受け取った内容もあわせて点検する（公開サイトと同じ中身で行う）
    ok, log = check()
    if not ok:
        raise SendFailed("点検で問題が見つかりました。直してからもう一度送ってください。\n"
                         "このパソコンの変更は記録済みです。失われていません。", log)

    # 4) GitHubへ送る
    if count("@{u}..HEAD") == 0:
        return False, "送るものはありません。すでに最新の状態です。"

    say("GitHubへ送信中...")
    pushed = git("push")
    if pushed.returncode != 0:
        raise SendFailed("送信できませんでした。インターネットにつながっているか確認して、もう一度送ってください。\n"
                         "それでも送れないときは、GitHub Desktop で「Push origin」を押してください。\n"
                         "記録はすでに済んでいるので、内容が失われることはありません。",
                         pushed.stderr or "")

    return True, ("送信しました。1〜2分でホームページに反映されます。\n"
                  "進み具合は GitHub の「Actions」タブで確認できます。")


def main() -> None:
    try:
        _, message = send()
    except SendFailed as e:
        bye("\n" + e.message + ("\n\n" + e.detail if e.detail else ""))
    print()
    print(message)


if __name__ == "__main__":
    main()
