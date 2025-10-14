# リリースガイド - 自動アップデート対応

## 📋 初回セットアップ

### 1. GitHubリポジトリの作成

```bash
# プロジェクトルートで実行
cd "/Users/saorin/Desktop/ai/インスタライブ音声"

# Gitリポジトリの初期化（まだの場合）
git init
git add .
git commit -m "Initial commit"

# GitHubリポジトリと接続
git remote add origin https://github.com/YOUR_USERNAME/instagram-live-transcription.git
git branch -M main
git push -u origin main
```

### 2. package.jsonのGitHubユーザー名を変更

`electron-app/package.json`の32-37行目：
```json
"publish": [
  {
    "provider": "github",
    "owner": "YOUR_GITHUB_USERNAME",  ← ここを変更
    "repo": "instagram-live-transcription"
  }
]
```

## 🔄 新バージョンのリリース手順

### ステップ1: バージョンの更新

```bash
cd electron-app

# パッチバージョンアップ (1.0.0 → 1.0.1)
npm version patch

# マイナーバージョンアップ (1.0.0 → 1.1.0)
npm version minor

# メジャーバージョンアップ (1.0.0 → 2.0.0)
npm version major
```

### ステップ2: ビルド

```bash
# Macのみビルド
npm run build:mac

# Windowsのみビルド（Windowsマシンで実行）
npm run build:win

# 両方ビルド
npm run build
```

ビルドが完了すると、`dist/`フォルダに以下のファイルが生成されます：
- Mac: `Instagram Live Transcription-1.0.1-arm64.dmg`
- Windows: `Instagram Live Transcription Setup 1.0.1.exe`

### ステップ3: GitHubにタグをプッシュ

```bash
# 変更をコミット
git add .
git commit -m "Release version 1.0.1"

# タグをプッシュ
git push
git push --tags
```

### ステップ4: GitHubでリリースを作成

1. GitHubのリポジトリページを開く
2. 右側の「Releases」をクリック
3. 「Create a new release」をクリック
4. タグを選択（例: `v1.0.1`）
5. リリースタイトルとノートを記入：

```markdown
## 新機能
- ✨ Whisperモデル選択機能を追加
- 📁 URL毎にフォルダを自動生成

## 改善
- ⏱️ リアルタイム進捗表示を改善
- 🎯 大きなファイルの警告機能を追加

## バグ修正
- 🐛 ウィンドウのドラッグ問題を修正
```

6. **ビルドファイルをアップロード**（重要！）：
   - `dist/Instagram Live Transcription-1.0.1-arm64.dmg` (Mac)
   - `dist/Instagram Live Transcription Setup 1.0.1.exe` (Windows)

7. 「Publish release」をクリック

## 🎯 自動アップデートの仕組み

1. **ユーザーがアプリを起動**
   → アプリが自動的にGitHubの最新リリースをチェック

2. **新バージョンが見つかった場合**
   → バックグラウンドで自動ダウンロード
   → 進捗バーで表示

3. **ダウンロード完了**
   → ユーザーに確認ダイアログ表示
   → 「今すぐインストール」→ 再起動してアップデート
   → 「キャンセル」→ 次回起動時にインストール

## 🧪 テスト方法

### 1. 現在のバージョンをインストール
```bash
cd electron-app
npm run build:mac
# distフォルダのdmgをインストール
```

### 2. バージョンを上げて新しいビルドを作成
```bash
npm version patch
npm run build:mac
```

### 3. GitHubリリースを作成
上記の手順でリリースを作成

### 4. 古いバージョンのアプリを起動
自動的にアップデート通知が表示されるはず

## ⚙️ GitHub Actions で自動ビルド（オプション）

`.github/workflows/release.yml`を作成すると、タグをプッシュしたら自動的にビルド＆リリースできます：

```yaml
name: Build and Release

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [macos-latest, windows-latest]

    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install dependencies
        run: |
          cd electron-app
          npm install

      - name: Build
        run: |
          cd electron-app
          npm run build
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Release
        uses: softprops/action-gh-release@v1
        with:
          files: electron-app/dist/*
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

この設定を使うと：
```bash
npm version patch
git push --tags
```
だけで、自動的にビルド＆リリースが完了します！

## 📝 注意事項

⚠️ **初回インストール**
自動アップデートは既にアプリをインストール済みのユーザーのみが対象です。新規ユーザーは手動でdmg/exeをダウンロードする必要があります。

⚠️ **開発モード**
`npm start`や`--dev`フラグで起動した場合、自動アップデートチェックは無効になります。

⚠️ **コード署名**
本番環境では、macOSのGatekeeper、WindowsのSmartScreenを通過するためにコード署名が必要です。

⚠️ **プライベートリポジトリ**
プライベートリポジトリの場合、GitHubトークンの設定が必要です。

## 🎉 これで完成！

あとはコードを更新して、上記の手順でリリースするだけです。
ユーザーは自動的に最新版にアップデートされます！
