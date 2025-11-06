#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
動画・音声ダウンローダー
yt-dlpを使用して各種プラットフォームから動画・音声をダウンロード
対応: Instagram, YouTube, X Spaces, Voicy, Radiko, stand.fm, UTAGE等（yt-dlp対応サイト全て）
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional, Dict, List
from utage_extractor import UtageExtractor

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

    yt-dlpを使用して、Instagram, YouTube, X Spaces, Voicy, UTAGE等、
    1,800以上のサイトから動画・音声をダウンロード
    """

    def __init__(self, output_dir: str = "output", keep_video: bool = False):
        """
        Args:
            output_dir: 出力ディレクトリ
            keep_video: 動画ファイルを保持するかどうか（UTAGE動画のMP4変換に使用）
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.utage_extractor = UtageExtractor()
        self.keep_video = keep_video
        self.is_utage_video = False  # UTAGE動画かどうかのフラグ

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
            url: 動画・音声のURL（Instagram, YouTube, X Spaces, Voicy, UTAGE等）
            output_filename: 出力ファイル名（拡張子なし）

        Returns:
            ダウンロードしたファイルのパス、失敗時はNone
        """
        try:
            # UTAGEページの場合、動画URLを抽出（単一動画のみ処理）
            if self.utage_extractor.is_utage_url(url):
                print(f"[INFO] UTAGEページを検出: {url}")
                self.is_utage_video = True  # UTAGEフラグを立てる

                # 複数動画がある可能性があるためチェック
                video_urls = self.utage_extractor.extract_video_urls(url)
                if video_urls:
                    if len(video_urls) > 1:
                        print(f"[INFO] 複数の動画を検出しました（{len(video_urls)}個）")
                        print(f"[INFO] 最初の動画のみダウンロードします: {video_urls[0]}")
                        print(f"[INFO] すべてダウンロードするには download_multiple() を使用してください")
                    video_url = video_urls[0]
                    print(f"[INFO] UTAGE動画URL: {video_url}")
                    url = video_url  # 抽出したm3u8 URLを使用
                else:
                    print(f"[ERROR] UTAGE動画URLの抽出に失敗")
                    return None
            else:
                self.is_utage_video = False

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
            downloaded_file = None
            if output_filename:
                # 可能性のある拡張子をチェック
                for ext in ['mp4', 'webm', 'mkv', 'm4a']:
                    filepath = self.output_dir / f"{output_filename}.{ext}"
                    if filepath.exists():
                        print(f"[OK] ダウンロード完了: {filepath}")
                        downloaded_file = str(filepath)
                        break
            else:
                # 最新の動画ファイルを取得（ログファイルを除外）
                video_files = []
                for ext in ['mp4', 'webm', 'mkv', 'm4a']:
                    video_files.extend(self.output_dir.glob(f"*.{ext}"))

                if video_files:
                    files = sorted(video_files, key=os.path.getmtime)
                    print(f"[OK] ダウンロード完了: {files[-1]}")
                    downloaded_file = str(files[-1])

            if not downloaded_file:
                print("[ERROR] ダウンロードしたファイルが見つかりません")
                return None

            # UTAGE動画でkeep_videoフラグが立っている場合、MP4に変換
            if self.is_utage_video and self.keep_video:
                print(f"[INFO] UTAGE動画をMP4形式に変換中...")
                from audio_converter import AudioConverter
                converter = AudioConverter()

                # MP4ファイル名を生成
                downloaded_path = Path(downloaded_file)
                mp4_file = str(downloaded_path.parent / f"{downloaded_path.stem}_converted.mp4")

                # MP4に変換
                converted_file = converter.convert_to_mp4(downloaded_file, mp4_file)
                if converted_file:
                    # 元のファイルを削除（変換後のMP4を保持）
                    try:
                        os.remove(downloaded_file)
                        print(f"[OK] 元のファイルを削除: {downloaded_file}")
                    except:
                        pass
                    return converted_file
                else:
                    print("[WARNING] MP4変換に失敗、元のファイルを使用します")
                    return downloaded_file

            return downloaded_file

        except subprocess.CalledProcessError as e:
            print(f"[ERROR] ダウンロードエラー: {e}")
            print(f"stdout: {e.stdout}")
            print(f"stderr: {e.stderr}")
            return None
        except Exception as e:
            print(f"[ERROR] 予期しないエラー: {e}")
            return None

    def download_multiple(self, url: str, output_filename_base: Optional[str] = None) -> List[str]:
        """
        UTAGE等の複数動画があるページから全動画をダウンロード

        Args:
            url: 動画ページのURL
            output_filename_base: 出力ファイル名のベース（拡張子なし）

        Returns:
            ダウンロードしたファイルパスのリスト
        """
        downloaded_files = []

        # UTAGEページの場合、全動画URLを抽出
        if self.utage_extractor.is_utage_url(url):
            print(f"[INFO] UTAGEページを検出: {url}")
            self.is_utage_video = True

            video_urls = self.utage_extractor.extract_video_urls(url)
            if not video_urls:
                print(f"[ERROR] UTAGE動画URLの抽出に失敗")
                return downloaded_files

            print(f"[INFO] {len(video_urls)}個の動画を検出しました")

            # 各動画をダウンロード
            for i, video_url in enumerate(video_urls, 1):
                print(f"\n[INFO] 動画 {i}/{len(video_urls)} をダウンロード中...")

                # ファイル名を生成
                if output_filename_base:
                    filename = f"{output_filename_base}_{i}"
                else:
                    filename = None

                # ダウンロード実行（extract_video_urlsで既にURLを取得しているので直接ダウンロード）
                try:
                    if filename:
                        output_template = str(self.output_dir / f"{filename}.%(ext)s")
                    else:
                        output_template = str(self.output_dir / f"video_{i}.%(ext)s")

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
                            ydl.download([video_url])

                    except ImportError:
                        # フォールバック: コマンドラインのyt-dlpを使用
                        cmd = [
                            "yt-dlp",
                            "--no-check-certificates",
                            "-f", "best",
                            "-o", output_template,
                            video_url
                        ]
                        subprocess.run(
                            cmd,
                            check=True,
                            capture_output=True,
                            encoding='utf-8',
                            errors='replace'
                        )

                    # ダウンロードしたファイルを探す
                    downloaded_file = None
                    if filename:
                        for ext in ['mp4', 'webm', 'mkv', 'm4a']:
                            filepath = self.output_dir / f"{filename}.{ext}"
                            if filepath.exists():
                                downloaded_file = str(filepath)
                                break
                    else:
                        # 最新の動画ファイルを取得
                        video_files = []
                        for ext in ['mp4', 'webm', 'mkv', 'm4a']:
                            video_files.extend(self.output_dir.glob(f"*.{ext}"))
                        if video_files:
                            files = sorted(video_files, key=os.path.getmtime)
                            downloaded_file = str(files[-1])

                    if not downloaded_file:
                        print(f"[ERROR] 動画 {i} のダウンロードファイルが見つかりません")
                        continue

                    # UTAGE動画でkeep_videoフラグが立っている場合、MP4に変換
                    if self.keep_video and downloaded_file:
                        print(f"[INFO] UTAGE動画 {i} をMP4形式に変換中...")
                        from audio_converter import AudioConverter
                        converter = AudioConverter()

                        # MP4ファイル名を生成
                        downloaded_path = Path(downloaded_file)
                        mp4_file = str(downloaded_path.parent / f"{downloaded_path.stem}_converted.mp4")

                        # MP4に変換
                        converted_file = converter.convert_to_mp4(downloaded_file, mp4_file)
                        if converted_file:
                            # 元のファイルを削除（変換後のMP4を保持）
                            try:
                                os.remove(downloaded_file)
                                print(f"[OK] 元のファイルを削除: {downloaded_file}")
                            except:
                                pass
                            downloaded_files.append(converted_file)
                            print(f"[OK] 動画 {i} ダウンロード完了: {converted_file}")
                        else:
                            print("[WARNING] MP4変換に失敗、元のファイルを使用します")
                            downloaded_files.append(downloaded_file)
                            print(f"[OK] 動画 {i} ダウンロード完了: {downloaded_file}")
                    elif downloaded_file:
                        downloaded_files.append(downloaded_file)
                        print(f"[OK] 動画 {i} ダウンロード完了: {downloaded_file}")

                except Exception as e:
                    print(f"[ERROR] 動画 {i} のダウンロードエラー: {e}")
                    continue

            print(f"\n[INFO] 合計 {len(downloaded_files)} 個の動画をダウンロードしました")
            return downloaded_files

        else:
            # UTAGE以外の場合は単一ダウンロード
            print("[INFO] 複数動画対応はUTAGEページのみです。単一ダウンロードを実行します")
            result = self.download(url, output_filename_base)
            if result:
                downloaded_files.append(result)
            return downloaded_files

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
