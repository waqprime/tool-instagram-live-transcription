#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
内容要約モジュール
文字起こしテキストをビルトイン(Lambda経由) / Gemini API / OpenAI API で要約
"""

import os
import sys
from typing import Optional

# Windows環境での文字化け対策
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

DEFAULT_SUMMARY_PROMPT = (
    "以下の文字起こしテキストの内容を要約してください。\n"
    "重要なポイントを箇条書きでまとめ、最後に全体のまとめを記載してください。"
)

DEFAULT_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"

# ビルトイン要約エンドポイント（Lambda + API Gateway）
BUILTIN_ENDPOINT = "https://iuymmhyuc9.execute-api.ap-northeast-1.amazonaws.com/prod/summarize"
BUILTIN_GEMINI_MODEL = "gemini-2.5-flash-lite"
# アプリ識別トークン（レート制限用）
# 注意: このトークンは配布バイナリから抽出可能です。秘密鍵ではありません。
# 不正利用の防止はサーバー側のレート制限（2 req/sec, burst 5）+ IP制限で担保しています。
BUILTIN_APP_TOKEN = os.environ.get('BUILTIN_APP_TOKEN', '')


def _load_app_token():
    """ビルド済みアプリ用: .app_tokenファイルからトークンを読み込む"""
    global BUILTIN_APP_TOKEN
    if BUILTIN_APP_TOKEN:
        return
    import sys as _sys
    paths = []
    if getattr(_sys, '_MEIPASS', None):
        paths.append(os.path.join(_sys._MEIPASS, '.app_token'))
    paths.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.app_token'))
    for p in paths:
        if os.path.exists(p):
            try:
                with open(p, 'r') as f:
                    BUILTIN_APP_TOKEN = f.read().strip()
                return
            except Exception:
                pass


_load_app_token()


class ContentSummarizer:
    """文字起こしテキストをLLMで要約するクラス"""

    def __init__(
        self,
        provider: str = "builtin",
        api_key: Optional[str] = None,
        prompt: Optional[str] = None,
        summary_model: Optional[str] = None,
        gemini_api_key: Optional[str] = None,
        **kwargs,
    ):
        """
        Args:
            provider: 要約プロバイダ ("builtin", "openai", "gemini")
            api_key: OpenAI APIキー（openai使用時、省略時は環境変数から取得）
            prompt: 要約プロンプト（省略時はデフォルトプロンプト）
            summary_model: 使用するモデル名（省略時はプロバイダのデフォルト）
            gemini_api_key: Gemini APIキー（gemini使用時、省略時は環境変数から取得）
        """
        self.provider = provider
        self.prompt = prompt or DEFAULT_SUMMARY_PROMPT

        if provider == "builtin":
            # Lambda経由（APIキー不要）
            self.base_url = None
            self.model = BUILTIN_GEMINI_MODEL
            self.api_key = None
        elif provider == "gemini":
            self.base_url = DEFAULT_GEMINI_BASE_URL
            self.model = summary_model or DEFAULT_GEMINI_MODEL
            self.api_key = gemini_api_key or os.environ.get('GEMINI_API_KEY')
        else:
            self.base_url = None
            self.model = summary_model or "gpt-4o-mini"
            self.api_key = api_key or os.environ.get('OPENAI_API_KEY')

    def summarize(self, text: str, max_chars: int = 10000) -> Optional[str]:
        """
        文字起こしテキストを要約

        Args:
            text: 文字起こしテキスト
            max_chars: APIに送る最大文字数

        Returns:
            要約テキスト、失敗時はNone
        """
        if self.provider == "builtin":
            return self._summarize_builtin(text, max_chars)

        if not self.api_key:
            label = "OpenAI" if self.provider == "openai" else "Gemini"
            print(f"[WARNING] {label} APIキーが設定されていないため要約をスキップ", flush=True)
            return None

        if not text or not text.strip():
            print("[WARNING] 要約対象のテキストが空です", flush=True)
            return None

        try:
            from openai import OpenAI

            client_kwargs = {"api_key": self.api_key}
            if self.base_url:
                client_kwargs["base_url"] = self.base_url

            client = OpenAI(**client_kwargs)
            truncated_text = text[:max_chars]

            provider_label = "Gemini" if self.provider == "gemini" else "OpenAI"
            print(f"[INFO] 内容要約を生成中... ({provider_label}: {self.model})", flush=True)

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self.prompt,
                    },
                    {
                        "role": "user",
                        "content": truncated_text,
                    },
                ],
                max_tokens=2000,
                temperature=0.3,
            )

            summary = response.choices[0].message.content.strip()
            if summary:
                print("[OK] 内容要約を生成しました", flush=True)
                return summary

            return None

        except Exception as e:
            print(f"[WARNING] 内容要約エラー: {e}", flush=True)
            return None

    def _summarize_builtin(self, text: str, max_chars: int = 10000) -> Optional[str]:
        """ビルトインLambdaエンドポイント経由で要約"""
        import json

        if not text or not text.strip():
            print("[WARNING] 要約対象のテキストが空です", flush=True)
            return None

        truncated_text = text[:max_chars]
        print(f"[INFO] 内容要約を生成中... (ビルトイン: {self.model})", flush=True)

        try:
            import urllib.request
            import urllib.error

            payload = json.dumps({
                "text": truncated_text,
            }).encode("utf-8")

            req_headers = {"Content-Type": "application/json"}
            if BUILTIN_APP_TOKEN:
                req_headers["X-App-Token"] = BUILTIN_APP_TOKEN

            req = urllib.request.Request(
                BUILTIN_ENDPOINT,
                data=payload,
                headers=req_headers,
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=90) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            summary = result.get("summary", "")
            if summary:
                print("[OK] 内容要約を生成しました", flush=True)
                return summary

            error = result.get("error", "")
            if error:
                print(f"[WARNING] 要約エラー: {error}", flush=True)
            return None

        except Exception as e:
            print(f"[WARNING] ビルトイン要約エラー: {e}", flush=True)
            return None

    def save_summary(self, summary: str, output_path: str) -> Optional[str]:
        """
        要約をファイルに保存

        Args:
            summary: 要約テキスト
            output_path: 保存先ファイルパス

        Returns:
            保存したファイルパス、失敗時はNone
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(summary)
            print(f"[OK] 要約ファイル保存: {output_path}", flush=True)
            return output_path
        except Exception as e:
            print(f"[WARNING] 要約ファイル保存エラー: {e}", flush=True)
            return None
