#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
タイトル生成モジュール
URL→yt-dlpメタデータからタイトル取得、ローカルファイル→GPT APIでタイトル生成
"""

import os
import sys
from typing import Optional

# Windows環境での文字化け対策
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'


class TitleGenerator:
    """動画・音声のタイトルを取得/生成するクラス"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: OpenAI APIキー（GPTタイトル生成用、省略時は環境変数から取得）
        """
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY')

    def get_title_from_url(self, url: str, downloader=None) -> Optional[str]:
        """
        URLからyt-dlpメタデータを使ってタイトルを取得

        Args:
            url: 動画・音声のURL
            downloader: VideoDownloaderインスタンス（get_video_infoメソッドを使用）

        Returns:
            タイトル文字列、失敗時はNone
        """
        try:
            if downloader:
                info = downloader.get_video_info(url)
                if info and info.get('title'):
                    title = info['title']
                    print(f"[OK] タイトル取得: {title}", flush=True)
                    return title

            # downloaderがない場合は直接yt-dlpを使用
            try:
                import yt_dlp
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    if info and info.get('title'):
                        title = info['title']
                        print(f"[OK] タイトル取得: {title}", flush=True)
                        return title
            except Exception as e:
                print(f"[WARNING] yt-dlpでのタイトル取得失敗: {e}", flush=True)

            return None

        except Exception as e:
            print(f"[WARNING] タイトル取得エラー: {e}", flush=True)
            return None

    def generate_title_from_text(self, text: str, max_chars: int = 500) -> Optional[str]:
        """
        文字起こしテキストからGPT APIを使ってタイトルを生成

        Args:
            text: 文字起こしテキスト
            max_chars: GPTに送る最大文字数

        Returns:
            生成されたタイトル、失敗時はNone
        """
        if not self.api_key:
            print("[WARNING] OpenAI APIキーが設定されていないためタイトル生成をスキップ", flush=True)
            return None

        if not text or not text.strip():
            return None

        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key)
            truncated_text = text[:max_chars]

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "あなたは音声コンテンツのタイトルを生成するアシスタントです。与えられたテキストの内容を簡潔に要約した1行のタイトルを日本語で生成してください。タイトルのみを返してください。"
                    },
                    {
                        "role": "user",
                        "content": f"以下の文字起こしテキストに適切なタイトルを付けてください:\n\n{truncated_text}"
                    }
                ],
                max_tokens=100,
                temperature=0.3,
            )

            title = response.choices[0].message.content.strip()
            if title:
                # 不要な引用符を除去
                title = title.strip('"\'「」『』')
                print(f"[OK] GPTタイトル生成: {title}", flush=True)
                return title

            return None

        except Exception as e:
            print(f"[WARNING] GPTタイトル生成エラー: {e}", flush=True)
            return None
