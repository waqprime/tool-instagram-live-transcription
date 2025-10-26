#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音声変換モジュール
動画ファイルからMP3音声を抽出
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional

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


class AudioConverter:
    """動画から音声を抽出してMP3に変換するクラス"""

    def __init__(self, ffmpeg_path: Optional[str] = None):
        """初期化

        Args:
            ffmpeg_path: ffmpegバイナリのパス（Noneの場合はシステムのffmpegを使用）
        """
        # ffmpegパスを環境変数または引数から取得
        self.ffmpeg_path = ffmpeg_path or os.environ.get('FFMPEG_BINARY', 'ffmpeg')
        self.ffprobe_path = os.environ.get('FFPROBE_BINARY', 'ffprobe')

        # バンドル版の場合、ffprobeもffmpegと同じディレクトリにあると仮定
        if ffmpeg_path and os.path.isfile(ffmpeg_path):
            ffmpeg_dir = os.path.dirname(ffmpeg_path)
            ffprobe_name = 'ffprobe.exe' if sys.platform == 'win32' else 'ffprobe'
            possible_ffprobe = os.path.join(ffmpeg_dir, ffprobe_name)
            if os.path.isfile(possible_ffprobe):
                self.ffprobe_path = possible_ffprobe

        self._check_ffmpeg()

    def _check_ffmpeg(self):
        """ffmpegがインストールされているか確認"""
        try:
            subprocess.run(
                [self.ffmpeg_path, "-version"],
                check=True,
                capture_output=True,
                encoding='utf-8',
                errors='replace'
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"[ERROR] エラー: ffmpegが見つかりません: {self.ffmpeg_path}")
            print("インストール方法:")
            print("  macOS: brew install ffmpeg")
            print("  Ubuntu: sudo apt install ffmpeg")
            print("  Windows: https://ffmpeg.org/download.html")
            sys.exit(1)

    def _get_duration(self, input_file: str) -> Optional[float]:
        """動画の長さを取得（秒）"""
        try:
            cmd = [
                self.ffprobe_path,
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                input_file
            ]
            result = subprocess.run(cmd, check=True, capture_output=True, encoding='utf-8', errors='replace')
            import json
            info = json.loads(result.stdout)
            return float(info.get('format', {}).get('duration', 0))
        except:
            return None

    def convert_to_mp4(
        self,
        input_file: str,
        output_file: Optional[str] = None
    ) -> Optional[str]:
        """
        動画ファイルをMP4形式に変換（HLS/m3u8対応）

        Args:
            input_file: 入力ファイルパス（動画ファイルまたはm3u8 URL）
            output_file: 出力ファイルパス（Noneの場合は自動生成）

        Returns:
            出力ファイルのパス、失敗時はNone
        """
        try:
            # 出力ファイル名を決定
            if output_file is None:
                # URLの場合とファイルパスの場合で処理を分ける
                if input_file.startswith('http://') or input_file.startswith('https://'):
                    # URLの場合は適当な名前を生成
                    from datetime import datetime
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_file = f"video_{timestamp}.mp4"
                else:
                    input_path = Path(input_file)
                    output_file = str(input_path.with_suffix('.mp4'))
            else:
                output_path = Path(output_file)
                if output_path.suffix != '.mp4':
                    output_file = str(output_path.with_suffix('.mp4'))

            print(f"MP4変換中: {input_file} → {output_file}")

            # ffmpegコマンドを実行（HLS/m3u8対応）
            cmd = [
                self.ffmpeg_path,
                "-i", input_file,
                "-c", "copy",  # コーデックをコピー（再エンコードなし）
                "-bsf:a", "aac_adtstoasc",  # AACストリームの修正
                "-y",  # 上書き確認なし
                output_file
            ]

            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                encoding='utf-8',
                errors='replace'
            )

            if Path(output_file).exists():
                file_size = Path(output_file).stat().st_size / (1024 * 1024)  # MB
                print(f"[OK] MP4変換完了: {output_file} ({file_size:.2f} MB)")
                return output_file
            else:
                print("[ERROR] 出力ファイルが生成されませんでした")
                return None

        except subprocess.CalledProcessError as e:
            print(f"[ERROR] MP4変換エラー: {e}")
            print(f"stderr: {e.stderr}")
            return None
        except Exception as e:
            print(f"[ERROR] 予期しないエラー: {e}")
            return None

    def extract_audio(
        self,
        input_file: str,
        output_file: Optional[str] = None,
        bitrate: str = "192k"
    ) -> Optional[str]:
        """
        動画ファイルから音声を抽出してMP3に変換

        Args:
            input_file: 入力ファイルパス
            output_file: 出力ファイルパス（Noneの場合は自動生成）
            bitrate: MP3のビットレート（デフォルト: 192k）

        Returns:
            出力ファイルのパス、失敗時はNone
        """
        try:
            input_path = Path(input_file)
            if not input_path.exists():
                print(f"[ERROR] エラー: ファイルが見つかりません: {input_file}")
                return None

            # 出力ファイル名を決定
            if output_file is None:
                output_file = str(input_path.with_suffix('.mp3'))
            else:
                output_path = Path(output_file)
                if output_path.suffix != '.mp3':
                    output_file = str(output_path.with_suffix('.mp3'))

            print(f"音声抽出中: {input_file} → {output_file}")

            # 動画の長さを取得
            total_duration = self._get_duration(input_file)

            # ffmpegコマンドを実行
            cmd = [
                self.ffmpeg_path,
                "-i", input_file,
                "-vn",  # 映像を無効化
                "-acodec", "libmp3lame",  # MP3コーデック
                "-b:a", bitrate,  # ビットレート
                "-y",  # 上書き確認なし
                "-progress", "pipe:2",  # 進捗をstderrに出力
                output_file
            ]

            # リアルタイムで進捗を表示
            import re
            process = subprocess.Popen(
                cmd,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                encoding='utf-8',
                errors='replace'
            )

            # stderrから進捗を読み取る
            for line in process.stderr:
                if total_duration and 'out_time_ms=' in line:
                    # out_time_ms=123456789 形式から現在の処理時間を取得
                    match = re.search(r'out_time_ms=(\d+)', line)
                    if match:
                        current_ms = int(match.group(1))
                        current_sec = current_ms / 1000000.0
                        percent = min(100, (current_sec / total_duration) * 100)
                        print(f"[PROGRESS] 音声抽出: {percent:.1f}%", flush=True)

            process.wait()

            if process.returncode != 0:
                print(f"[ERROR] ffmpegエラー: 終了コード {process.returncode}")
                return None

            if Path(output_file).exists():
                file_size = Path(output_file).stat().st_size / (1024 * 1024)  # MB
                print(f"[OK] 音声抽出完了: {output_file} ({file_size:.2f} MB)")
                return output_file
            else:
                print("[ERROR] 出力ファイルが生成されませんでした")
                return None

        except subprocess.CalledProcessError as e:
            print(f"[ERROR] 音声抽出エラー: {e}")
            print(f"stderr: {e.stderr}")
            return None
        except Exception as e:
            print(f"[ERROR] 予期しないエラー: {e}")
            return None

    def get_audio_info(self, audio_file: str) -> Optional[dict]:
        """
        音声ファイルの情報を取得

        Args:
            audio_file: 音声ファイルパス

        Returns:
            音声情報の辞書、失敗時はNone
        """
        try:
            cmd = [
                self.ffprobe_path,
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                audio_file
            ]

            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                encoding='utf-8',
                errors='replace'
            )

            import json
            info = json.loads(result.stdout)

            # 音声ストリーム情報を抽出
            audio_stream = None
            for stream in info.get('streams', []):
                if stream.get('codec_type') == 'audio':
                    audio_stream = stream
                    break

            if audio_stream:
                duration = float(info['format'].get('duration', 0))
                return {
                    'duration': duration,
                    'duration_str': f"{int(duration // 60)}分{int(duration % 60)}秒",
                    'codec': audio_stream.get('codec_name'),
                    'sample_rate': audio_stream.get('sample_rate'),
                    'channels': audio_stream.get('channels'),
                    'bitrate': info['format'].get('bit_rate'),
                }

            return None

        except Exception as e:
            print(f"[ERROR] 情報取得エラー: {e}")
            return None


def main():
    """テスト用のメイン関数"""
    import argparse

    parser = argparse.ArgumentParser(description="音声抽出ツール")
    parser.add_argument("input", help="入力動画ファイル")
    parser.add_argument("-o", "--output", help="出力MP3ファイル", default=None)
    parser.add_argument("-b", "--bitrate", help="ビットレート", default="192k")

    args = parser.parse_args()

    converter = AudioConverter()
    output = converter.extract_audio(args.input, args.output, args.bitrate)

    if output:
        info = converter.get_audio_info(output)
        if info:
            print(f"\n音声情報:")
            print(f"  長さ: {info['duration_str']}")
            print(f"  コーデック: {info['codec']}")
            print(f"  サンプルレート: {info['sample_rate']} Hz")
            print(f"  チャンネル数: {info['channels']}")
        return 0
    else:
        print("\n音声抽出に失敗しました")
        return 1


if __name__ == "__main__":
    sys.exit(main())
