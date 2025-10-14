# Instagram Live Transcription

Instagram LiveやReelをMP3で保存し、Whisper AIで自動文字起こしを行うElectronアプリです。

## ✨ 特徴

- 🎵 Instagram動画をMP3音声で保存
- 📝 OpenAI Whisperによる高精度な文字起こし
- 🌐 美しいLiquid GlassデザインのUI
- 🔄 **自動アップデート機能** - 新バージョンを自動的にダウンロード
- 📊 リアルタイム進捗表示
- 🎯 複数のWhisperモデル選択（速度 vs 精度）
- 📁 URL毎に整理されたフォルダ出力

## 📥 ダウンロード

**最新版**: [リリースページ](https://github.com/waqprime/tool-instagram-live-transcription/releases) からダウンロード

- **macOS**: `Instagram Live Transcription-x.x.x-arm64.dmg`
- **Windows**: `Instagram Live Transcription Setup x.x.x.exe`

**対応OS**:
- macOS 15.3.2 (24D81) 以降
- Windows 10/11

## 🚀 使い方

1. **アプリをダウンロード** - リリースページから最新版を取得
2. **インストール**
   - macOS: dmgファイルをマウントしてアプリをドラッグ
   - Windows: セットアップを実行
3. **起動** - アプリケーションを起動
4. **URLを入力** - Instagram ReelまたはLiveのURLを入力
5. **保存先を選択** - 出力フォルダを選択
6. **モデルと言語を選択** - 用途に応じて設定
7. **処理開始** - 自動的にダウンロード → 音声抽出 → 文字起こし

### 初回起動時の注意

**macOS**: 「開発元を確認できません」と表示された場合
- アプリを右クリック → 「開く」→「開く」をクリック

**Windows**: Windows Defenderの警告が出た場合
- 「詳細情報」→「実行」をクリック

## 🔄 自動アップデート

アプリは起動時に自動的に新しいバージョンをチェックします。
- 新バージョンが見つかるとバックグラウンドでダウンロード
- ダウンロード完了後、確認ダイアログを表示
- 「今すぐインストール」で即座にアップデート

## 🎨 スクリーンショット

（スクリーンショットを追加予定）

## 🛠️ 開発者向け - ビルド方法

### 依存関係のインストール

```bash
# Python仮想環境の作成
python3 -m venv venv_new
source venv_new/bin/activate  # Windows: venv_new\Scripts\activate

# Pythonパッケージのインストール
pip install -r requirements.txt

# ffmpegのインストール（音声変換に必要）
# macOS:
brew install ffmpeg

# Ubuntu/Debian:
sudo apt install ffmpeg

# Windows:
# https://ffmpeg.org/download.html からダウンロード

# Electronアプリの依存関係
cd electron-app
npm install
```

### 開発モードで起動

```bash
cd electron-app
npm start

# または開発者ツール付きで起動
npm run dev
```

### ビルド方法

```bash
cd electron-app

# macOS版
npm run build:mac

# Windows版
npm run build:win

# 両方ビルド
npm run build
```

ビルド成果物: `electron-app/dist/`

### リリース方法

詳しくは `electron-app/RELEASE_GUIDE.md` を参照してください。

```bash
# バージョンアップ
cd electron-app
npm version patch  # 1.0.0 → 1.0.1

# ビルド
npm run build:mac

# GitHubにプッシュ
git push --tags

# GitHubでリリースを作成し、dmg/exeをアップロード
```

## 📤 出力ファイル

選択した出力フォルダに、各URL毎のフォルダが作成されます：

```
output/
  ├── video_1_2025-10-14T00-42-24/
  │   ├── video_1.mp3
  │   └── video_1_transcript.txt
  └── video_2_2025-10-14T00-45-10/
      ├── video_2.mp3
      └── video_2_transcript.txt
```

## Whisperモデルについて

| モデル | 精度 | 速度 | 推奨用途 |
|--------|------|------|----------|
| tiny   | ★☆☆☆☆ | ★★★★★ | テスト用 |
| base   | ★★☆☆☆ | ★★★★☆ | デフォルト |
| small  | ★★★☆☆ | ★★★☆☆ | **推奨** |
| medium | ★★★★☆ | ★★☆☆☆ | 高精度 |
| large  | ★★★★★ | ★☆☆☆☆ | 最高精度（要GPU） |

## 注意事項

- Instagram動画のダウンロードには適切な権限が必要です
- 著作権に配慮して使用してください
- 長時間の動画は処理に時間がかかります
- 初回起動時はWhisperモデルのダウンロードに時間がかかります

## トラブルシューティング

### ffmpegが見つからないエラー
- macOS: `brew install ffmpeg`
- Windows: [公式サイト](https://ffmpeg.org/download.html)からダウンロードしてPATHに追加

### Whisperのダウンロードが遅い
- 初回起動時のみ発生します（モデルのダウンロード）
- 安定したネットワーク環境で実行してください

### macOSで「開発元を確認できません」エラー
- アプリを右クリック → 「開く」→「開く」で実行

### Windowsで「WindowsによってPCが保護されました」エラー
- 「詳細情報」→「実行」をクリック

## ライセンス

個人利用・商用利用ともに自由にご利用いただけます。

## 🏗️ 技術スタック

### フロントエンド
- **Electron**: クロスプラットフォームデスクトップアプリ
- **HTML/CSS/JavaScript**: Liquid Glassデザインの美しいUI
- **electron-updater**: 自動アップデート機能

### バックエンド
- **Python 3.13**: メイン処理エンジン
- **yt-dlp**: Instagram動画ダウンロード
- **ffmpeg**: 音声抽出・変換
- **OpenAI Whisper**: AI音声認識・文字起こし

### ビルド & デプロイ
- **electron-builder**: アプリケーションパッケージング
- **GitHub Releases**: 配布プラットフォーム
- **自動アップデート**: electron-updater + GitHub連携

## 🤝 コントリビューション

プルリクエスト大歓迎です！

1. このリポジトリをフォーク
2. 新しいブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

## 📄 ライセンス

MIT License - 個人利用・商用利用ともに自由にご利用いただけます。

## 🙏 謝辞

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - Instagram動画ダウンロード
- [OpenAI Whisper](https://github.com/openai/whisper) - 音声認識エンジン
- [Electron](https://www.electronjs.org/) - クロスプラットフォームフレームワーク
