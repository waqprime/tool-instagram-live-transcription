#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
動画・音声ダウンローダー
yt-dlpを使用して各種プラットフォームから動画・音声をダウンロード
対応: Instagram, YouTube, X Spaces, Voicy, Radiko, stand.fm等（yt-dlp対応サイト全て）
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional, Dict

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


class VideoDownloader:
    """各種プラットフォームから動画・音声をダウンロードするクラス

    yt-dlpを使用して、Instagram, YouTube, X Spaces, Voicy等、
    1,800以上のサイトから動画・音声をダウンロード
    """

    def __init__(self, output_dir: str = "output"):
        """
        Args:
            output_dir: 出力ディレクトリ
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def _get_yt_dlp_path(self) -> str:
        """yt-dlpの実行可能ファイルのパスを取得"""
        # Pythonモジュールとしてインポート
        try:
            import yt_dlp
            # yt-dlpモジュールがある場合はPythonモジュールとして実行
            return sys.executable
        except ImportError:
            # システムのyt-dlpコマンドを使用
            return "yt-dlp"

    def _progress_hook(self, d):
        """yt-dlpの進捗フック"""
        if d['status'] == 'downloading':
            # ダウンロード中の進捗
            if 'total_bytes' in d and d['total_bytes'] > 0:
                percent = (d['downloaded_bytes'] / d['total_bytes']) * 100
                print(f"[PROGRESS] ダウンロード: {percent:.1f}%", flush=True)
            elif 'total_bytes_estimate' in d and d['total_bytes_estimate'] > 0:
                percent = (d['downloaded_bytes'] / d['total_bytes_estimate']) * 100
                print(f"[PROGRESS] ダウンロード: {percent:.1f}%", flush=True)
        elif d['status'] == 'finished':
            print(f"[PROGRESS] ダウンロード: 100%", flush=True)

    def download(self, url: str, output_filename: Optional[str] = None) -> Optional[str]:
        """
        各種プラットフォームから動画・音声をダウンロード

        Args:
            url: 動画・音声のURL（Instagram, YouTube, X Spaces, Voicy等）
            output_filename: 出力ファイル名（拡張子なし）

        Returns:
            ダウンロードしたファイルのパス、失敗時はNone
        """
        try:
            if output_filename:
                output_template = str(self.output_dir / f"{output_filename}.%(ext)s")
            else:
                output_template = str(self.output_dir / "%(id)s.%(ext)s")

            print(f"ダウンロード中: {url}")

            # yt-dlpをPythonモジュールとして使用
            try:
                import yt_dlp

                ydl_opts = {
                    'outtmpl': output_template,
                    'format': 'best',
                    'nocheckcertificate': True,
                    'quiet': False,
                    'no_warnings': False,
                    'progress_hooks': [self._progress_hook],
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])

            except ImportError:
                # フォールバック: コマンドラインのyt-dlpを使用
                cmd = [
                    "yt-dlp",
                    "--no-check-certificates",
                    "-f", "best",
                    "-o", output_template,
                    url
                ]
                result = subprocess.run(
                    cmd,
                    check=True,
                    capture_output=True,
                    encoding='utf-8',
                    errors='replace'
                )

            # ダウンロードしたファイルを探す
            if output_filename:
                # 可能性のある拡張子をチェック
                for ext in ['mp4', 'webm', 'mkv', 'm4a']:
                    filepath = self.output_dir / f"{output_filename}.{ext}"
                    if filepath.exists():
                        print(f"[OK] ダウンロード完了: {filepath}")
                        return str(filepath)
            else:
                # 最新の動画ファイルを取得（ログファイルを除外）
                video_files = []
                for ext in ['mp4', 'webm', 'mkv', 'm4a']:
                    video_files.extend(self.output_dir.glob(f"*.{ext}"))

                if video_files:
                    files = sorted(video_files, key=os.path.getmtime)
                    print(f"[OK] ダウンロード完了: {files[-1]}")
                    return str(files[-1])

            print("[ERROR] ダウンロードしたファイルが見つかりません")
            return None

        except subprocess.CalledProcessError as e:
            print(f"[ERROR] ダウンロードエラー: {e}")
            print(f"stdout: {e.stdout}")
            print(f"stderr: {e.stderr}")
            return None
        except Exception as e:
            print(f"[ERROR] 予期しないエラー: {e}")
            return None

    def get_video_info(self, url: str) -> Optional[Dict]:
        """
        動画・音声情報を取得

        Args:
            url: 動画・音声のURL

        Returns:
            動画・音声情報の辞書、失敗時はNone
        """
        try:
            import yt_dlp

            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'nocheckcertificate': True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info

        except Exception as e:
            print(f"[ERROR] 情報取得エラー: {e}")
            return None


def main():
    """テスト用のメイン関数"""
    import argparse

    parser = argparse.ArgumentParser(description="動画・音声ダウンローダー（yt-dlp対応全サイト）")
    parser.add_argument("url", help="動画・音声のURL（Instagram, YouTube, X Spaces, Voicy等）")
    parser.add_argument("-o", "--output", help="出力ディレクトリ", default="output")
    parser.add_argument("-n", "--name", help="出力ファイル名", default=None)

    args = parser.parse_args()

    downloader = VideoDownloader(args.output)
    filepath = downloader.download(args.url, args.name)

    if filepath:
        print(f"\n保存先: {filepath}")
        return 0
    else:
        print("\nダウンロードに失敗しました")
        return 1


if __name__ == "__main__":
    sys.exit(main())
