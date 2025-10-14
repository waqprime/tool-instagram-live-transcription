# 自動アップデート機能の実装ガイド

## 概要

Electronアプリに自動アップデート機能を追加するには、`electron-updater`パッケージを使用します。
GitHubリリースと連携して、新しいバージョンを自動的にダウンロード・インストールできます。

## 実装手順

### 1. パッケージのインストール

```bash
cd electron-app
npm install electron-updater
```

### 2. package.jsonの設定

```json
{
  "version": "1.0.0",
  "build": {
    "publish": [
      {
        "provider": "github",
        "owner": "あなたのGitHubユーザー名",
        "repo": "リポジトリ名"
      }
    ]
  }
}
```

### 3. main.jsに自動アップデートコードを追加

```javascript
const { app, BrowserWindow } = require('electron');
const { autoUpdater } = require('electron-updater');

// アプリ起動時にアップデートをチェック
app.whenReady().then(() => {
  createWindow();

  // 開発環境では実行しない
  if (!isDev) {
    checkForUpdates();
  }
});

function checkForUpdates() {
  // アップデートチェック
  autoUpdater.checkForUpdatesAndNotify();

  // イベントリスナー
  autoUpdater.on('update-available', () => {
    console.log('アップデートが利用可能です');
    // ユーザーに通知
    mainWindow.webContents.send('update-available');
  });

  autoUpdater.on('update-downloaded', () => {
    console.log('アップデートのダウンロードが完了しました');
    // ユーザーに再起動を促す
    mainWindow.webContents.send('update-downloaded');
  });

  autoUpdater.on('error', (error) => {
    console.error('アップデートエラー:', error);
  });
}

// ユーザーがインストールを承認したら再起動
ipcMain.handle('install-update', () => {
  autoUpdater.quitAndInstall();
});
```

### 4. UIでアップデート通知を表示

renderer.jsに追加:

```javascript
// アップデート通知を受信
window.electronAPI.onUpdateAvailable(() => {
  updateProgress(null, 'アップデートをダウンロード中...', '新しいバージョンが利用可能です');
});

window.electronAPI.onUpdateDownloaded(() => {
  const userResponse = confirm('新しいバージョンがダウンロードされました。今すぐインストールしますか？');
  if (userResponse) {
    window.electronAPI.installUpdate();
  }
});
```

preload.jsに追加:

```javascript
contextBridge.exposeInMainWorld('electronAPI', {
  // 既存のAPI...
  onUpdateAvailable: (callback) => ipcRenderer.on('update-available', callback),
  onUpdateDownloaded: (callback) => ipcRenderer.on('update-downloaded', callback),
  installUpdate: () => ipcRenderer.invoke('install-update')
});
```

## GitHubリリースの作成手順

### 5. GitHubリポジトリの作成

1. GitHubで新しいリポジトリを作成
2. ローカルのコードをプッシュ

```bash
cd "/Users/saorin/Desktop/ai/インスタライブ音声"
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/yourusername/instagram-live-transcription.git
git push -u origin main
```

### 6. ビルドしてリリースを作成

```bash
cd electron-app

# バージョン番号を更新
npm version 1.0.1

# ビルド（Mac/Windows両方）
npm run build

# GitHubにタグをプッシュ
git push --tags
```

### 7. GitHub Releasesでリリースを公開

1. GitHubのリポジトリページで「Releases」をクリック
2. 「Create a new release」をクリック
3. タグを選択（例: v1.0.1）
4. リリースノートを記入
5. ビルドしたファイルをアップロード:
   - `dist/Instagram Live Transcription-1.0.1-arm64.dmg` (Mac)
   - `dist/Instagram Live Transcription Setup 1.0.1.exe` (Windows)
6. 「Publish release」をクリック

### 8. 自動ビルド（GitHub Actions - オプション）

`.github/workflows/build.yml`を作成:

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

      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: ${{ matrix.os }}-build
          path: electron-app/dist/*
```

## 更新の流れ

1. **新バージョンの開発**
   - コードを修正
   - `npm version patch` (1.0.0 → 1.0.1)
   - `npm version minor` (1.0.0 → 1.1.0)
   - `npm version major` (1.0.0 → 2.0.0)

2. **ビルドとリリース**
   - `npm run build`
   - GitHubでリリースを作成
   - ビルドファイルをアップロード

3. **ユーザー側**
   - アプリ起動時に自動的にアップデートをチェック
   - 新バージョンが見つかるとバックグラウンドでダウンロード
   - ダウンロード完了後、ユーザーに通知
   - ユーザーが承認すると再起動してインストール

## メリット

✅ **自動化**: ユーザーは手動でダウンロードする必要なし
✅ **安全**: 署名されたアップデートのみインストール
✅ **簡単**: GitHubリリースにファイルをアップロードするだけ
✅ **無料**: GitHubの機能を使うので追加コスト不要

## 注意点

⚠️ **コード署名**: 本番環境では、アプリに署名が必要
⚠️ **初回インストール**: 自動アップデートは既にインストール済みのユーザーのみ
⚠️ **ネットワーク**: ユーザーのインターネット接続が必要

## テスト方法

1. バージョン1.0.0をビルドしてインストール
2. コードを修正してバージョン1.0.1をビルド
3. GitHubにリリースを作成
4. バージョン1.0.0のアプリを起動
5. 自動的にアップデート通知が表示されることを確認
