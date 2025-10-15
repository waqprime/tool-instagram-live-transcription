#!/usr/bin/env python3
"""
Instagram動画ダウンローダー
yt-dlpを使用してInstagram LiveやReelをダウンロード
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional, Dict


class InstagramDownloader:
    """Instagram動画をダウンロードするクラス"""

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

    def download(self, url: str, output_filename: Optional[str] = None) -> Optional[str]:
        """
        Instagram動画をダウンロード

        Args:
            url: Instagram動画のURL
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
                    text=True
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
                # 最新のファイルを取得
                files = sorted(self.output_dir.glob("*"), key=os.path.getmtime)
                if files:
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
        動画情報を取得

        Args:
            url: Instagram動画のURL

        Returns:
            動画情報の辞書、失敗時はNone
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

    parser = argparse.ArgumentParser(description="Instagram動画ダウンローダー")
    parser.add_argument("url", help="Instagram動画のURL")
    parser.add_argument("-o", "--output", help="出力ディレクトリ", default="output")
    parser.add_argument("-n", "--name", help="出力ファイル名", default=None)

    args = parser.parse_args()

    downloader = InstagramDownloader(args.output)
    filepath = downloader.download(args.url, args.name)

    if filepath:
        print(f"\n保存先: {filepath}")
        return 0
    else:
        print("\nダウンロードに失敗しました")
        return 1


if __name__ == "__main__":
    sys.exit(main())
