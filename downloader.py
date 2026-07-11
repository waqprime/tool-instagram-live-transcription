#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
動画・音声ダウンローダー
yt-dlpを使用して各種プラットフォームから動画・音声をダウンロード
対応: Instagram, YouTube, X Spaces, Voicy, Radiko, stand.fm, Spotify Podcast, UTAGE等（yt-dlp対応サイト全て）
"""

import os
import re
import sys
import time
import subprocess
from pathlib import Path
from typing import Optional, Dict, List
from utage_extractor import UtageExtractor
from voicy_extractor import VoicyExtractor
from standfm_extractor import StandfmExtractor
from spotify_extractor import SpotifyExtractor

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

# バンドルされたdenoをPATHに追加（yt-dlpのYouTube JS解析に必要）
_deno_dir = os.environ.get('DENO_DIR_PATH', '')
if _deno_dir and os.path.isdir(_deno_dir):
    _current_path = os.environ.get('PATH', '')
    if _deno_dir not in _current_path:
        os.environ['PATH'] = _deno_dir + os.pathsep + _current_path
        print(f"denoパスを設定: {_deno_dir}", flush=True)


class VideoDownloader:
    """各種プラットフォームから動画・音声をダウンロードするクラス

    yt-dlpを使用して、Instagram, YouTube, X Spaces, Voicy, UTAGE等、
    1,800以上のサイトから動画・音声をダウンロード
    """

    def __init__(
        self,
        output_dir: str = "output",
        keep_video: bool = False,
        cookies_from_browser: Optional[str] = None,
    ):
        """
        Args:
            output_dir: 出力ディレクトリ
            keep_video: 動画ファイルを保持するかどうか（UTAGE動画のMP4変換に使用）
            cookies_from_browser: Cookieを取得するブラウザ名（chrome/edge/firefox等）
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.utage_extractor = UtageExtractor()
        self.voicy_extractor = VoicyExtractor()
        self.standfm_extractor = StandfmExtractor()
        self.spotify_extractor = SpotifyExtractor()
        self.keep_video = keep_video
        self.cookies_from_browser = cookies_from_browser
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

    def _apply_cookies(self, ydl_opts: dict) -> dict:
        """yt-dlpオプションにブラウザCookie設定と共通設定を適用"""
        if self.cookies_from_browser:
            ydl_opts['cookiesfrombrowser'] = (self.cookies_from_browser,)
        # YouTubeのn-challenge解決にyt-dlp-ejsソルバースクリプトの取得を許可。
        # 同梱denoをJSランタイムとして使い、画像のみ/フォーマット取得失敗を回避する。
        # （非YouTubeサイトでは未使用なので無害。GitHubからの取得には通信が必要）
        ydl_opts.setdefault('remote_components', ['ejs:github'])
        return ydl_opts

    def _login_required_hint(self, url: str, error: Exception) -> Optional[str]:
        """
        ログイン/Cookieが必要なことに起因するエラーかを判定し、
        該当する場合はユーザー向けの案内メッセージを返す（非該当時はNone）。
        """
        msg = str(error).lower()
        needs_login = (
            'empty media response' in msg
            or 'login' in msg
            or 'cookies' in msg
            or 'rate-limit' in msg
            or 'requested content is not available' in msg
        )
        if not needs_login:
            return None
        # 既にCookieブラウザが指定済みの場合は、非公開/未ログインの可能性を案内
        if self.cookies_from_browser:
            return (
                "この投稿はログインが必要か、選択中のブラウザがログイン状態でない可能性があります。"
                "対象アカウントでブラウザにログイン済みか確認し、非公開投稿はダウンロードできない点にご注意ください。"
            )
        service = "このサイト"
        if 'instagram.com' in url:
            service = "Instagram"
        elif 'facebook.com' in url:
            service = "Facebook"
        elif 'twitter.com' in url or 'x.com' in url:
            service = "X (Twitter)"
        return (
            f"{service}はログインが必要です。アプリ設定の「Cookieブラウザ」で"
            "ログイン済みのブラウザ（Chrome等）を選択してから、もう一度お試しください。"
        )

    # ダウンロード後に探す拡張子（yt-dlpが選択しうる代表的なコンテナ/コーデック）
    KNOWN_MEDIA_EXTENSIONS = [
        'mp4', 'webm', 'mkv', 'm4a', 'mp3', 'opus', 'ogg',
        'ts', 'flv', '3gp', 'aac', 'wav', 'mov', 'avi',
    ]

    def _find_downloaded_file(self, filename: Optional[str], start_time: float) -> Optional[str]:
        """
        ダウンロードしたファイルを探す。

        既知の拡張子リストで見つからない場合は、フォールバックとして
        output_dir内で処理開始（start_time）以降に更新された、
        一時ファイル(.part/.ytdl/.tmp)・出力物(.txt/.json/.md)以外の
        最新ファイルを採用する（未知の拡張子で保存されたケースに対応）。
        """
        if filename:
            for ext in self.KNOWN_MEDIA_EXTENSIONS:
                filepath = self.output_dir / f"{filename}.{ext}"
                if filepath.exists():
                    return str(filepath)
        else:
            media_files = []
            for ext in self.KNOWN_MEDIA_EXTENSIONS:
                media_files.extend(self.output_dir.glob(f"*.{ext}"))
            if media_files:
                files = sorted(media_files, key=os.path.getmtime)
                return str(files[-1])

        excluded_suffixes = {'.part', '.ytdl', '.tmp', '.txt', '.json', '.md'}
        candidates = []
        for entry in self.output_dir.iterdir():
            if not entry.is_file() or entry.suffix.lower() in excluded_suffixes:
                continue
            try:
                mtime = entry.stat().st_mtime
            except OSError:
                continue
            if mtime >= start_time:
                candidates.append((mtime, entry))

        if candidates:
            candidates.sort(key=lambda x: x[0])
            fallback_path = candidates[-1][1]
            print(f"[WARNING] 既知の拡張子で見つからないため、更新日時から最新ファイルを採用: {fallback_path}", flush=True)
            return str(fallback_path)

        return None

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

            # Spotify Podcastの場合、RSSフィード経由で音声を取得
            if self.spotify_extractor.is_spotify_url(url):
                print(f"[INFO] Spotify Podcastを検出: {url}")
                self.is_utage_video = False
                return self._download_spotify(url, output_filename)

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
            download_start_time = time.time()

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
                    'retries': 10,
                    'fragment_retries': 10,
                    'file_access_retries': 3,
                    'extractor_retries': 3,
                }
                self._apply_cookies(ydl_opts)

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])

            except ImportError:
                # フォールバック: コマンドラインのyt-dlpを使用
                cmd = [
                    "yt-dlp",
                    "-f", "best",
                    "--remote-components", "ejs:github",
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
            downloaded_file = self._find_downloaded_file(output_filename, download_start_time)
            if downloaded_file:
                print(f"[OK] ダウンロード完了: {downloaded_file}")

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
            hint = self._login_required_hint(url, e)
            if hint:
                print(f"[HINT] {hint}", flush=True)
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
                "-protocol_whitelist", "file,crypto,data,http,https,tcp,tls,httpproxy",
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

            # M4Aを直接ダウンロード（Session共有・リトライ付き）
            output_path = self.output_dir / f"{safe_name}.{ext}"

            import requests
            import time
            session = self.standfm_extractor._session
            max_retries = 3
            response = None
            for attempt in range(1, max_retries + 1):
                try:
                    response = session.get(audio_url, stream=True, timeout=60)
                    if response.status_code == 429:
                        delay = int(response.headers.get('Retry-After', 5 * attempt))
                        print(f"[WARNING] レート制限 (429)。{delay}秒後にリトライ ({attempt}/{max_retries})", flush=True)
                        time.sleep(delay)
                        continue
                    response.raise_for_status()
                    break
                except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                    delay = 5 * attempt
                    print(f"[WARNING] 接続エラー。{delay}秒後にリトライ ({attempt}/{max_retries}): {e}", flush=True)
                    time.sleep(delay)
                    if attempt == max_retries:
                        raise
            if response is None or response.status_code != 200:
                raise Exception(f"音声ダウンロードに失敗しました (status={response.status_code if response else 'None'})")

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

    def _download_spotify(self, url: str, output_filename: Optional[str] = None) -> Optional[str]:
        """
        Spotify PodcastをRSSフィード経由でダウンロード

        Args:
            url: SpotifyのPodcast URL
            output_filename: 出力ファイル名（拡張子なし）

        Returns:
            ダウンロードしたファイルのパス、失敗時はNone
        """
        try:
            result = self.spotify_extractor.extract_audio_info(url)
            if not result:
                print("[ERROR] Spotify Podcast音声URLの取得に失敗")
                return None

            audio_url = result['url']

            if output_filename:
                safe_name = output_filename
            else:
                safe_name = re.sub(r'[\\/:*?"<>|]', '_', result.get('title', 'spotify_podcast'))

            ext = result.get('ext', 'mp3')
            print(f"[INFO] Podcast音声をダウンロード中: {audio_url[:100]}...")

            # 音声を直接ダウンロード
            output_path = self.output_dir / f"{safe_name}.{ext}"

            import requests
            response = self.spotify_extractor._session.get(audio_url, stream=True, timeout=120)
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

            # MP3以外の場合はMP3に変換
            if ext != 'mp3':
                mp3_path = self.output_dir / f"{safe_name}.mp3"
                return self._convert_m4a_to_mp3(str(output_path), str(mp3_path))

            return str(output_path)

        except Exception as e:
            print(f"[ERROR] Spotify Podcastダウンロードエラー: {e}")
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
                    download_start_time = time.time()
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
                            'retries': 10,
                            'fragment_retries': 10,
                            'file_access_retries': 3,
                            'extractor_retries': 3,
                        }
                        self._apply_cookies(ydl_opts)

                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            ydl.download([video_url])

                    except ImportError:
                        # フォールバック: コマンドラインのyt-dlpを使用
                        cmd = [
                            "yt-dlp",
                            "-f", "best",
                            "--remote-components", "ejs:github",
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
                    downloaded_file = self._find_downloaded_file(filename, download_start_time)

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

        # Spotify Podcast URLの場合はRSSフィード経由で情報取得
        if self.spotify_extractor.is_spotify_url(url):
            return self.spotify_extractor.get_video_info(url)

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
            self._apply_cookies(ydl_opts)

            def _extract():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(url, download=False)

            # タイムアウト付きで実行（30秒）
            # with文だとexit時にshutdown(wait=True)されタイムアウト後もバックグラウンドスレッドの完了を待ってしまうため、
            # 明示的にshutdown(wait=False)して即座に戻す
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            try:
                future = executor.submit(_extract)
                info = future.result(timeout=30)
                return info
            finally:
                executor.shutdown(wait=False)

        except concurrent.futures.TimeoutError:
            print(f"[WARNING] 情報取得タイムアウト（30秒）: {url}", flush=True)
            return None
        except Exception as e:
            print(f"[ERROR] 情報取得エラー: {e}", flush=True)
            hint = self._login_required_hint(url, e)
            if hint:
                print(f"[HINT] {hint}", flush=True)
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
