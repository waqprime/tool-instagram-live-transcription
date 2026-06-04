#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ログ送信モジュール
process_log_*.txt の内容＋アプリ情報を、ビルトイン要約と同じ
AWS Lambda + API Gateway（X-App-Token認証）へ送信する。

トークン(.app_token)は summarizer.py が既に読み込むため、それを再利用する。
"""

import os
import sys
import json
import platform
from datetime import datetime
from typing import Optional

# Windows環境での文字化け対策
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# ログ送信エンドポイント（要約と同じ API Gateway の別ルート /logs を想定）
# 環境変数 LOGS_ENDPOINT で上書き可能。AWS側に /logs(POST) ルートを用意する必要がある。
LOGS_ENDPOINT = os.environ.get(
    "LOGS_ENDPOINT",
    "https://iuymmhyuc9.execute-api.ap-northeast-1.amazonaws.com/prod/logs",
)

# 送信するログの最大バイト数（巨大ログ対策。末尾を優先して送る）
MAX_LOG_BYTES = 256 * 1024


def _get_app_token() -> str:
    """summarizer の .app_token 読込ロジックを再利用してトークンを取得"""
    try:
        import summarizer
        if getattr(summarizer, "BUILTIN_APP_TOKEN", ""):
            return summarizer.BUILTIN_APP_TOKEN
    except Exception:
        pass
    return os.environ.get("BUILTIN_APP_TOKEN", "")


def scrub_pii(text: str) -> str:
    """送信前にログから個人情報（ユーザー名・ホームパス）を除去する"""
    if not text:
        return text

    import re
    import getpass

    # 1) 実際のホームディレクトリのフルパスを置換
    try:
        home = os.path.expanduser("~")
        if home and home not in ("", "/", "\\"):
            if home.startswith("/Users"):
                repl = "/Users/[user]"
            elif home.startswith("/home"):
                repl = "/home/[user]"
            else:
                repl = "[home]"
            text = text.replace(home, repl)
    except Exception:
        pass

    # 2) 汎用パターン: /Users/<名>/ , /home/<名>/ , /Volumes/<名>/ , X:\Users\<名>\
    text = re.sub(r'(/Users/)[^/\s"\':]+', r'\1[user]', text)
    text = re.sub(r'(/home/)[^/\s"\':]+', r'\1[user]', text)
    text = re.sub(r'(/Volumes/)[^/\s"\':]+', r'\1[volume]', text)
    text = re.sub(r'([A-Za-z]:\\Users\\)[^\\\s"\':]+', r'\1[user]', text)

    # 3) 念のためログインユーザー名トークン単体も置換
    try:
        user = getpass.getuser()
        if user and len(user) >= 3:
            text = re.sub(r'\b' + re.escape(user) + r'\b', '[user]', text)
    except Exception:
        pass

    # 4) APIキー・トークン類（書き込み時にマスク漏れした場合の保険）
    text = re.sub(r'sk-[A-Za-z0-9_\-]{12,}', 'sk-[REDACTED]', text)            # OpenAI
    text = re.sub(r'AIza[A-Za-z0-9_\-]{10,}', 'AIza[REDACTED]', text)          # Google/Gemini
    text = re.sub(r'(?i)bearer\s+[A-Za-z0-9._\-]{8,}', 'Bearer [REDACTED]', text)
    # key=value 形式（api_key / token / access_token / x-app-token / authorization / cookie）
    text = re.sub(
        r'(?i)(api[_-]?key|access[_-]?token|auth[_-]?token|x-app-token|authorization|password|secret|cookie)'
        r'(["\']?\s*[:=]\s*["\']?)[^\s"\'&]+',
        r'\1\2[REDACTED]',
        text,
    )
    # URLのクエリ/フラグメントを除去（?key=... 等にトークンが載るケース）
    text = re.sub(r'(https?://[^\s"\'<>]+?)[?#][^\s"\'<>]*', r'\1', text)

    return text


def read_log_tail(path: str, max_bytes: int = MAX_LOG_BYTES) -> str:
    """ログファイルの末尾 max_bytes を読み込む（巨大ファイル対策）"""
    with open(path, "rb") as f:
        f.seek(0, os.SEEK_END)
        size = f.tell()
        if size > max_bytes:
            f.seek(-max_bytes, os.SEEK_END)
            data = f.read()
            text = data.decode("utf-8", errors="replace")
            # 途中で切れた先頭行を捨てる
            nl = text.find("\n")
            if nl != -1:
                text = text[nl + 1:]
            text = "...(先頭を省略しました)...\n" + text
        else:
            f.seek(0)
            text = f.read().decode("utf-8", errors="replace")
    return text


def send_log(
    log_path: str,
    app_version: str = "",
    note: str = "",
    timeout: int = 30,
) -> dict:
    """
    ログ＋アプリ情報を開発者エンドポイントへ送信する。

    Returns:
        {"ok": bool, "error"?: str, "status"?: int}
    """
    if not LOGS_ENDPOINT:
        return {"ok": False, "error": "送信先エンドポイントが未設定です (LOGS_ENDPOINT)"}

    if not log_path or not os.path.exists(log_path):
        return {"ok": False, "error": f"ログファイルが見つかりません: {log_path}"}

    try:
        log_text = read_log_tail(log_path)
    except Exception as e:
        return {"ok": False, "error": f"ログ読込エラー: {e}"}

    # 個人情報（ユーザー名・ホームパス）を送信前に除去
    log_text = scrub_pii(log_text)
    safe_note = scrub_pii(note or "")

    payload = json.dumps({
        "log": log_text,
        "logFileName": os.path.basename(log_path),
        "appVersion": app_version or "",
        "platform": platform.system(),
        "arch": platform.machine(),
        "osRelease": platform.release(),
        "note": safe_note,
        "sentAt": datetime.now().astimezone().isoformat(),
    }).encode("utf-8")

    headers = {"Content-Type": "application/json"}
    token = _get_app_token()
    if token:
        headers["X-App-Token"] = token

    try:
        import urllib.request
        import urllib.error

        req = urllib.request.Request(
            LOGS_ENDPOINT,
            data=payload,
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
        return {"ok": True, "status": getattr(resp, "status", 200), "response": body[:500]}

    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            pass
        return {"ok": False, "error": f"HTTP {e.code}: {e.reason} {detail}".strip()}
    except urllib.error.URLError as e:
        return {"ok": False, "error": f"接続エラー: {e.reason}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
