# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

Instagram LiveやReelをMP3で保存し、自動的に文字起こしを行うPythonシステム。

## Architecture

システムは3つの主要モジュールで構成されています:

1. **downloader.py** - Instagram動画のダウンロード
   - `yt-dlp`を使用してInstagram動画を取得
   - `InstagramDownloader`クラスが処理を担当

2. **audio_converter.py** - 音声抽出・変換
   - `ffmpeg`を使用して動画からMP3音声を抽出
   - `AudioConverter`クラスが処理を担当

3. **transcriber.py** - 音声文字起こし
   - OpenAI Whisperを使用して日本語音声をテキスト化
   - `AudioTranscriber`クラスが処理を担当
   - 3種類の出力: プレーンテキスト、タイムスタンプ付きテキスト、JSON

4. **main.py** - メインオーケストレーター
   - 全モジュールを統合し、ワークフロー全体を管理
   - `InstagramLiveProcessor`クラスが処理を統括

## Development Setup

```bash
# 仮想環境の作成
python3 -m venv venv
source venv/bin/activate

# 依存関係のインストール
pip install -r requirements.txt

# システム依存パッケージ
brew install ffmpeg  # macOS
```

## Common Commands

### 基本的な使い方
```bash
# link.txtのURLを一括処理
python main.py

# 単一URLを処理
python main.py --url "https://www.instagram.com/reel/..."

# Whisperモデルを指定（精度 vs 速度のトレードオフ）
python main.py --model small   # 推奨: バランス型
python main.py --model medium  # 高精度（処理時間長め）
python main.py --model tiny    # 高速（精度低め）
```

### 個別モジュールのテスト
```bash
# ダウンローダーのテスト
python downloader.py "https://www.instagram.com/reel/..."

# 音声変換のテスト
python audio_converter.py input_video.mp4

# 文字起こしのテスト
python transcriber.py audio.mp3 --model base
```

## Input/Output

### 入力
- `link.txt` - Instagram動画URLのリスト（1行1URL）

### 出力（`output/`ディレクトリ）
- `*.mp3` - 抽出された音声ファイル
- `*_transcript.txt` - 文字起こしテキスト
- `*_transcript_detailed.txt` - タイムスタンプ付き文字起こし
- `*_transcript.json` - 詳細情報（セグメント、信頼度など）

## Technical Notes

- **文字コード**: 日本語対応のため、すべてのファイルI/OでUTF-8エンコーディングを使用
- **Whisperモデル**: `base`がデフォルト。`tiny` < `base` < `small` < `medium` < `large`の順で精度が向上（処理時間も増加）
- **エラーハンドリング**: 各モジュールは独立してエラー処理を行い、失敗時は`None`を返す
- **一時ファイル**: ダウンロードした動画ファイルは音声抽出後に自動削除される

## Dependencies

- **yt-dlp**: Instagram動画ダウンロード
- **ffmpeg**: 音声抽出・変換（システムパッケージ）
- **openai-whisper**: 音声認識・文字起こし
- **pydub**: 音声ファイル操作（Whisperの依存関係）

## Known Limitations

- Instagram動画のダウンロードは公開コンテンツに限定される
- 長時間の動画（60分以上）はWhisper処理に時間がかかる場合がある
- Whisper `large`モデルは高性能GPU推奨
