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

            # ffmpegコマンドを実行
            cmd = [
                self.ffmpeg_path,
                "-i", input_file,
                "-vn",  # 映像を無効化
                "-acodec", "libmp3lame",  # MP3コーデック
                "-b:a", bitrate,  # ビットレート
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
