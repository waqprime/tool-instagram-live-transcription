# GitHubプッシュ手順

## 1. GitHubリポジトリを作成

1. GitHub.com にアクセス
2. 右上の「+」→「New repository」
3. リポジトリ名: `instagram-live-transcription`
4. 説明: `Instagram Live & Reel transcription app with Whisper AI - Electron desktop application`
5. **Public**を選択
6. 「Create repository」をクリック

## 2. package.jsonを更新

```bash
# electron-app/package.jsonを開いて、35行目を変更:
"owner": "YOUR_GITHUB_USERNAME"
↓
"owner": "あなたの実際のGitHubユーザー名"
```

## 3. README.mdのリンクを更新

```bash
# README.mdを開いて、17行目を変更:
https://github.com/YOUR_USERNAME/instagram-live-transcription
↓
https://github.com/あなたのユーザー名/instagram-live-transcription
```

## 4. Gitの初期化とプッシュ

```bash
cd "/Users/saorin/Desktop/ai/インスタライブ音声"

# Gitの初期化（まだの場合）
git init

# ファイルをステージング
git add .

# コミット
git commit -m "Initial commit - Instagram Live Transcription app with auto-update"

# リモートリポジトリを追加
git remote add origin https://github.com/YOUR_USERNAME/instagram-live-transcription.git

# メインブランチ名を設定
git branch -M main

# プッシュ
git push -u origin main
```

## 5. リポジトリの設定（推奨）

GitHubリポジトリページで：

### 基本設定
- **About**を編集:
  - Description: `🎵 Instagram Live & Reel transcription with Whisper AI - Beautiful Electron desktop app with auto-update`
  - Website: リリース後に追加
  - Topics: `electron`, `whisper`, `instagram`, `transcription`, `openai`, `javascript`, `python`, `desktop-app`

### セキュリティ
- **Settings** → **Security** → **Dependabot**
  - ✅ Dependabot alerts を有効化
  - ✅ Dependabot security updates を有効化

### ブランチ保護（オプション）
- **Settings** → **Branches** → **Add rule**
  - Branch name pattern: `main`
  - ✅ Require pull request reviews before merging

### Actions（自動ビルド用・オプション）
- **Settings** → **Actions** → **General**
  - ✅ Allow all actions and reusable workflows

## 6. 最初のリリースを作成（オプション）

```bash
cd electron-app

# バージョンを1.0.0に設定（すでに設定済み）
npm version 1.0.0

# ビルド
npm run build:mac

# GitHubでリリースを作成
# 1. 「Releases」→「Create a new release」
# 2. Tag: v1.0.0
# 3. Title: v1.0.0 - Initial Release
# 4. Description:
```

```markdown
## ✨ 初回リリース

Instagram Live Transcriptionの最初のバージョンです！

### 🎯 主な機能
- Instagram Reel/Live動画のダウンロード
- OpenAI Whisper AIによる自動文字起こし
- 美しいLiquid GlassデザインのUI
- リアルタイム進捗表示
- 複数のWhisperモデル選択
- URL毎のフォルダ整理
- **自動アップデート機能**

### 📥 ダウンロード
macOS版とWindows版をダウンロードできます。

### 📝 使い方
1. アプリをインストール
2. Instagram URLを入力
3. 保存先を選択
4. 処理開始！

### ⚠️ 初回起動時の注意
- **macOS**: 「開発元を確認できません」→ 右クリック→「開く」
- **Windows**: Windows Defender警告→「詳細情報」→「実行」
```

```bash
# 5. ビルドファイルをアップロード:
#    - Instagram Live Transcription-1.0.0-arm64.dmg
# 6. 「Publish release」をクリック
```

## 7. プッシュ後のチェックリスト

- [ ] リポジトリが正しく表示される
- [ ] README.mdが正しく表示される
- [ ] ファイル数が適切（機密情報が含まれていない）
- [ ] .gitignoreが機能している（venv/, node_modules/が含まれていない）
- [ ] リンクが正しく動作する
- [ ] トピックタグが設定されている

## 8. SNSでシェア（オプション）

```markdown
🎉 新しいElectronアプリをリリースしました！

Instagram Live Transcription
Instagram動画を自動で文字起こしするデスクトップアプリです

✨ 特徴:
- OpenAI Whisper AI
- 美しいUI
- 自動アップデート
- クロスプラットフォーム

https://github.com/YOUR_USERNAME/instagram-live-transcription

#Electron #Whisper #OpenAI #JavaScript #Python
```

---

**これで完了です！** 🎉

あとは定期的にコミット＆プッシュして、リリースを作成するだけです。
