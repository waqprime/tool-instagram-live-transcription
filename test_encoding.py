#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows環境でのエンコーディングテスト
"""

import sys
import os

# Windows環境での文字化け対策
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        if hasattr(sys.stdout, 'buffer') and sys.stdout.encoding.lower() != 'utf-8':
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        if hasattr(sys.stderr, 'buffer') and sys.stderr.encoding.lower() != 'utf-8':
            import io
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except (AttributeError, OSError):
        pass

print("=" * 60)
print("エンコーディングテスト")
print("=" * 60)

# システム情報
print(f"\nプラットフォーム: {sys.platform}")
print(f"Pythonバージョン: {sys.version}")
print(f"デフォルトエンコーディング: {sys.getdefaultencoding()}")
print(f"ファイルシステムエンコーディング: {sys.getfilesystemencoding()}")
print(f"stdout エンコーディング: {sys.stdout.encoding}")
print(f"stderr エンコーディング: {sys.stderr.encoding}")

# 環境変数
print(f"\nPYTHONIOENCODING: {os.environ.get('PYTHONIOENCODING', '未設定')}")

# 日本語テスト
print("\n" + "=" * 60)
print("日本語出力テスト")
print("=" * 60)
test_strings = [
    "こんにちは、世界！",
    "文字起こしテスト",
    "【ステップ1/3】動画ダウンロード",
    "[OK] 処理完了！",
    "[ERROR] エラーが発生しました",
    "Instagram Live/Reel MP3保存・文字起こしシステム"
]

for i, text in enumerate(test_strings, 1):
    print(f"{i}. {text}")

print("\n" + "=" * 60)
print("テスト完了")
print("=" * 60)
print("\n上記の日本語が正しく表示されていれば成功です。")
print("文字化けしている場合は、エンコーディング設定に問題があります。")
