#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音声文字起こしモジュール
4つのエンジンに対応:
  - faster-whisper (デフォルト、高速・高精度)
  - openai-api (クラウド、OpenAI Whisper API / gpt-4o-transcribe)
  - local-whisper (従来版、openai-whisper)
  - kotoba-whisper (日本語特化、Kotoba-Whisper v2.0)
"""

import os
import sys
import json
import ssl
import time
import traceback
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, List

# SSL証明書の設定（PyInstaller環境対応）
try:
    import certifi
    os.environ['SSL_CERT_FILE'] = certifi.where()
except ImportError:
    pass

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


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------
class TranscriberBase(ABC):
    """全エンジン共通のインターフェース"""

    def __init__(self, model_name: str, language: str = "ja"):
        self.model_name = model_name
        self.language = language

        # ffmpegパスを環境変数から取得してPATHに追加
        ffmpeg_binary = os.environ.get('FFMPEG_BINARY')
        if ffmpeg_binary and os.path.isfile(ffmpeg_binary):
            ffmpeg_dir = os.path.dirname(ffmpeg_binary)
            os.environ['PATH'] = ffmpeg_dir + os.pathsep + os.environ.get('PATH', '')
            print(f"ffmpegパスを設定: {ffmpeg_dir}", flush=True)

    @abstractmethod
    def _load_model(self):
        """モデル/クライアントを初期化"""

    @abstractmethod
    def _run_transcription(self, audio_path: str) -> Optional[Dict]:
        """
        文字起こしを実行し、統一形式で返す。

        Returns:
            {
                'text': str,              # 全文テキスト
                'segments': [             # セグメントのリスト
                    {'start': float, 'end': float, 'text': str}, ...
                ]
            }
            失敗時は None
        """

    def transcribe(
        self,
        audio_file: str,
        output_dir: Optional[str] = None,
        save_json: bool = False
    ) -> Optional[Dict]:
        """音声ファイルを文字起こしし、出力ファイルを保存"""
        try:
            audio_path = Path(audio_file)
            if not audio_path.exists():
                print(f"[ERROR] エラー: ファイルが見つかりません: {audio_file}", flush=True)
                return None

            print(f"\n文字起こし中: {audio_file}", flush=True)
            print("(処理には数分かかる場合があります...)", flush=True)
            print(f"[PROGRESS] 文字起こし: 0%", flush=True)

            result = self._run_transcription(str(audio_path))
            if result is None:
                return None

            print(f"[PROGRESS] 文字起こし: 100%", flush=True)

            # 出力ファイルを保存
            self._save_outputs(audio_path, result, output_dir, save_json)

            print(f"\n文字起こし完了!", flush=True)
            print(f"全体の文字数: {len(result['text'])}文字", flush=True)
            print(f"セグメント数: {len(result['segments'])}", flush=True)

            return result

        except Exception as e:
            print(f"[ERROR] 文字起こしエラー: {e}", flush=True)
            traceback.print_exc()
            return None

    # --- 共通ユーティリティ ------------------------------------------------

    def _save_outputs(
        self,
        audio_path: Path,
        result: Dict,
        output_dir: Optional[str],
        save_json: bool
    ):
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True)
        else:
            output_path = audio_path.parent

        base_name = audio_path.stem

        # 1. 全文テキスト
        txt_file = output_path / f"{base_name}_transcript.txt"
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(result['text'])
        print(f"[OK] 全文テキスト保存: {txt_file}", flush=True)

        # 2. タイムスタンプ付きテキスト（話者情報対応）
        detailed_file = output_path / f"{base_name}_transcript_detailed.txt"
        with open(detailed_file, 'w', encoding='utf-8') as f:
            for seg in result['segments']:
                start = self._format_timestamp(seg['start'])
                end = self._format_timestamp(seg['end'])
                text = seg['text'].strip()
                speaker = seg.get('speaker', '')
                if speaker:
                    f.write(f"[{start} -> {end}] [{speaker}] {text}\n")
                else:
                    f.write(f"[{start} -> {end}] {text}\n")
        print(f"[OK] タイムスタンプ付きテキスト保存: {detailed_file}", flush=True)

        # 3. JSON（オプション）
        if save_json:
            json_file = output_path / f"{base_name}_transcript.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"[OK] JSON保存: {json_file}", flush=True)

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def get_model_info(self) -> Dict:
        return {
            'model_name': self.model_name,
            'language': self.language,
            'engine': self.__class__.__name__,
        }


# ---------------------------------------------------------------------------
# Engine 1: faster-whisper (default)
# ---------------------------------------------------------------------------
class FasterWhisperTranscriber(TranscriberBase):
    """faster-whisper を使用した高速・高精度文字起こし"""

    MODELS = [
        "large-v3-turbo", "large-v3", "large-v2",
        "medium", "small", "base", "tiny",
    ]
    DEFAULT_MODEL = "large-v3-turbo"

    def __init__(self, model_name: Optional[str] = None, language: str = "ja"):
        name = model_name or self.DEFAULT_MODEL
        super().__init__(name, language)
        print(f"[faster-whisper] モデルを読み込み中... (モデル: {self.model_name})", flush=True)
        self._load_model()

    def _load_model(self):
        from faster_whisper import WhisperModel

        # GPU自動検出
        device = "cpu"
        compute_type = "int8"
        try:
            import torch
            if torch.cuda.is_available():
                device = "cuda"
                compute_type = "float16"
                print(f"[faster-whisper] GPU (CUDA) を検出しました", flush=True)
        except ImportError:
            pass

        try:
            self.model = WhisperModel(
                self.model_name,
                device=device,
                compute_type=compute_type,
            )
            print(f"[OK] faster-whisper モデル読み込み完了: {self.model_name} (device={device}, compute={compute_type})", flush=True)
        except Exception as e:
            if device == "cuda":
                print(f"[WARNING] GPU読み込み失敗、CPUにフォールバックします: {e}", flush=True)
                self.model = WhisperModel(
                    self.model_name,
                    device="cpu",
                    compute_type="int8",
                )
                print(f"[OK] faster-whisper モデル読み込み完了: {self.model_name} (device=cpu, compute=int8)", flush=True)
            else:
                raise

    def _run_transcription(self, audio_path: str) -> Optional[Dict]:
        try:
            segments_iter, info = self.model.transcribe(
                audio_path,
                language=self.language,
                beam_size=5,
                vad_filter=True,
            )

            full_text_parts: List[str] = []
            segments: List[Dict] = []

            for seg in segments_iter:
                full_text_parts.append(seg.text)
                segments.append({
                    'start': seg.start,
                    'end': seg.end,
                    'text': seg.text,
                })

            return {
                'text': ''.join(full_text_parts),
                'segments': segments,
            }
        except Exception as e:
            print(f"[ERROR] faster-whisper 文字起こしエラー: {e}", flush=True)
            traceback.print_exc()
            return None


# ---------------------------------------------------------------------------
# Engine 2: OpenAI API (cloud)
# ---------------------------------------------------------------------------
class OpenAIAPITranscriber(TranscriberBase):
    """OpenAI Whisper API / gpt-4o-transcribe を使用したクラウド文字起こし"""

    MODELS = ["gpt-4o-transcribe", "gpt-4o-mini-transcribe", "whisper-1"]
    DEFAULT_MODEL = "gpt-4o-transcribe"
    MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB
    CHUNK_DURATION_MS = 10 * 60 * 1000  # 10分

    def __init__(self, model_name: Optional[str] = None, language: str = "ja", api_key: Optional[str] = None):
        name = model_name or self.DEFAULT_MODEL
        if name not in self.MODELS:
            print(f"[WARNING] openai-api は '{name}' をサポートしていません。'{self.DEFAULT_MODEL}' を使用します。", flush=True)
            name = self.DEFAULT_MODEL
        super().__init__(name, language)
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError(
                "OpenAI APIキーが必要です。--api-key 引数または環境変数 OPENAI_API_KEY を設定してください。"
            )
        print(f"[openai-api] OpenAI API を使用します (モデル: {self.model_name})", flush=True)
        self._load_model()

    def _load_model(self):
        from openai import OpenAI
        self.client = OpenAI(api_key=self.api_key)
        print(f"[OK] OpenAI API クライアント初期化完了", flush=True)

    def _run_transcription(self, audio_path: str) -> Optional[Dict]:
        try:
            file_size = os.path.getsize(audio_path)

            if file_size <= self.MAX_FILE_SIZE:
                return self._transcribe_single(audio_path)
            else:
                print(f"[openai-api] ファイルサイズ ({file_size / 1024 / 1024:.1f}MB) が25MBを超えています。分割して送信します。", flush=True)
                return self._transcribe_chunked(audio_path)

        except Exception as e:
            print(f"[ERROR] OpenAI API 文字起こしエラー: {e}", flush=True)
            traceback.print_exc()
            return None

    def _is_gpt4o_model(self) -> bool:
        """gpt-4o系モデルかどうかを判定"""
        return self.model_name.startswith("gpt-4o")

    def _transcribe_single(self, audio_path: str) -> Optional[Dict]:
        """単一ファイルを送信"""
        for attempt in range(3):
            try:
                with open(audio_path, 'rb') as f:
                    # gpt-4o系モデルは timestamp_granularities 非対応
                    params = {
                        'model': self.model_name,
                        'file': f,
                        'language': self.language,
                        'response_format': "verbose_json",
                    }
                    if not self._is_gpt4o_model():
                        params['timestamp_granularities'] = ["segment"]

                    response = self.client.audio.transcriptions.create(**params)

                segments = []
                if hasattr(response, 'segments') and response.segments:
                    for seg in response.segments:
                        segments.append({
                            'start': seg.get('start', seg.start) if hasattr(seg, 'start') else seg.get('start', 0),
                            'end': seg.get('end', seg.end) if hasattr(seg, 'end') else seg.get('end', 0),
                            'text': seg.get('text', seg.text) if hasattr(seg, 'text') else seg.get('text', ''),
                        })
                else:
                    # gpt-4o系など segments が返らないモデル用フォールバック
                    if response.text:
                        segments.append({
                            'start': 0.0,
                            'end': 0.0,
                            'text': response.text,
                        })

                return {
                    'text': response.text,
                    'segments': segments,
                }

            except Exception as e:
                wait = 2 ** attempt
                print(f"[WARNING] OpenAI API リトライ {attempt + 1}/3 ({wait}秒待機): {e}", flush=True)
                if attempt < 2:
                    time.sleep(wait)
                else:
                    raise

    def _transcribe_chunked(self, audio_path: str) -> Optional[Dict]:
        """大きなファイルを分割して送信"""
        from pydub import AudioSegment
        import tempfile

        audio = AudioSegment.from_file(audio_path)
        duration_ms = len(audio)
        chunks = []
        offset = 0

        while offset < duration_ms:
            end = min(offset + self.CHUNK_DURATION_MS, duration_ms)
            chunks.append(audio[offset:end])
            offset = end

        print(f"[openai-api] {len(chunks)}チャンクに分割しました", flush=True)

        full_text_parts: List[str] = []
        all_segments: List[Dict] = []
        time_offset = 0.0
        failed_chunks = 0

        for idx, chunk in enumerate(chunks):
            print(f"[openai-api] チャンク {idx + 1}/{len(chunks)} を送信中...", flush=True)

            tmp_path = None
            try:
                # 一時ファイルに書き出し
                with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
                    tmp_path = tmp.name
                    chunk.export(tmp_path, format='mp3')

                result = self._transcribe_single(tmp_path)
                if result:
                    full_text_parts.append(result['text'])
                    for seg in result['segments']:
                        all_segments.append({
                            'start': seg['start'] + time_offset,
                            'end': seg['end'] + time_offset,
                            'text': seg['text'],
                        })
            except Exception as e:
                failed_chunks += 1
                print(f"[WARNING] チャンク {idx + 1}/{len(chunks)} の処理に失敗（スキップ）: {e}", flush=True)
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    os.unlink(tmp_path)

            time_offset += len(chunk) / 1000.0

        if failed_chunks > 0:
            print(f"[WARNING] {failed_chunks}/{len(chunks)} チャンクが失敗しました", flush=True)

        if not full_text_parts:
            return None

        return {
            'text': ''.join(full_text_parts),
            'segments': all_segments,
        }


# ---------------------------------------------------------------------------
# Engine 3: local-whisper (従来版)
# ---------------------------------------------------------------------------
class LocalWhisperTranscriber(TranscriberBase):
    """従来の openai-whisper を使用した文字起こし"""

    MODELS = ["tiny", "base", "small", "medium", "large"]
    DEFAULT_MODEL = "base"

    def __init__(self, model_name: Optional[str] = None, language: str = "ja"):
        name = model_name or self.DEFAULT_MODEL
        if name not in self.MODELS:
            print(f"[WARNING] local-whisper は '{name}' をサポートしていません。'{self.DEFAULT_MODEL}' を使用します。", flush=True)
            name = self.DEFAULT_MODEL
        super().__init__(name, language)
        print(f"[local-whisper] Whisperモデルを読み込み中... (サイズ: {self.model_name})", flush=True)
        self._load_model()

    def _load_model(self):
        import whisper
        try:
            self.model = whisper.load_model(self.model_name)
            print(f"[OK] モデル読み込み完了: {self.model_name}", flush=True)
        except Exception as e:
            print(f"[ERROR] モデル読み込みエラー: {e}", flush=True)
            sys.exit(1)

    def _run_transcription(self, audio_path: str) -> Optional[Dict]:
        try:
            result = self.model.transcribe(
                audio_path,
                language=self.language,
                verbose=False,
            )
            segments = []
            for seg in result.get('segments', []):
                segments.append({
                    'start': seg['start'],
                    'end': seg['end'],
                    'text': seg['text'],
                })
            return {
                'text': result['text'],
                'segments': segments,
            }
        except Exception as e:
            print(f"[ERROR] local-whisper 文字起こしエラー: {e}", flush=True)
            traceback.print_exc()
            return None


# ---------------------------------------------------------------------------
# Engine 4: Kotoba-Whisper (日本語特化)
# ---------------------------------------------------------------------------
class KotobaWhisperTranscriber(TranscriberBase):
    """Kotoba-Whisper v2.0 を使用した日本語特化文字起こし"""

    MODELS = ["kotoba-whisper-v2.0"]
    DEFAULT_MODEL = "kotoba-whisper-v2.0"
    HF_MODEL_ID = "kotoba-tech/kotoba-whisper-v2.0"

    def __init__(self, model_name: Optional[str] = None, language: str = "ja"):
        name = model_name or self.DEFAULT_MODEL
        super().__init__(name, language)
        print(f"[kotoba-whisper] Kotoba-Whisper v2.0 を読み込み中... (日本語特化モデル)", flush=True)
        self._load_model()

    def _load_model(self):
        import torch
        from transformers import pipeline

        # デバイス自動検出: CUDA → MPS (Apple Silicon) → CPU
        device = "cpu"
        torch_dtype = torch.float32
        if torch.cuda.is_available():
            device = "cuda"
            torch_dtype = torch.float16
            print(f"[kotoba-whisper] GPU (CUDA) を検出しました", flush=True)
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            device = "mps"
            torch_dtype = torch.float16
            print(f"[kotoba-whisper] Apple Silicon (MPS) を検出しました", flush=True)

        try:
            self.pipe = pipeline(
                "automatic-speech-recognition",
                model=self.HF_MODEL_ID,
                device=device,
                torch_dtype=torch_dtype,
                chunk_length_s=30,
            )
            print(f"[OK] Kotoba-Whisper v2.0 読み込み完了 (device={device})", flush=True)
        except Exception as e:
            if device != "cpu":
                print(f"[WARNING] {device} での読み込みに失敗、CPUにフォールバックします: {e}", flush=True)
                self.pipe = pipeline(
                    "automatic-speech-recognition",
                    model=self.HF_MODEL_ID,
                    device="cpu",
                    torch_dtype=torch.float32,
                    chunk_length_s=30,
                )
                print(f"[OK] Kotoba-Whisper v2.0 読み込み完了 (device=cpu)", flush=True)
            else:
                raise

    def _run_transcription(self, audio_path: str) -> Optional[Dict]:
        try:
            result = self.pipe(
                audio_path,
                return_timestamps=True,
                generate_kwargs={"language": "japanese", "task": "transcribe"},
            )

            full_text = result.get("text", "")
            segments: List[Dict] = []

            # chunks（タイムスタンプ付きセグメント）を変換
            chunks = result.get("chunks", [])
            if chunks:
                for chunk in chunks:
                    ts = chunk.get("timestamp", (0.0, 0.0))
                    start = ts[0] if ts[0] is not None else 0.0
                    end = ts[1] if ts[1] is not None else start
                    segments.append({
                        'start': float(start),
                        'end': float(end),
                        'text': chunk.get("text", ""),
                    })
            else:
                # チャンクがない場合は全文を1セグメントとして返す
                segments.append({
                    'start': 0.0,
                    'end': 0.0,
                    'text': full_text,
                })

            return {
                'text': full_text,
                'segments': segments,
            }
        except Exception as e:
            print(f"[ERROR] Kotoba-Whisper 文字起こしエラー: {e}", flush=True)
            traceback.print_exc()
            return None


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------
def create_transcriber(
    engine: str = "faster-whisper",
    model: Optional[str] = None,
    language: str = "ja",
    api_key: Optional[str] = None,
) -> TranscriberBase:
    """
    エンジン名からトランスクライバーを生成するファクトリ関数。

    faster-whisper のインポートに失敗した場合は local-whisper にフォールバック。
    """
    if engine == "openai-api":
        return OpenAIAPITranscriber(model_name=model, language=language, api_key=api_key)

    if engine == "faster-whisper":
        try:
            return FasterWhisperTranscriber(model_name=model, language=language)
        except ImportError:
            print("[WARNING] faster-whisper が見つかりません。local-whisper にフォールバックします。", flush=True)
            print("[WARNING] インストール: pip install faster-whisper", flush=True)
            return LocalWhisperTranscriber(model_name=model, language=language)

    if engine == "local-whisper":
        return LocalWhisperTranscriber(model_name=model, language=language)

    if engine == "kotoba-whisper":
        return KotobaWhisperTranscriber(model_name=model, language=language)

    raise ValueError(f"不明なエンジン: {engine}  (選択肢: faster-whisper, openai-api, local-whisper, kotoba-whisper)")


# ---------------------------------------------------------------------------
# Backward-compatible wrapper
# ---------------------------------------------------------------------------
class AudioTranscriber:
    """後方互換ラッパー — main.py から呼び出されるIF を維持"""

    MODELS = ["tiny", "base", "small", "medium", "large"]

    def __init__(
        self,
        model_size: str = "base",
        language: str = "ja",
        engine: str = "faster-whisper",
        api_key: Optional[str] = None,
    ):
        self.engine = engine
        self._transcriber = create_transcriber(
            engine=engine,
            model=model_size if model_size else None,
            language=language,
            api_key=api_key,
        )

    def transcribe(
        self,
        audio_file: str,
        output_dir: Optional[str] = None,
        save_json: bool = False,
    ) -> Optional[Dict]:
        return self._transcriber.transcribe(audio_file, output_dir, save_json)

    def get_model_info(self) -> Dict:
        return self._transcriber.get_model_info()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    """テスト用のメイン関数"""
    import argparse

    parser = argparse.ArgumentParser(description="音声文字起こしツール")
    parser.add_argument("audio", help="音声ファイル")
    parser.add_argument("-m", "--model", help="モデル名", default=None)
    parser.add_argument("-l", "--language", help="言語コード", default="ja")
    parser.add_argument("-o", "--output", help="出力ディレクトリ", default=None)
    parser.add_argument(
        "-e", "--engine",
        choices=["faster-whisper", "openai-api", "local-whisper", "kotoba-whisper"],
        default="faster-whisper",
        help="文字起こしエンジン (デフォルト: faster-whisper)",
    )
    parser.add_argument("--api-key", help="OpenAI APIキー (openai-api エンジン用)", default=None)

    args = parser.parse_args()

    transcriber = create_transcriber(
        engine=args.engine,
        model=args.model,
        language=args.language,
        api_key=args.api_key,
    )
    result = transcriber.transcribe(args.audio, args.output)

    if result:
        print("\n=== 文字起こし結果（抜粋） ===", flush=True)
        print(result['text'][:500], flush=True)
        if len(result['text']) > 500:
            print("...", flush=True)
        return 0
    else:
        print("\n文字起こしに失敗しました", flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
