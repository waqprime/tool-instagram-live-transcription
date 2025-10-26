# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

Instagram LiveやReelをMP3で保存し、自動的に文字起こしを行うPythonシステム。
YouTube、X Spaces、Voicy、UTAGEなど、yt-dlp対応の1,800以上のプラットフォームに対応。

## Architecture

システムは4つの主要モジュールで構成されています:

1. **downloader.py** - 動画・音声のダウンロード
   - `yt-dlp`を使用して各種プラットフォームから動画・音声を取得
   - `VideoDownloader`クラスが処理を担当
   - UTAGE動画の自動検出とm3u8抽出に対応
   - `--keep-video`オプションでUTAGE動画をMP4形式に自動変換

2. **audio_converter.py** - 音声抽出・変換
   - `ffmpeg`を使用して動画からMP3音声を抽出
   - `AudioConverter`クラスが処理を担当
   - HLS/m3u8形式からMP4への変換機能を提供

3. **transcriber.py** - 音声文字起こし
   - OpenAI Whisperを使用して日本語音声をテキスト化
   - `AudioTranscriber`クラスが処理を担当
   - 3種類の出力: プレーンテキスト、タイムスタンプ付きテキスト、JSON

4. **main.py** - メインオーケストレーター
   - 全モジュールを統合し、ワークフロー全体を管理
   - `AudioTranscriptionProcessor`クラスが処理を統括

5. **utage_extractor.py** - UTAGE専用モジュール
   - Seleniumを使用してUTAGEページから動画URLを抽出
   - ブラウザ自動化によりm3u8 URLを取得

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

# 単一URLを処理（Instagram）
python main.py --url "https://www.instagram.com/reel/..."

# 単一URLを処理（YouTube）
python main.py --url "https://www.youtube.com/watch?v=..."

# 単一URLを処理（UTAGE）
python main.py --url "https://example.utage-system.com/..."

# 動画ファイルを保持する（MP4として保存、削除しない）
python main.py --url "URL" --keep-video

# UTAGE動画をMP4で保存（ローカル再生可能）
python main.py --url "UTAGE_URL" --keep-video

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
- `link.txt` - 動画・音声URLのリスト（1行1URL、Instagram/YouTube/X Spaces/Voicy/UTAGE等）

### 出力（デフォルト: `~/Downloads/InstagramTranscripts/`）
- `*.mp3` - 抽出された音声ファイル
- `*.mp4` - 動画ファイル（`--keep-video`オプション使用時）
- `*_converted.mp4` - UTAGE動画のMP4変換版（`--keep-video`使用時）
- `*_transcript.txt` - 文字起こしテキスト
- `*_transcript_detailed.txt` - タイムスタンプ付き文字起こし
- `*_transcript.json` - 詳細情報（セグメント、信頼度など）

## Technical Notes

- **文字コード**: 日本語対応のため、すべてのファイルI/OでUTF-8エンコーディングを使用
- **Whisperモデル**: `base`がデフォルト。`tiny` < `base` < `small` < `medium` < `large`の順で精度が向上（処理時間も増加）
- **エラーハンドリング**: 各モジュールは独立してエラー処理を行い、失敗時は`None`を返す
- **動画ファイル保持**: デフォルトでは音声抽出後に動画ファイルを自動削除、`--keep-video`フラグで保持可能
- **UTAGE動画変換**: `--keep-video`使用時、UTAGE動画（HLS/m3u8）はローカル再生可能なMP4形式に自動変換される

## Dependencies

- **yt-dlp**: 各種プラットフォームから動画・音声ダウンロード
- **ffmpeg**: 音声抽出・変換、MP4変換（システムパッケージ）
- **openai-whisper**: 音声認識・文字起こし
- **selenium**: UTAGE動画URL抽出用のブラウザ自動化
- **webdriver-manager**: ChromeDriverの自動インストール
- **pydub**: 音声ファイル操作（Whisperの依存関係）

## Known Limitations

- Instagram動画のダウンロードは公開コンテンツに限定される
- 長時間の動画（60分以上）はWhisper処理に時間がかかる場合がある
- Whisper `large`モデルは高性能GPU推奨
- UTAGE動画の抽出にはChromeブラウザとSeleniumが必要（初回実行時に自動インストール）
