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
from voicy_extractor import VoicyExtractor
from standfm_extractor import StandfmExtractor

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
        self.voicy_extractor = VoicyExtractor()
        self.standfm_extractor = StandfmExtractor()
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
            # Voicyの場合、専用エクストラクタで音声URLを取得
            if self.voicy_extractor.is_voicy_url(url):
                print(f"[INFO] Voicyページを検出: {url}")
                self.is_utage_video = False
                return self._download_voicy(url, output_filename)

            # stand.fmの場合、専用エクストラクタで音声URLを取得
            if self.standfm_extractor.is_standfm_url(url):
                print(f"[INFO] stand.fmページを検出: {url}")
                self.is_utage_video = False
                return self._download_standfm(url, output_filename)

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
                    'nocheckcertificate': False,
                    'quiet': False,
                    'no_warnings': False,
                    'progress_hooks': [self._progress_hook],
                    'socket_timeout': 30,
                    'noplaylist': True,
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])

            except ImportError:
                # フォールバック: コマンドラインのyt-dlpを使用
                cmd = [
                    "yt-dlp",
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
                for ext in ['mp4', 'webm', 'mkv', 'm4a', 'mp3', 'opus', 'ogg']:
                    filepath = self.output_dir / f"{output_filename}.{ext}"
                    if filepath.exists():
                        print(f"[OK] ダウンロード完了: {filepath}")
                        downloaded_file = str(filepath)
                        break
            else:
                # 最新の動画ファイルを取得（ログファイルを除外）
                video_files = []
                for ext in ['mp4', 'webm', 'mkv', 'm4a', 'mp3', 'opus', 'ogg']:
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

    def _download_voicy(self, url: str, output_filename: Optional[str] = None) -> Optional[str]:
        """
        Voicy音声をダウンロード

        Args:
            url: VoicyのURL
            output_filename: 出力ファイル名（拡張子なし）

        Returns:
            ダウンロードしたファイルのパス、失敗時はNone
        """
        try:
            result = self.voicy_extractor.extract_audio_info(url)
            if not result:
                print("[ERROR] Voicy音声URLの取得に失敗")
                return None

            audio_url = result['url']

            if output_filename:
                safe_name = output_filename
            else:
                safe_name = re.sub(r'[\\/:*?"<>|]', '_', result.get('title', 'voicy_audio'))

            print(f"[INFO] Voicy音声をダウンロード中: {audio_url[:100]}...")

            # HLS(.m3u8)の場合はffmpegでMP3に直接変換
            if '.m3u8' in audio_url:
                output_path = self.output_dir / f"{safe_name}.mp3"
                return self._download_hls_to_mp3(audio_url, str(output_path))
            else:
                # 通常のファイルダウンロード
                ext = result.get('ext', 'mp3')
                output_path = self.output_dir / f"{safe_name}.{ext}"

                import requests
                response = requests.get(audio_url, stream=True, timeout=60, headers={
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                })
                response.raise_for_status()

                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0

                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"[PROGRESS] ダウンロード: {percent:.1f}%", flush=True)

                file_size = output_path.stat().st_size / (1024 * 1024)
                print(f"[OK] ダウンロード完了: {output_path} ({file_size:.2f} MB)")
                return str(output_path)

        except Exception as e:
            print(f"[ERROR] Voicyダウンロードエラー: {e}")
            return None

    def _download_hls_to_mp3(self, m3u8_url: str, output_path: str) -> Optional[str]:
        """HLS(.m3u8)をffmpegでMP3に変換してダウンロード"""
        try:
            ffmpeg_path = os.environ.get('FFMPEG_BINARY', 'ffmpeg')
            if ffmpeg_path and not os.path.isfile(ffmpeg_path):
                ffmpeg_path = 'ffmpeg'

            cmd = [
                ffmpeg_path,
                "-i", m3u8_url,
                "-acodec", "libmp3lame",
                "-b:a", "192k",
                "-y",
                output_path
            ]

            print("[INFO] HLS音声をMP3に変換中...", flush=True)
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                encoding='utf-8',
                errors='replace',
                timeout=300,
            )

            output = Path(output_path)
            if output.exists():
                file_size = output.stat().st_size / (1024 * 1024)
                print(f"[OK] ダウンロード・変換完了: {output_path} ({file_size:.2f} MB)")
                return output_path

            print("[ERROR] 出力ファイルが生成されませんでした")
            return None

        except subprocess.CalledProcessError as e:
            print(f"[ERROR] HLS変換エラー: {e}")
            if e.stderr:
                print(f"stderr: {e.stderr[:500]}")
            return None
        except Exception as e:
            print(f"[ERROR] HLS変換エラー: {e}")
            return None

    def _download_standfm(self, url: str, output_filename: Optional[str] = None) -> Optional[str]:
        """
        stand.fm音声をダウンロード

        Args:
            url: stand.fmのURL
            output_filename: 出力ファイル名（拡張子なし）

        Returns:
            ダウンロードしたファイルのパス、失敗時はNone
        """
        try:
            result = self.standfm_extractor.extract_audio_info(url)
            if not result:
                print("[ERROR] stand.fm音声URLの取得に失敗")
                return None

            audio_url = result['url']

            if output_filename:
                safe_name = output_filename
            else:
                safe_name = re.sub(r'[\\/:*?"<>|]', '_', result.get('title', 'standfm_audio'))

            ext = result.get('ext', 'm4a')
            print(f"[INFO] stand.fm音声をダウンロード中: {audio_url[:100]}...")

            # HLS(.m3u8)の場合はffmpegでMP3に変換
            if '.m3u8' in audio_url:
                output_path = self.output_dir / f"{safe_name}.mp3"
                return self._download_hls_to_mp3(audio_url, str(output_path))

            # M4Aを直接ダウンロード
            output_path = self.output_dir / f"{safe_name}.{ext}"

            import requests
            response = requests.get(audio_url, stream=True, timeout=60, headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            })
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0 and downloaded % (8192 * 100) == 0:
                        percent = (downloaded / total_size) * 100
                        print(f"\r[PROGRESS] ダウンロード: {percent:.1f}%", end="", flush=True)

            if total_size > 0:
                print()  # 改行

            file_size = output_path.stat().st_size / (1024 * 1024)
            print(f"[OK] ダウンロード完了: {output_path} ({file_size:.2f} MB)")

            # M4AをMP3に変換
            mp3_path = self.output_dir / f"{safe_name}.mp3"
            return self._convert_m4a_to_mp3(str(output_path), str(mp3_path))

        except Exception as e:
            print(f"[ERROR] stand.fmダウンロードエラー: {e}")
            return None

    def _convert_m4a_to_mp3(self, input_path: str, output_path: str) -> Optional[str]:
        """M4AをMP3に変換"""
        try:
            ffmpeg_path = os.environ.get('FFMPEG_BINARY', 'ffmpeg')
            if ffmpeg_path and not os.path.isfile(ffmpeg_path):
                ffmpeg_path = 'ffmpeg'

            cmd = [
                ffmpeg_path,
                "-i", input_path,
                "-acodec", "libmp3lame",
                "-b:a", "192k",
                "-y",
                output_path
            ]

            print("[INFO] M4AをMP3に変換中...", flush=True)
            subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                encoding='utf-8',
                errors='replace',
                timeout=300,
            )

            output = Path(output_path)
            if output.exists():
                # 元のM4Aを削除
                try:
                    os.remove(input_path)
                except Exception:
                    pass
                file_size = output.stat().st_size / (1024 * 1024)
                print(f"[OK] 変換完了: {output_path} ({file_size:.2f} MB)")
                return output_path

            print("[ERROR] MP3ファイルが生成されませんでした")
            return input_path  # 変換失敗時はM4Aを返す

        except Exception as e:
            print(f"[WARNING] MP3変換失敗、M4Aのまま使用: {e}")
            return input_path

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
                            'nocheckcertificate': False,
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
                        for ext in ['mp4', 'webm', 'mkv', 'm4a', 'mp3', 'opus', 'ogg']:
                            filepath = self.output_dir / f"{filename}.{ext}"
                            if filepath.exists():
                                downloaded_file = str(filepath)
                                break
                    else:
                        # 最新の動画ファイルを取得
                        video_files = []
                        for ext in ['mp4', 'webm', 'mkv', 'm4a', 'mp3', 'opus', 'ogg']:
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
        # stand.fm URLの場合は専用エクストラクタから情報取得
        if self.standfm_extractor.is_standfm_url(url):
            return self.standfm_extractor.get_video_info(url)

        # Voicy URLの場合はAPIから情報取得
        if self.voicy_extractor.is_voicy_url(url):
            channel_info = self.voicy_extractor._api_get(
                f"/channel/{self.voicy_extractor._parse_url(url)['channel_id']}"
            )
            if channel_info:
                return {
                    'title': channel_info.get('name', 'Voicy'),
                    'uploader': channel_info.get('personality', {}).get('name', ''),
                    'id': channel_info.get('id', ''),
                }
            return None

        try:
            import yt_dlp
            import concurrent.futures

            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'nocheckcertificate': False,
                'socket_timeout': 15,
                'noplaylist': True,
            }

            def _extract():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(url, download=False)

            # タイムアウト付きで実行（30秒）
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_extract)
                info = future.result(timeout=30)
                return info

        except concurrent.futures.TimeoutError:
            print(f"[WARNING] 情報取得タイムアウト（30秒）: {url}", flush=True)
            return None
        except Exception as e:
            print(f"[ERROR] 情報取得エラー: {e}", flush=True)
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
