#!/usr/bin/env python3
"""
音声文字起こしモジュール
OpenAI Whisperを使用して音声をテキストに変換
"""

import os
import sys
import json
from pathlib import Path
from typing import Optional, Dict, List
import whisper


class AudioTranscriber:
    """Whisperを使用した音声文字起こしクラス"""

    # 利用可能なモデルサイズ
    MODELS = ["tiny", "base", "small", "medium", "large"]

    def __init__(self, model_size: str = "base", language: str = "ja"):
        """
        Args:
            model_size: Whisperモデルのサイズ (tiny/base/small/medium/large)
            language: 言語コード (デフォルト: ja=日本語)
        """
        if model_size not in self.MODELS:
            print(f"[ERROR] 無効なモデルサイズ: {model_size}")
            print(f"利用可能なモデル: {', '.join(self.MODELS)}")
            sys.exit(1)

        self.model_size = model_size
        self.language = language
        self.model = None

        print(f"Whisperモデルを読み込み中... (サイズ: {model_size})")
        self._load_model()

    def _load_model(self):
        """Whisperモデルを読み込む"""
        try:
            self.model = whisper.load_model(self.model_size)
            print(f"[OK] モデル読み込み完了: {self.model_size}")
        except Exception as e:
            print(f"[ERROR] モデル読み込みエラー: {e}")
            sys.exit(1)

    def transcribe(
        self,
        audio_file: str,
        output_dir: Optional[str] = None,
        save_json: bool = False
    ) -> Optional[Dict]:
        """
        音声ファイルを文字起こし

        Args:
            audio_file: 音声ファイルのパス
            output_dir: 出力ディレクトリ（Noneの場合は音声ファイルと同じ場所）
            save_json: JSON形式でも保存するか

        Returns:
            文字起こし結果の辞書、失敗時はNone
        """
        try:
            audio_path = Path(audio_file)
            if not audio_path.exists():
                print(f"[ERROR] エラー: ファイルが見つかりません: {audio_file}")
                return None

            print(f"\n文字起こし中: {audio_file}")
            print("(処理には数分かかる場合があります...)")

            # 文字起こし実行
            result = self.model.transcribe(
                str(audio_path),
                language=self.language,
                verbose=False
            )

            # 出力ディレクトリを決定
            if output_dir:
                output_path = Path(output_dir)
                output_path.mkdir(exist_ok=True)
            else:
                output_path = audio_path.parent

            # ベースファイル名
            base_name = audio_path.stem

            # 1. まとめたテキスト（全文）
            txt_file = output_path / f"{base_name}_transcript.txt"
            with open(txt_file, 'w', encoding='utf-8') as f:
                f.write(result['text'])
            print(f"[OK] 全文テキスト保存: {txt_file}")

            # 2. タイムスタンプ付きテキスト
            detailed_file = output_path / f"{base_name}_transcript_detailed.txt"
            with open(detailed_file, 'w', encoding='utf-8') as f:
                for segment in result['segments']:
                    start = self._format_timestamp(segment['start'])
                    end = self._format_timestamp(segment['end'])
                    text = segment['text'].strip()
                    f.write(f"[{start} -> {end}] {text}\n")
            print(f"[OK] タイムスタンプ付きテキスト保存: {detailed_file}")

            # JSONは保存しない（オプションで有効化可能）
            if save_json:
                json_file = output_path / f"{base_name}_transcript.json"
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                print(f"[OK] JSON保存: {json_file}")

            print(f"\n文字起こし完了!")
            print(f"全体の文字数: {len(result['text'])}文字")
            print(f"セグメント数: {len(result['segments'])}")

            return result

        except Exception as e:
            print(f"[ERROR] 文字起こしエラー: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _format_timestamp(self, seconds: float) -> str:
        """
        秒数を時:分:秒形式に変換

        Args:
            seconds: 秒数

        Returns:
            "HH:MM:SS"形式の文字列
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def get_model_info(self) -> Dict:
        """
        使用中のモデル情報を取得

        Returns:
            モデル情報の辞書
        """
        return {
            'model_size': self.model_size,
            'language': self.language,
            'description': self._get_model_description(self.model_size)
        }

    @staticmethod
    def _get_model_description(model_size: str) -> str:
        """モデルサイズの説明を取得"""
        descriptions = {
            'tiny': '最小・最速（精度は低め）',
            'base': '小型・高速（バランス型）',
            'small': '中型（推奨）',
            'medium': '大型・高精度（処理時間長め）',
            'large': '最大・最高精度（要高性能PC）'
        }
        return descriptions.get(model_size, '不明')


def main():
    """テスト用のメイン関数"""
    import argparse

    parser = argparse.ArgumentParser(description="音声文字起こしツール")
    parser.add_argument("audio", help="音声ファイル")
    parser.add_argument("-m", "--model", help="Whisperモデル",
                       default="base", choices=AudioTranscriber.MODELS)
    parser.add_argument("-l", "--language", help="言語コード", default="ja")
    parser.add_argument("-o", "--output", help="出力ディレクトリ", default=None)

    args = parser.parse_args()

    transcriber = AudioTranscriber(args.model, args.language)
    result = transcriber.transcribe(args.audio, args.output)

    if result:
        print("\n=== 文字起こし結果（抜粋） ===")
        print(result['text'][:500])
        if len(result['text']) > 500:
            print("...")
        return 0
    else:
        print("\n文字起こしに失敗しました")
        return 1


if __name__ == "__main__":
    sys.exit(main())
