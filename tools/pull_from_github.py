#!/usr/bin/env python3
"""
GitHubから最新を取り込む（ほかのパソコンでの変更を受け取る）

  python3 tools/pull_from_github.py

次の順に行います。
  1. このパソコンにまだ記録していない変更があれば、先に記録する（失われません）
  2. ほかのパソコンの変更を受け取る

「⓪ 最新を取り込む」から呼ばれます。編集を始める前に実行してください。
日本語の案内はすべてここにあります
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


def git(*args) -> subprocess.CompletedProcess:
    return subprocess.run([GIT, *args], cwd=ROOT, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")


def count(rng: str) -> int:
    r = git("rev-list", "--count", rng)
    try:
        return int((r.stdout or "0").strip())
    except ValueError:
        return 0


def bye(message: str, code: int = 1) -> None:
    print(message)
    sys.exit(code)


def main() -> None:
    if not GIT:
        bye("git が見つかりませんでした。\n\n"
            "かわりに GitHub Desktop を使ってください。\n"
            "  1. GitHub Desktop を開く\n"
            "  2. 上の「Fetch origin」を押す\n"
            "  3. 同じ場所が「Pull origin」に変わったら、それを押す")

    if not (ROOT / ".git").exists() or git("remote", "get-url", "origin").returncode != 0:
        bye("まだGitHubと連携していません。\n"
            "GitHub Desktop で「Publish repository」を先に行ってください。")

    print("GitHubに問い合わせています...")
    fetched = git("fetch", "--quiet", "origin")
    if fetched.returncode != 0:
        bye("\nGitHubに接続できませんでした。インターネット接続を確認してください。\n\n"
            + (fetched.stderr or ""))

    # 1) このパソコンの変更を先に記録する（受け取りで失われないように）
    if git("status", "--porcelain").stdout.strip():
        print("このパソコンにまだ記録していない変更があるので、先に記録します。")
        print(git("status", "--short").stdout.rstrip())
        print()
        git("add", "-A")
        stamp = datetime.now(JST).strftime("%Y-%m-%d %H:%M")
        git("commit", "-m", f"サイト更新 {stamp}")

    # 2) ほかのパソコンの変更を受け取る
    incoming = count("HEAD..@{u}")
    if not incoming:
        print("ほかのパソコンでの変更はありません。すでに最新の状態です。")
        unsent = count("@{u}..HEAD")
        if unsent:
            print(f"（このパソコンにまだ送っていない変更が {unsent} 件あります。"
                  "編集が終わったら「⑥ 変更をGitHubに送る」を実行してください）")
        return

    print(f"ほかのパソコンの変更 {incoming} 件を受け取ります...")
    merged = git("merge", "--no-edit", "@{u}")
    if merged.returncode != 0:
        git("merge", "--abort")
        bye("\n受け取りを中断しました。\n\n"
            "同じ場所を2台のパソコンで変更したため、自動でまとめられませんでした。\n"
            "このパソコンの変更は記録済みで、失われていません。\n"
            "このままの状態で、サポートにご相談ください。\n\n"
            + (merged.stdout or "") + (merged.stderr or ""))

    print()
    print("受け取りました。これで最新の状態です。")
    print("このまま「① 編集をはじめる」で編集できます。")


if __name__ == "__main__":
    main()
