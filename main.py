#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音声文字起こしシステム
各種プラットフォーム（Instagram, YouTube, X Spaces, Voicy等）から
動画・音声をダウンロードし、MP3抽出と文字起こしを実行
"""

import os
import sys
import argparse
import multiprocessing
from pathlib import Path
from typing import List, Optional
from datetime import datetime

# PyInstaller環境でのmultiprocessing対応
multiprocessing.freeze_support()

# Windows環境での文字化け対策
if sys.platform == 'win32':
    # PYTHONIOENCODING環境変数を設定
    os.environ['PYTHONIOENCODING'] = 'utf-8'

    # コンソール出力をUTF-8に設定（安全にラップ）
    try:
        if hasattr(sys.stdout, 'buffer') and sys.stdout.encoding.lower() != 'utf-8':
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        if hasattr(sys.stderr, 'buffer') and sys.stderr.encoding.lower() != 'utf-8':
            import io
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except (AttributeError, OSError):
        # PyInstallerやリダイレクト環境ではスキップ
        pass

from downloader import VideoDownloader
from audio_converter import AudioConverter
from transcriber import AudioTranscriber


class AudioTranscriptionProcessor:
    """各種プラットフォームの動画・音声を処理するメインクラス

    Instagram, YouTube, X Spaces, Voicy等、yt-dlp対応サイトから
    動画・音声をダウンロードし、MP3抽出と文字起こしを実行
    """

    def __init__(
        self,
        output_dir: str = "output",
        whisper_model: str = "base",
        language: str = "ja"
    ):
        """
        Args:
            output_dir: 出力ディレクトリ
            whisper_model: Whisperモデルサイズ
            language: 言語コード
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        print("=" * 60)
        print("音声文字起こしシステム")
        print("対応: Instagram, YouTube, X Spaces, Voicy等")
        print("=" * 60)

        # 各コンポーネントを初期化
        self.downloader = VideoDownloader(str(self.output_dir))
        self.converter = AudioConverter()
        self.transcriber = AudioTranscriber(whisper_model, language)

    def process_url(self, url: str, filename_prefix: Optional[str] = None) -> bool:
        """
        単一のURLを処理

        Args:
            url: 動画・音声のURL（Instagram, YouTube, X Spaces, Voicy等）
            filename_prefix: ファイル名のプレフィックス

        Returns:
            成功した場合True
        """
        print(f"\n{'=' * 60}")
        print(f"処理開始: {url}")
        print(f"{'=' * 60}\n")

        # ファイル名プレフィックスが指定されていない場合は自動生成
        if not filename_prefix:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename_prefix = f"video_{timestamp}"

        # ステップ1: 動画をダウンロード
        print("【ステップ1/3】動画ダウンロード")
        video_file = self.downloader.download(url, filename_prefix)
        if not video_file:
            print("[ERROR] ダウンロード失敗")
            return False

        # ステップ2: 音声をMP3に変換
        print(f"\n【ステップ2/3】音声抽出")
        mp3_file = self.converter.extract_audio(video_file)
        if not mp3_file:
            print("[ERROR] 音声抽出失敗")
            return False

        # 元の動画ファイルを削除（オプション）
        try:
            if video_file != mp3_file:
                os.remove(video_file)
                print(f"[OK] 元の動画ファイルを削除: {video_file}")
        except Exception as e:
            print(f"[WARNING] 動画ファイル削除時の警告: {e}")

        # ステップ3: 音声を文字起こし
        print(f"\n【ステップ3/3】文字起こし")
        result = self.transcriber.transcribe(mp3_file, str(self.output_dir))
        if not result:
            print("[ERROR] 文字起こし失敗")
            return False

        print(f"\n{'=' * 60}")
        print("[OK] 処理完了!")
        print(f"{'=' * 60}")
        print(f"MP3ファイル: {mp3_file}")
        print(f"文字起こし: {Path(mp3_file).stem}_transcript.txt")
        print(f"詳細情報: {Path(mp3_file).stem}_transcript.json")

        return True

    def process_urls_from_file(self, file_path: str) -> dict:
        """
        ファイルに記載されたURLを一括処理

        Args:
            file_path: URLが記載されたテキストファイル

        Returns:
            処理結果の統計情報
        """
        urls = self._read_urls_from_file(file_path)
        if not urls:
            print(f"[ERROR] URLが見つかりません: {file_path}")
            return {'total': 0, 'success': 0, 'failed': 0}

        print(f"\n処理するURL数: {len(urls)}")

        stats = {'total': len(urls), 'success': 0, 'failed': 0}

        for i, url in enumerate(urls, 1):
            print(f"\n\n{'#' * 60}")
            print(f"URL {i}/{len(urls)}")
            print(f"{'#' * 60}")

            # ファイル名のプレフィックスを生成
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            prefix = f"video_{timestamp}_{i}"

            if self.process_url(url, prefix):
                stats['success'] += 1
            else:
                stats['failed'] += 1

        # 最終結果を表示
        print(f"\n\n{'=' * 60}")
        print("全体の処理結果")
        print(f"{'=' * 60}")
        print(f"合計: {stats['total']}")
        print(f"成功: {stats['success']}")
        print(f"失敗: {stats['failed']}")

        return stats

    def _read_urls_from_file(self, file_path: str) -> List[str]:
        """
        ファイルからURLを読み込む

        Args:
            file_path: テキストファイルのパス

        Returns:
            URLのリスト
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # 空行とコメント行を除外、URL形式の行を抽出
            urls = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    # http/httpsで始まる行をURLとみなす
                    if line.startswith('http://') or line.startswith('https://'):
                        urls.append(line)

            return urls

        except Exception as e:
            print(f"[ERROR] ファイル読み込みエラー: {e}")
            return []


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="各種プラットフォームの動画・音声をMP3で保存して文字起こし（Instagram, YouTube, X Spaces, Voicy等）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # link.txtに記載されたURLを一括処理
  python main.py

  # 単一URLを処理（Instagram）
  python main.py --url "https://www.instagram.com/reel/..."

  # 単一URLを処理（YouTube）
  python main.py --url "https://www.youtube.com/watch?v=..."

  # 単一URLを処理（X Spaces）
  python main.py --url "https://twitter.com/i/spaces/..."

  # モデルとオプションを指定
  python main.py --model medium --language ja --output-dir ./results
        """
    )

    parser.add_argument(
        "-u", "--url",
        help="動画・音声のURL（Instagram, YouTube, X Spaces, Voicy等）"
    )
    parser.add_argument(
        "-f", "--file",
        default="link.txt",
        help="URLリストファイル（デフォルト: link.txt）"
    )
    parser.add_argument(
        "-m", "--model",
        default="base",
        choices=AudioTranscriber.MODELS,
        help="Whisperモデルサイズ（デフォルト: base）"
    )
    parser.add_argument(
        "-l", "--language",
        default="ja",
        help="言語コード（デフォルト: ja）"
    )
    parser.add_argument(
        "-o", "--output-dir",
        default="output",
        help="出力ディレクトリ（デフォルト: output）"
    )

    args = parser.parse_args()

    # プロセッサーを初期化
    processor = AudioTranscriptionProcessor(
        output_dir=args.output_dir,
        whisper_model=args.model,
        language=args.language
    )

    # 単一URL処理 or ファイル一括処理
    if args.url:
        success = processor.process_url(args.url)
        return 0 if success else 1
    else:
        if not Path(args.file).exists():
            print(f"[ERROR] エラー: ファイルが見つかりません: {args.file}")
            print(f"使い方: python main.py --url <動画・音声URL>")
            return 1

        stats = processor.process_urls_from_file(args.file)
        return 0 if stats['failed'] == 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n[ERROR] ユーザーによる中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] 予期しないエラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
