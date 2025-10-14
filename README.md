# Instagram Live Transcription

<div align="center">

Instagram LiveやReelを**簡単に**MP3保存 & AI文字起こし

[![GitHub release](https://img.shields.io/github/v/release/waqprime/tool-instagram-live-transcription)](https://github.com/waqprime/tool-instagram-live-transcription/releases)
[![Downloads](https://img.shields.io/github/downloads/waqprime/tool-instagram-live-transcription/total)](https://github.com/waqprime/tool-instagram-live-transcription/releases)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**[📥 ダウンロード](#-ダウンロード方法) • [📖 使い方](#-使い方簡単3ステップ) • [❓ FAQ](#-よくある質問faq)**

![App Screenshot](https://via.placeholder.com/800x500/1a1a2e/ffffff?text=Instagram+Live+Transcription+%E3%82%B9%E3%82%AF%E3%83%AA%E3%83%BC%E3%83%B3%E3%82%B7%E3%83%A7%E3%83%83%E3%83%88%E3%82%92%E8%BF%BD%E5%8A%A0%E4%BA%88%E5%AE%9A)

</div>

---

## ✨ できること

<table>
<tr>
<td width="50%">

### 🎵 動画を音声に変換
Instagram ReelやLiveの動画を、高音質のMP3ファイルとして保存できます。

</td>
<td width="50%">

### 📝 自動で文字起こし
OpenAI Whisper AIが、音声を自動的にテキストに変換。議事録作成に最適！

</td>
</tr>
<tr>
<td width="50%">

### 🔄 自動アップデート
新しいバージョンが出たら、アプリが自動的にお知らせ＆更新。

</td>
<td width="50%">

### 🎯 簡単操作
URLを貼り付けて「開始」ボタンを押すだけ。プログラミング知識不要！

</td>
</tr>
</table>

---

## 📥 ダウンロード方法

### ステップ 1: ファイルをダウンロード

**最新版をダウンロード** 👉 [リリースページ](https://github.com/waqprime/tool-instagram-live-transcription/releases/latest)

| OS | ダウンロードファイル | サイズ |
|:---:|:---|:---:|
| 🍎 **macOS** | `Instagram Live Transcription-1.0.0-arm64.dmg` | ~90MB |
| 🪟 **Windows** | `Instagram Live Transcription Setup 1.0.0.exe` | ~90MB |

**動作環境:**
- macOS 10.15 (Catalina) 以降
- Windows 10 / 11

---

### ステップ 2: インストール

#### 🍎 macOS の場合

1. ダウンロードした `.dmg` ファイルをダブルクリック
2. 表示されたウィンドウで、アプリを「Applications」フォルダにドラッグ
3. Launchpad または Finder から「Instagram Live Transcription」を起動

**⚠️ 初回起動時に「開発元を確認できません」と表示される場合:**

<details>
<summary>👉 解決方法を見る</summary>

1. アプリを**右クリック**（または Control + クリック）
2. メニューから「**開く**」を選択
3. 確認ダイアログで「**開く**」をクリック

これで次回から通常通り起動できます。

</details>

---

#### 🪟 Windows の場合

1. ダウンロードした `.exe` ファイルをダブルクリック
2. インストーラーの指示に従ってインストール
3. デスクトップまたはスタートメニューから起動

**⚠️「WindowsによってPCが保護されました」と表示される場合:**

<details>
<summary>👉 解決方法を見る</summary>

1. 「**詳細情報**」をクリック
2. 「**実行**」ボタンをクリック

これは署名されていないアプリの標準的な警告です。安全なアプリですのでご安心ください。

</details>

---

## 🚀 使い方（簡単3ステップ）

### 📹 ステップ 1: Instagram URLをコピー

1. Instagram アプリまたはブラウザで、文字起こししたい動画を開く
2. 「**シェア**」→「**リンクをコピー**」

例: `https://www.instagram.com/reel/ABC123xyz/`

---

### 🎬 ステップ 2: アプリに貼り付け

<table>
<tr>
<td width="60%">

1. アプリを起動
2. **URLを入力**欄に、コピーしたリンクを貼り付け
3. **保存先フォルダ**を選択（デフォルトは `output`）
4. **言語**を選択（日本語 / 英語 / 自動検出）
5. **Whisperモデル**を選択（迷ったら「Base」でOK）

</td>
<td width="40%">

![使い方イメージ](https://via.placeholder.com/300x400/0f1729/ffffff?text=%E3%82%A2%E3%83%97%E3%83%AA%E7%94%BB%E9%9D%A2%E3%82%A4%E3%83%A1%E3%83%BC%E3%82%B8)

</td>
</tr>
</table>

---

### ⚡ ステップ 3: 処理開始！

「**処理開始**」ボタンをクリック

アプリが自動的に以下を実行します：

```
1. 📥 動画をダウンロード
   ↓
2. 🎵 MP3音声を抽出
   ↓
3. 📝 AIで文字起こし
   ↓
4. ✅ 完了！
```

**処理時間の目安:**
- 5分の動画 → 約2〜3分
- 30分の動画 → 約10〜15分

---

## 🎯 Whisperモデルの選び方

処理速度と精度のバランスで選びます：

| モデル | 精度 | 速度 | こんな人におすすめ |
|:---:|:---:|:---:|:---|
| **Tiny** | ★☆☆☆☆ | ★★★★★ | とにかく速く試したい |
| **Base** | ★★☆☆☆ | ★★★★☆ | **初心者におすすめ！**バランス型 |
| **Small** | ★★★☆☆ | ★★★☆☆ | 精度重視で、ある程度速くしたい |
| **Medium** | ★★★★☆ | ★★☆☆☆ | 高精度が必要（処理時間長め） |
| **Large** | ★★★★★ | ★☆☆☆☆ | 最高精度（要高性能PC・時間かかる） |

💡 **迷ったら「Base」を選びましょう！**

---

## 📂 ファイルの保存場所

選択した保存先フォルダに、以下のように整理されて保存されます：

```
📁 output/
  ├── 📁 video_1_2025-01-15T10-30-45/
  │   ├── 🎵 video_1.mp3              ← 音声ファイル
  │   └── 📄 video_1_transcript.txt   ← 文字起こし結果
  │
  └── 📁 video_2_2025-01-15T10-45-20/
      ├── 🎵 video_2.mp3
      └── 📄 video_2_transcript.txt
```

**完了後に「フォルダを開く」ボタンで、すぐに確認できます！**

---

## ❓ よくある質問（FAQ）

<details>
<summary><b>Q1: アプリは無料ですか？</b></summary>

**A:** はい、完全無料です。個人利用・商用利用ともに自由にご利用いただけます。

</details>

<details>
<summary><b>Q2: Instagram以外の動画も処理できますか？</b></summary>

**A:** 現在はInstagramのみ対応していますが、将来的に他のプラットフォームにも対応予定です。

</details>

<details>
<summary><b>Q3: インターネット接続は必要ですか？</b></summary>

**A:** はい、以下の場合に必要です：
- 動画のダウンロード時
- 初回起動時（Whisperモデルのダウンロード）
- アップデートの確認時

処理自体（文字起こし）はオフラインで実行されます。

</details>

<details>
<summary><b>Q4: どのくらい時間がかかりますか？</b></summary>

**A:** 動画の長さとWhisperモデルによります：

| 動画の長さ | Base モデル | Large モデル |
|:---:|:---:|:---:|
| 5分 | 約2〜3分 | 約5〜8分 |
| 30分 | 約10〜15分 | 約30〜45分 |
| 60分 | 約20〜30分 | 約1〜1.5時間 |

</details>

<details>
<summary><b>Q5: 処理中に「モデルをダウンロード中」と表示されます</b></summary>

**A:** 初回起動時のみ、Whisperモデル（約200MB〜3GB）をダウンロードします。
次回からはダウンロード不要で、すぐに処理が始まります。

</details>

<details>
<summary><b>Q6: 複数の動画を一度に処理できますか？</b></summary>

**A:** はい！「URLを追加」ボタンで、複数のURLを入力できます。
順番に自動処理されます。

</details>

<details>
<summary><b>Q7: 文字起こしの精度を上げるには？</b></summary>

**A:** 以下の方法があります：
1. より大きなWhisperモデル（Small, Medium, Large）を選択
2. 音声がクリアな動画を選ぶ
3. 言語設定を正確に（日本語の場合は「Japanese」）

</details>

<details>
<summary><b>Q8: 自動アップデートを無効にできますか？</b></summary>

**A:** 現在は自動でチェックされますが、更新は任意です。
「今すぐインストール」をキャンセルすれば、現在のバージョンを使い続けられます。

</details>

---

## 🔧 トラブルシューティング

### ❌ 「ダウンロードに失敗しました」

**原因:**
- Instagram動画が非公開または削除されている
- ネットワーク接続の問題

**解決方法:**
1. URLが正しいか確認
2. 動画が公開されているか確認
3. インターネット接続を確認

---

### ❌ 「音声抽出に失敗しました」

**原因:** ffmpegがインストールされていない

**解決方法（macOS）:**
```bash
brew install ffmpeg
```

**解決方法（Windows）:**
1. [ffmpeg公式サイト](https://ffmpeg.org/download.html) からダウンロード
2. インストールしてPATHに追加

---

### ❌ 処理が途中で止まる

**考えられる原因:**
- PCのメモリ不足
- Whisperモデルが大きすぎる

**解決方法:**
1. 他のアプリを閉じてメモリを解放
2. より小さいモデル（Tiny, Base）を試す
3. アプリを再起動

---

### ❌ macOSで「開発元を確認できません」

**解決方法:**
1. アプリを**右クリック**
2. 「**開く**」を選択
3. 確認ダイアログで「**開く**」をクリック

---

### ❌ Windowsで「WindowsによってPCが保護されました」

**解決方法:**
1. 「**詳細情報**」をクリック
2. 「**実行**」をクリック

---

## 🔄 自動アップデート機能

アプリは起動時に自動的に新しいバージョンをチェックします。

**アップデートの流れ:**
1. 🔍 起動時に最新版をチェック
2. 📥 新バージョンがあればバックグラウンドでダウンロード
3. 🔔 ダウンロード完了後、通知ダイアログを表示
4. ✅ 「今すぐインストール」→ 自動的に再起動＆更新

---

## 🛡️ プライバシーとセキュリティ

- ✅ すべての処理はあなたのPC上で実行されます
- ✅ 動画や音声ファイルは外部サーバーに送信されません
- ✅ 個人情報を収集しません
- ✅ オープンソース - コードはすべてGitHubで公開

---

## 📄 ライセンス

MIT License - 個人利用・商用利用ともに自由にご利用いただけます。

---

## 🤝 フィードバック・バグ報告

問題や要望があれば、お気軽に[Issue](https://github.com/waqprime/tool-instagram-live-transcription/issues)を作成してください！

---

## 🏗️ 技術スタック

<details>
<summary>開発者向け情報</summary>

### フロントエンド
- Electron
- HTML/CSS/JavaScript（Liquid Glass UI）
- electron-updater

### バックエンド
- Python 3.13
- yt-dlp
- ffmpeg
- OpenAI Whisper

### ビルド & デプロイ
- electron-builder
- GitHub Actions（自動ビルド）
- GitHub Releases（配布）

### 開発モードで起動
```bash
cd electron-app
npm install
npm start
```

詳しくは [CLAUDE.md](CLAUDE.md) と `electron-app/RELEASE_GUIDE.md` を参照。

</details>

---

## 🙏 謝辞

このプロジェクトは以下のオープンソースプロジェクトを使用しています：

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - Instagram動画ダウンロード
- [OpenAI Whisper](https://github.com/openai/whisper) - 音声認識エンジン
- [Electron](https://www.electronjs.org/) - クロスプラットフォームフレームワーク
- [ffmpeg](https://ffmpeg.org/) - 音声処理

---

<div align="center">

**⭐ このプロジェクトが役に立ったら、ぜひスターをお願いします！ ⭐**

Made with ❤️ by [waqprime](https://github.com/waqprime)

</div>
