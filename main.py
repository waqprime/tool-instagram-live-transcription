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
import platform

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
from title_generator import TitleGenerator
from obsidian_writer import ObsidianWriter
from summarizer import ContentSummarizer, DEFAULT_SUMMARY_PROMPT


def get_default_output_dir() -> str:
    """
    OSごとのデフォルト出力ディレクトリを取得

    Returns:
        デフォルト出力ディレクトリのパス
    """
    system = platform.system()
    home = Path.home()

    if system == "Darwin":  # macOS
        return str(home / "Downloads" / "InstagramTranscripts")
    elif system == "Windows":
        # Windowsはダウンロードフォルダを優先
        downloads = home / "Downloads" / "InstagramTranscripts"
        if downloads.parent.exists():
            return str(downloads)
        # ダウンロードフォルダがない場合はデスクトップ
        desktop = home / "Desktop" / "InstagramTranscripts"
        return str(desktop)
    else:  # Linux等
        return str(home / "Downloads" / "InstagramTranscripts")


class AudioTranscriptionProcessor:
    """各種プラットフォームの動画・音声を処理するメインクラス

    Instagram, YouTube, X Spaces, Voicy等、yt-dlp対応サイトから
    動画・音声をダウンロードし、MP3抽出と文字起こしを実行
    """

    def __init__(
        self,
        output_dir: Optional[str] = None,
        whisper_model: str = "base",
        language: str = "ja",
        keep_video: bool = False,
        engine: str = "faster-whisper",
        api_key: Optional[str] = None,
        diarize: bool = False,
        obsidian_vault: Optional[str] = None,
        obsidian_folder: str = "",
        summarize: bool = False,
        summary_prompt: Optional[str] = None,
        summary_provider: str = "openai",
        ollama_url: Optional[str] = None,
        summary_model: Optional[str] = None,
    ):
        """
        Args:
            output_dir: 出力ディレクトリ（Noneの場合はOSごとのデフォルト）
            whisper_model: Whisperモデル名
            language: 言語コード
            keep_video: 動画ファイルを保持するかどうか
            engine: 文字起こしエンジン (faster-whisper / openai-api / local-whisper)
            api_key: OpenAI APIキー (openai-api エンジン用)
            diarize: 話者分離を実行するかどうか
            obsidian_vault: Obsidian Vaultのルートパス
            obsidian_folder: Vault内のサブフォルダパス
            summarize: 内容要約を実行するかどうか
            summary_prompt: 要約プロンプト（カスタム）
            summary_provider: 要約プロバイダ ("openai" or "ollama")
            ollama_url: OllamaのAPIエンドポイント
            summary_model: 要約に使用するモデル名
        """
        # output_dirが指定されていない場合はOSごとのデフォルトを使用
        if output_dir is None:
            output_dir = get_default_output_dir()

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.keep_video = keep_video
        self.diarize = diarize
        self.api_key = api_key

        print("=" * 60)
        print("音声文字起こしシステム")
        print(f"エンジン: {engine}")
        if diarize:
            print("話者分離: 有効")
        if summarize:
            print("内容要約: 有効")
        if obsidian_vault:
            print(f"Obsidian Vault: {obsidian_vault}")
        print("対応: Instagram, YouTube, X Spaces, Voicy等")
        print("=" * 60)

        # 各コンポーネントを初期化
        self.downloader = VideoDownloader(str(self.output_dir), keep_video=keep_video)
        self.converter = AudioConverter()
        self.transcriber = AudioTranscriber(whisper_model, language, engine=engine, api_key=api_key)
        self.title_generator = TitleGenerator(api_key=api_key)

        # 話者分離（オプション）
        self.diarizer = None
        if diarize:
            try:
                from diarizer import SpeakerDiarizer
                self.diarizer = SpeakerDiarizer()
            except ImportError:
                print("[WARNING] 話者分離モジュール (diarizer) が見つかりません。話者分離をスキップします。", flush=True)

        # Obsidian（オプション）
        self.obsidian_writer = None
        if obsidian_vault:
            self.obsidian_writer = ObsidianWriter(obsidian_vault, obsidian_folder)

        # 内容要約（オプション）
        self.summarizer = None
        if summarize:
            if summary_provider == "ollama" or api_key:
                self.summarizer = ContentSummarizer(
                    provider=summary_provider,
                    api_key=api_key,
                    prompt=summary_prompt,
                    ollama_url=ollama_url,
                    summary_model=summary_model,
                )

    def process_file(self, file_path: str) -> bool:
        """
        ローカルファイル（動画・音声）を処理

        Args:
            file_path: ローカルの動画・音声ファイルのパス（MP4, MP3, M4A, WAV, WebM, MKV, MOV）

        Returns:
            成功した場合True
        """
        print(f"\n{'=' * 60}")
        print(f"ファイル処理開始: {file_path}")
        print(f"{'=' * 60}\n")

        file_path_obj = Path(file_path)

        # ファイルの存在確認
        if not file_path_obj.exists():
            print(f"[ERROR] ファイルが見つかりません: {file_path}")
            return False

        # ファイル拡張子の確認
        file_ext = file_path_obj.suffix.lower()
        if file_ext not in ['.mp4', '.mp3', '.m4a', '.wav', '.webm', '.mkv', '.mov']:
            print(f"[ERROR] サポートされていないファイル形式: {file_ext}")
            print("[INFO] 対応形式: .mp4, .mp3, .m4a, .wav, .webm, .mkv, .mov")
            return False

        # MP3ファイルの場合はそのまま文字起こし
        if file_ext == '.mp3':
            print("【ステップ1/2】MP3ファイルを検出")
            mp3_file = str(file_path_obj)

            # 出力ディレクトリにコピー
            output_mp3 = self.output_dir / file_path_obj.name
            if str(file_path_obj) != str(output_mp3):
                import shutil
                shutil.copy2(file_path_obj, output_mp3)
                mp3_file = str(output_mp3)
                print(f"[OK] MP3をコピー: {output_mp3}")

            # ステップ2: 文字起こし
            print(f"\n【ステップ2/2】文字起こし")
            result = self.transcriber.transcribe(mp3_file, str(self.output_dir))
            if not result:
                print("[ERROR] 文字起こし失敗")
                return False

            # 話者分離（オプション）
            if self.diarizer and result:
                result = self._apply_diarization(mp3_file, result)

            # タイトル生成（GPT、ローカルファイル用）
            title = self.title_generator.generate_title_from_text(result.get('text', ''))

            # 内容要約（オプション）
            self._apply_summarization(mp3_file, result)

            # Obsidian保存（オプション）
            if self.obsidian_writer and result:
                note_title = title or file_path_obj.stem
                self.obsidian_writer.save_note(
                    title=note_title,
                    text=result.get('text', ''),
                    segments=result.get('segments'),
                )

            print(f"\n[OK] 処理完了!")
            print(f"MP3ファイル: {mp3_file}")
            print(f"文字起こし: {Path(mp3_file).stem}_transcript.txt")
            return True

        # MP4等の動画ファイルの場合は音声抽出してから文字起こし
        else:
            print(f"【ステップ1/3】{file_ext}ファイルを検出")

            # 出力ディレクトリにコピー
            output_video = self.output_dir / file_path_obj.name
            if str(file_path_obj) != str(output_video):
                import shutil
                shutil.copy2(file_path_obj, output_video)
                video_file = str(output_video)
                print(f"[OK] 動画ファイルをコピー: {output_video}")
            else:
                video_file = str(file_path_obj)

            # ステップ2: 音声をMP3に変換
            print(f"\n【ステップ2/3】音声抽出")
            mp3_file = self.converter.extract_audio(video_file)
            if not mp3_file:
                print("[ERROR] 音声抽出失敗")
                return False

            # 動画ファイルの処理（保持 or 削除）
            if self.keep_video:
                print(f"[OK] 動画ファイルを保持: {video_file}")
            else:
                try:
                    if video_file != str(file_path_obj):  # コピーした場合のみ削除
                        os.remove(video_file)
                        print(f"[OK] 元の動画ファイルを削除: {video_file}")
                except Exception as e:
                    print(f"[WARNING] 動画ファイル削除時の警告: {e}")

            # ステップ3: 文字起こし
            print(f"\n【ステップ3/3】文字起こし")
            result = self.transcriber.transcribe(mp3_file, str(self.output_dir))
            if not result:
                print("[ERROR] 文字起こし失敗")
                return False

            # 話者分離（オプション）
            if self.diarizer and result:
                result = self._apply_diarization(mp3_file, result)

            # タイトル生成（GPT、ローカルファイル用）
            title = self.title_generator.generate_title_from_text(result.get('text', ''))

            # 内容要約（オプション）
            self._apply_summarization(mp3_file, result)

            # Obsidian保存（オプション）
            if self.obsidian_writer and result:
                note_title = title or file_path_obj.stem
                self.obsidian_writer.save_note(
                    title=note_title,
                    text=result.get('text', ''),
                    segments=result.get('segments'),
                )

            print(f"\n[OK] 処理完了!")
            print(f"MP3ファイル: {mp3_file}")
            print(f"文字起こし: {Path(mp3_file).stem}_transcript.txt")
            return True

    def process_url(self, url: str, filename_prefix: Optional[str] = None, process_all: bool = False) -> bool:
        """
        単一のURLを処理（複数動画対応）

        Args:
            url: 動画・音声のURL（Instagram, YouTube, X Spaces, Voicy等）
            filename_prefix: ファイル名のプレフィックス
            process_all: UTAGEページで複数動画がある場合、全てを処理するか

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

        # UTAGEページで複数動画がある場合の処理
        if process_all and self.downloader.utage_extractor.is_utage_url(url):
            return self._process_multiple_videos(url, filename_prefix)

        # タイトル取得（yt-dlpメタデータ）
        title = None
        try:
            print("タイトル取得中...", flush=True)
            title = self.title_generator.get_title_from_url(url, self.downloader)
        except Exception as e:
            print(f"[WARNING] タイトル取得失敗（処理は続行）: {e}", flush=True)

        # ステップ1: 動画をダウンロード
        print("【ステップ1/3】動画ダウンロード", flush=True)
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

        # 動画ファイルの処理（保持 or 削除）
        if self.keep_video:
            print(f"[OK] 動画ファイルを保持: {video_file}")
        else:
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

        # 話者分離（オプション）
        if self.diarizer and result:
            result = self._apply_diarization(mp3_file, result)

        # 内容要約（オプション）
        self._apply_summarization(mp3_file, result)

        # Obsidian保存（オプション）
        if self.obsidian_writer and result:
            note_title = title or filename_prefix or Path(mp3_file).stem
            source = self._detect_source(url)
            self.obsidian_writer.save_note(
                title=note_title,
                text=result.get('text', ''),
                segments=result.get('segments'),
                url=url,
                source=source,
            )

        print(f"\n{'=' * 60}")
        print("[OK] 処理完了!")
        print(f"{'=' * 60}")
        print(f"MP3ファイル: {mp3_file}")
        print(f"文字起こし: {Path(mp3_file).stem}_transcript.txt")
        print(f"詳細情報: {Path(mp3_file).stem}_transcript.json")

        return True

    def _apply_summarization(self, mp3_file: str, result: dict) -> Optional[str]:
        """
        要約を実行しファイルに保存

        Args:
            mp3_file: 音声ファイルパス（ファイル名生成用）
            result: 文字起こし結果

        Returns:
            要約テキスト、失敗時はNone
        """
        if not self.summarizer:
            return None

        text = result.get('text', '')
        if not text:
            return None

        try:
            print("\n【追加ステップ】内容要約")
            summary = self.summarizer.summarize(text)
            if summary:
                base_name = Path(mp3_file).stem
                summary_file = self.output_dir / f"{base_name}_summary.txt"
                self.summarizer.save_summary(summary, str(summary_file))
                return summary
        except Exception as e:
            print(f"[WARNING] 内容要約失敗（処理は続行）: {e}", flush=True)

        return None

    def _apply_diarization(self, mp3_file: str, result: dict) -> dict:
        """
        話者分離を実行し、結果をマージ。detailedファイルを再保存する。

        Args:
            mp3_file: 音声ファイルパス
            result: 文字起こし結果

        Returns:
            話者情報が付与された結果辞書
        """
        try:
            print("\n【追加ステップ】話者分離")
            diarization_segments = self.diarizer.diarize(mp3_file)
            if diarization_segments:
                merged_segments = self.diarizer.merge_with_transcription(
                    result['segments'], diarization_segments
                )
                result['segments'] = merged_segments

                # detailed テキストを再保存（speaker付き）
                from transcriber import TranscriberBase
                base_name = Path(mp3_file).stem
                detailed_file = self.output_dir / f"{base_name}_transcript_detailed.txt"
                with open(detailed_file, 'w', encoding='utf-8') as f:
                    for seg in merged_segments:
                        start = TranscriberBase._format_timestamp(seg['start'])
                        end = TranscriberBase._format_timestamp(seg['end'])
                        text = seg['text'].strip()
                        speaker = seg.get('speaker', '')
                        if speaker:
                            f.write(f"[{start} -> {end}] [{speaker}] {text}\n")
                        else:
                            f.write(f"[{start} -> {end}] {text}\n")
                print(f"[OK] 話者情報付きdetailedテキスト再保存: {detailed_file}")
        except Exception as e:
            print(f"[WARNING] 話者分離失敗（処理は続行）: {e}")

        return result

    def _detect_source(self, url: str) -> str:
        """
        URLからソースプラットフォームを検出

        Args:
            url: 動画・音声のURL

        Returns:
            ソース名（例: "YouTube", "Instagram"）
        """
        url_lower = url.lower()
        if 'instagram.com' in url_lower:
            return 'Instagram'
        elif 'youtube.com' in url_lower or 'youtu.be' in url_lower:
            return 'YouTube'
        elif 'twitter.com' in url_lower or 'x.com' in url_lower:
            return 'X (Twitter)'
        elif 'voicy.jp' in url_lower:
            return 'Voicy'
        elif 'radiko.jp' in url_lower:
            return 'Radiko'
        elif 'stand.fm' in url_lower:
            return 'stand.fm'
        elif 'utage' in url_lower:
            return 'UTAGE'
        elif 'tiktok.com' in url_lower:
            return 'TikTok'
        elif 'nicovideo.jp' in url_lower or 'nico.ms' in url_lower:
            return 'niconico'
        else:
            return 'Web'

    def _process_multiple_videos(self, url: str, filename_prefix: str) -> bool:
        """
        複数動画があるページを処理（UTAGEページ用）

        Args:
            url: UTAGEページのURL
            filename_prefix: ファイル名のプレフィックス

        Returns:
            全ての動画処理が成功した場合True
        """
        print(f"\n{'=' * 60}")
        print(f"複数動画の処理を開始")
        print(f"{'=' * 60}\n")

        # ステップ1: 全動画をダウンロード
        print("【ステップ1/3】全動画ダウンロード")
        video_files = self.downloader.download_multiple(url, filename_prefix)
        if not video_files:
            print("[ERROR] ダウンロード失敗")
            return False

        print(f"\n[INFO] {len(video_files)}個の動画をダウンロード完了")

        # 各動画を処理
        success_count = 0
        for i, video_file in enumerate(video_files, 1):
            print(f"\n{'=' * 60}")
            print(f"動画 {i}/{len(video_files)} の処理")
            print(f"{'=' * 60}\n")

            # ステップ2: 音声をMP3に変換
            print(f"【ステップ2/3】音声抽出 ({i}/{len(video_files)})")
            mp3_file = self.converter.extract_audio(video_file)
            if not mp3_file:
                print(f"[ERROR] 動画 {i} の音声抽出失敗")
                continue

            # 動画ファイルの処理（保持 or 削除）
            if self.keep_video:
                print(f"[OK] 動画ファイルを保持: {video_file}")
            else:
                try:
                    if video_file != mp3_file:
                        os.remove(video_file)
                        print(f"[OK] 元の動画ファイルを削除: {video_file}")
                except Exception as e:
                    print(f"[WARNING] 動画ファイル削除時の警告: {e}")

            # ステップ3: 音声を文字起こし
            print(f"\n【ステップ3/3】文字起こし ({i}/{len(video_files)})")
            result = self.transcriber.transcribe(mp3_file, str(self.output_dir))
            if not result:
                print(f"[ERROR] 動画 {i} の文字起こし失敗")
                continue

            # 内容要約（オプション）
            self._apply_summarization(mp3_file, result)

            print(f"\n[OK] 動画 {i} の処理完了!")
            print(f"MP3ファイル: {mp3_file}")
            print(f"文字起こし: {Path(mp3_file).stem}_transcript.txt")
            success_count += 1

        # 最終結果
        print(f"\n{'=' * 60}")
        print(f"全体の処理結果")
        print(f"{'=' * 60}")
        print(f"合計: {len(video_files)} 個")
        print(f"成功: {success_count} 個")
        print(f"失敗: {len(video_files) - success_count} 個")

        return success_count == len(video_files)

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

  # UTAGEページで複数動画を全て処理
  python main.py --url "https://example.utage-system.com/..." --all

  # ローカルファイルを処理（MP4/MP3）
  python main.py --local-file "/path/to/video.mp4"
  python main.py --local-file "/path/to/audio.mp3"

  # モデルとオプションを指定
  python main.py --model medium --language ja --output-dir ./results
        """
    )

    parser.add_argument(
        "-u", "--url",
        help="動画・音声のURL（Instagram, YouTube, X Spaces, Voicy等）"
    )
    parser.add_argument(
        "-lf", "--local-file",
        help="処理するローカルファイルのパス（MP4, MP3, M4A, WAV, WebM, MKV）"
    )
    parser.add_argument(
        "-f", "--file",
        default="link.txt",
        help="URLリストファイル（デフォルト: link.txt）"
    )
    parser.add_argument(
        "-e", "--engine",
        default="faster-whisper",
        choices=["faster-whisper", "openai-api", "local-whisper", "kotoba-whisper"],
        help="文字起こしエンジン（デフォルト: faster-whisper）"
    )
    parser.add_argument(
        "-m", "--model",
        default=None,
        help="Whisperモデル名（デフォルト: エンジンに依存。faster-whisper=large-v3-turbo, local-whisper=base）"
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="OpenAI APIキー（openai-api エンジン使用時に必要。環境変数 OPENAI_API_KEY でも指定可）"
    )
    parser.add_argument(
        "-l", "--language",
        default="ja",
        help="言語コード（デフォルト: ja）"
    )
    parser.add_argument(
        "-o", "--output-dir",
        default=None,
        help="出力ディレクトリ（デフォルト: macOSは~/Downloads/InstagramTranscripts, Windowsは~/Downloads/InstagramTranscripts または ~/Desktop/InstagramTranscripts）"
    )
    parser.add_argument(
        "-k", "--keep-video",
        action="store_true",
        help="動画ファイルを保持する（削除せずにMP4として保存）"
    )
    parser.add_argument(
        "-a", "--all",
        action="store_true",
        help="UTAGEページで複数動画がある場合、全てを処理する"
    )
    parser.add_argument(
        "--diarize",
        action="store_true",
        help="話者分離を実行する（SpeechBrain使用、追加APIキー不要）"
    )
    parser.add_argument(
        "--obsidian-vault",
        default=None,
        help="Obsidian Vaultのルートパス（指定すると文字起こし結果をMarkdownノートとして保存）"
    )
    parser.add_argument(
        "--obsidian-folder",
        default="",
        help="Obsidian Vault内のサブフォルダパス"
    )
    parser.add_argument(
        "--summarize",
        action="store_true",
        help="内容要約を実行する（OpenAI API または Ollama使用）"
    )
    parser.add_argument(
        "--summary-prompt",
        default=None,
        help="要約プロンプト（カスタム、省略時はデフォルトプロンプト使用）"
    )
    parser.add_argument(
        "--summary-provider",
        default="openai",
        choices=["openai", "ollama"],
        help="要約プロバイダ（デフォルト: openai）"
    )
    parser.add_argument(
        "--ollama-url",
        default=None,
        help="OllamaのAPIエンドポイント（デフォルト: http://localhost:11434/v1）"
    )
    parser.add_argument(
        "--summary-model",
        default=None,
        help="要約モデル名（openai: gpt-4o-mini, ollama: gemma3 がデフォルト）"
    )

    args = parser.parse_args()

    # プロセッサーを初期化
    processor = AudioTranscriptionProcessor(
        output_dir=args.output_dir,
        whisper_model=args.model,
        language=args.language,
        keep_video=args.keep_video,
        engine=args.engine,
        api_key=args.api_key,
        diarize=args.diarize,
        obsidian_vault=args.obsidian_vault,
        obsidian_folder=args.obsidian_folder,
        summarize=args.summarize,
        summary_prompt=args.summary_prompt,
        summary_provider=args.summary_provider,
        ollama_url=args.ollama_url,
        summary_model=args.summary_model,
    )

    # 単一URL処理、ローカルファイル処理、またはファイル一括処理
    if args.url:
        success = processor.process_url(args.url, process_all=args.all)
        return 0 if success else 1
    elif args.local_file:
        success = processor.process_file(args.local_file)
        return 0 if success else 1
    else:
        if not Path(args.file).exists():
            print(f"[ERROR] エラー: ファイルが見つかりません: {args.file}")
            print(f"使い方: python main.py --url <動画・音声URL> または python main.py --local-file <ファイルパス>")
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
