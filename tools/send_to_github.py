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


def main() -> None:
    if not GIT:
        bye("git が見つかりませんでした。\n\n"
            "かわりに GitHub Desktop を使ってください。\n"
            "  1. GitHub Desktop を開く\n"
            "  2. 左下に一言（例：サイト更新）を入れて「Commit to main」\n"
            "  3. 上の「Push origin」を押す")

    if not (ROOT / ".git").exists() or git("remote", "get-url", "origin").returncode != 0:
        bye("まだGitHubと連携していません。\n"
            "GitHub Desktop で「Publish repository」を先に行ってください。")

    # 1) GitHubの最新を確認し、このパソコンの変更を先に記録する
    git("fetch", "--quiet", "origin")

    changed = git("status", "--porcelain").stdout.strip()
    if changed:
        print("今回の変更")
        print(git("status", "--short").stdout.rstrip())
        print()
        git("add", "-A")
        stamp = datetime.now(JST).strftime("%Y-%m-%d %H:%M")
        git("commit", "-m", f"サイト更新 {stamp}")

    # 2) ほかのパソコンの変更を受け取る
    incoming = count("HEAD..@{u}")
    if incoming:
        print(f"ほかのパソコンの変更 {incoming} 件を受け取ります...")
        merged = git("merge", "--no-edit", "@{u}")
        if merged.returncode != 0:
            git("merge", "--abort")
            bye("\n受け取りを中断しました。送信はしていません。\n\n"
                "同じ場所を2台のパソコンで変更したため、自動でまとめられませんでした。\n"
                "このパソコンの変更は記録済みで、失われていません。\n"
                "このままの状態で、サポートにご相談ください。\n\n"
                + (merged.stdout or "") + (merged.stderr or ""))
        print("受け取りました。")
        print()

    # 3) 受け取った内容もあわせて点検する
    # 送る前の点検は、公開サイトと同じ中身で行う
    python_run("build.py", "--public")
    checked = python_run("tools/check.py")
    if checked.returncode != 0:
        bye("点検で問題が見つかりました。直してからもう一度実行してください。\n"
            "このパソコンの変更は記録済みです。失われていません。\n\n"
            + (checked.stdout or "") + (checked.stderr or ""))

    # 4) GitHubへ送る
    if count("@{u}..HEAD") == 0:
        bye("送るものはありません。すでに最新の状態です。", 0)

    print("GitHubへ送信中...")
    pushed = git("push")
    if pushed.returncode != 0:
        bye("\n送信できませんでした。\n"
            "GitHub Desktop を開いて「Push origin」を押してみてください。\n"
            "記録はすでに済んでいるので、内容が失われることはありません。\n\n"
            + (pushed.stderr or ""))

    # 手元の表示は、公開予定の記事も見える状態に戻しておく
    python_run("build.py")

    print()
    print("送信しました。1〜2分でホームページに反映されます。")
    print("進み具合は GitHub の「Actions」タブで確認できます。")


if __name__ == "__main__":
    main()
