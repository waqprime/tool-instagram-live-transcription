# Instagram Live Transcription - Electron App

Instagram LiveやReelをMP3で保存し、自動文字起こしを行うデスクトップアプリケーション。

## Features

- **Liquid Glass UI**: 美しいガラスモルフィズムデザイン
- **Multiple URLs**: 複数のInstagram URLを一括処理
- **Real-time Logs**: 処理状況をリアルタイムで確認
- **Progress Tracking**: 進行状況を視覚的に表示
- **DevTools Support**: F12キーでChrome DevToolsを開いてCSS開発が可能
- **Multi-language**: 日本語、英語、中国語、韓国語など多言語対応
- **High Accuracy**: Whisper largeモデルで最高精度の文字起こし

## Tech Stack

- **Frontend**: HTML5, CSS3 (Liquid Glass Design), Vanilla JavaScript
- **Framework**: Electron 28
- **Backend**: Node.js + Python 3
- **AI**: OpenAI Whisper (large model)
- **Video Download**: yt-dlp
- **Audio Processing**: ffmpeg

## Project Structure

```
electron-app/
├── package.json          # Node.js dependencies
├── main.js               # Electron main process
├── preload.js            # Secure IPC bridge
├── index.html            # UI structure
├── styles.css            # Liquid Glass CSS
├── renderer.js           # Frontend logic
├── backend/
│   └── process.js        # Python process manager
└── README.md
```

## Installation

### 1. System Requirements

- Node.js 18+
- Python 3.8+
- ffmpeg
- macOS, Windows, or Linux

### 2. Install System Dependencies

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
```

### 3. Setup Python Environment

```bash
# Navigate to project root (parent directory)
cd /Users/saorin/Desktop/ai/インスタライブ音声

# Create virtual environment (if not exists)
python3 -m venv venv_new

# Activate virtual environment
source venv_new/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### 4. Install Electron Dependencies

```bash
# Navigate to electron-app directory
cd electron-app

# Install Node.js dependencies
npm install
```

## Usage

### Development Mode (with DevTools)

```bash
npm run dev
```

- DevToolsが自動的に開きます
- F12キーでDevToolsの表示/非表示を切り替え
- CSS編集をリアルタイムで確認可能

### Production Mode

```bash
npm start
```

### Using the App

1. **URLを入力**: Instagram LiveやReelのURLを入力（+ 追加ボタンで複数追加可能）
2. **言語を選択**: 文字起こしする言語を選択（デフォルト: 日本語）
3. **保存先を選択**: 出力ファイルの保存先を指定
4. **開始**: 処理を開始
5. **完了後**: "フォルダを開く"ボタンで結果を確認

### Output Files

処理後、以下のファイルが生成されます：

- `*.mp3` - 抽出された音声ファイル
- `*_transcript.txt` - プレーンテキスト文字起こし
- `*_transcript_detailed.txt` - タイムスタンプ付き文字起こし
- `*_transcript.json` - 詳細データ（セグメント、信頼度など）

## Development

### CSS Development

Liquid Glass CSSの調整方法：

1. `npm run dev`で開発モードで起動
2. DevToolsでElementsタブを開く
3. `styles.css`をライブ編集
4. 変更を確認後、`styles.css`ファイルに反映

### Key CSS Variables

```css
/* Background */
background: #0f1729;

/* Glass Card */
background: rgba(6, 78, 59, 0.18);
border: 1px solid rgba(110, 231, 183, 0.2);
box-shadow: 0px 10px 30px 0 rgba(2, 44, 34, 0.25),
            inset 0 0 0px rgba(255, 255, 255, 0),
            inset 0px 0px 4px 2px rgba(255, 255, 255, 0.05);
```

### Python Integration

Electronは以下のPythonスクリプトを呼び出します：

- `downloader.py` - Instagram動画ダウンロード (yt-dlp)
- `audio_converter.py` - 動画から音声抽出 (ffmpeg)
- `transcriber.py` - 音声文字起こし (Whisper)

`backend/process.js`でプロセス管理とログ処理を行います。

## Troubleshooting

### Python not found

```bash
# Check Python path
which python3

# Update pythonPath in main.js if needed
const pythonPath = '/path/to/your/venv_new/bin/python3';
```

### ffmpeg not found

```bash
# Verify ffmpeg installation
ffmpeg -version

# Install if missing
brew install ffmpeg  # macOS
```

### Whisper model download

初回起動時、Whisperモデル（約3GB）が自動ダウンロードされます。
インターネット接続が必要です。

## Building for Production

### macOS

```bash
npm install electron-builder --save-dev
npm run build:mac
```

### Windows

```bash
npm install electron-builder --save-dev
npm run build:win
```

## License

MIT License

## Credits

- **Whisper**: OpenAI
- **yt-dlp**: Community-driven YouTube-DL fork
- **Electron**: GitHub/Microsoft
- **Design**: Liquid Glass CSS aesthetic
