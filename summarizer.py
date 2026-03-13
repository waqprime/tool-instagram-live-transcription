#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
内容要約モジュール
文字起こしテキストをOpenAI API または ローカルLLM (Ollama) で要約
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

DEFAULT_OLLAMA_URL = "http://localhost:11434/v1"
DEFAULT_OLLAMA_MODEL = "gemma3"
DEFAULT_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"


class ContentSummarizer:
    """文字起こしテキストをLLMで要約するクラス"""

    def __init__(
        self,
        provider: str = "openai",
        api_key: Optional[str] = None,
        prompt: Optional[str] = None,
        ollama_url: Optional[str] = None,
        summary_model: Optional[str] = None,
        gemini_api_key: Optional[str] = None,
    ):
        """
        Args:
            provider: 要約プロバイダ ("openai", "ollama", "gemini")
            api_key: OpenAI APIキー（openai使用時、省略時は環境変数から取得）
            prompt: 要約プロンプト（省略時はデフォルトプロンプト）
            ollama_url: OllamaのAPIエンドポイント（省略時はデフォルト）
            summary_model: 使用するモデル名（省略時はプロバイダのデフォルト）
            gemini_api_key: Gemini APIキー（gemini使用時、省略時は環境変数から取得）
        """
        self.provider = provider
        self.prompt = prompt or DEFAULT_SUMMARY_PROMPT

        if provider == "ollama":
            self.base_url = ollama_url or DEFAULT_OLLAMA_URL
            self.model = summary_model or DEFAULT_OLLAMA_MODEL
            self.api_key = "ollama"  # Ollamaはダミーキーでよい
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
        if self.provider in ("openai", "gemini") and not self.api_key:
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

            provider_label = {"ollama": "Ollama", "gemini": "Gemini"}.get(self.provider, "OpenAI")
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
