#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Obsidianノート書き出しモジュール
文字起こし結果をYAMLフロントマター付きMarkdownノートとして保存
"""

import os
import re
import sys
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime

# Windows環境での文字化け対策
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'


class ObsidianWriter:
    """文字起こし結果をObsidian Vaultにマークダウンノートとして保存するクラス"""

    def __init__(self, vault_path: str, subfolder: str = ""):
        """
        Args:
            vault_path: Obsidian Vaultのルートパス
            subfolder: Vault内のサブフォルダパス
        """
        self.vault_path = Path(vault_path)
        self.subfolder = subfolder

    def _get_output_dir(self) -> Path:
        """出力ディレクトリを取得（サブフォルダ考慮）"""
        if self.subfolder:
            output_dir = self.vault_path / self.subfolder
        else:
            output_dir = self.vault_path
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def _sanitize_filename(self, title: str, max_length: int = 100) -> str:
        """
        タイトルからファイル名として不正な文字を除去

        Args:
            title: 元のタイトル
            max_length: ファイル名の最大文字数

        Returns:
            サニタイズされたファイル名（拡張子なし）
        """
        # ファイル名に使えない文字を除去/置換
        sanitized = re.sub(r'[\\/:*?"<>|]', '', title)
        # 連続スペースを1つに
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        # 長さ制限
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length].rstrip()
        # 空になった場合のフォールバック
        if not sanitized:
            sanitized = datetime.now().strftime("Transcript_%Y%m%d_%H%M%S")
        return sanitized

    def _format_body(self, text: str, segments: Optional[List[Dict]] = None) -> str:
        """
        ノート本文を生成

        Args:
            text: 全文テキスト
            segments: セグメントリスト（speaker情報を含む場合あり）

        Returns:
            マークダウン形式の本文
        """
        # 話者情報付きセグメントがある場合
        if segments:
            has_speakers = any(seg.get('speaker') for seg in segments)
            if has_speakers:
                lines = []
                current_speaker = None
                for seg in segments:
                    speaker = seg.get('speaker', '')
                    seg_text = seg.get('text', '').strip()
                    if not seg_text:
                        continue
                    if speaker and speaker != current_speaker:
                        current_speaker = speaker
                        lines.append(f"\n**{speaker}:** {seg_text}")
                    else:
                        lines.append(seg_text)
                return '\n'.join(lines).strip()

        # 話者情報なし: 全文テキストをそのまま出力
        return text

    def save_note(
        self,
        title: str,
        text: str,
        segments: Optional[List[Dict]] = None,
        url: Optional[str] = None,
        source: Optional[str] = None,
        date: Optional[str] = None,
    ) -> Optional[str]:
        """
        Obsidianノートを保存

        Args:
            title: ノートタイトル
            text: 全文テキスト
            segments: セグメントリスト（speaker情報を含む場合あり）
            url: ソースURL
            source: ソース名（YouTube, Instagram等）
            date: 日付文字列

        Returns:
            保存したファイルパス、失敗時はNone
        """
        try:
            if not self.vault_path.exists():
                print(f"[ERROR] Obsidian Vaultが見つかりません: {self.vault_path}", flush=True)
                return None

            output_dir = self._get_output_dir()
            filename = self._sanitize_filename(title)
            filepath = output_dir / f"{filename}.md"

            # 同名ファイルが存在する場合はサフィックスを追加
            counter = 1
            while filepath.exists():
                filepath = output_dir / f"{filename}_{counter}.md"
                counter += 1

            # 日付のデフォルト
            if not date:
                date = datetime.now().strftime("%Y-%m-%d")

            # YAML frontmatter
            frontmatter_lines = ["---"]
            # タイトル中のコロンやクォートをエスケープ
            safe_title = title.replace('"', '\\"')
            frontmatter_lines.append(f'title: "{safe_title}"')
            if url:
                safe_url = url.replace('"', '%22')
                frontmatter_lines.append(f'url: "{safe_url}"')
            if source:
                safe_source = source.replace('"', '\\"')
                frontmatter_lines.append(f'source: "{safe_source}"')
            frontmatter_lines.append(f"date: {date}")
            frontmatter_lines.append("---")
            frontmatter = '\n'.join(frontmatter_lines)

            # 本文
            body = self._format_body(text, segments)

            # ファイル書き込み
            content = f"{frontmatter}\n\n{body}\n"
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

            print(f"[OK] Obsidianノート保存: {filepath}", flush=True)
            return str(filepath)

        except Exception as e:
            print(f"[WARNING] Obsidianノート保存エラー: {e}", flush=True)
            return None
