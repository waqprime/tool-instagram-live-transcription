# プライベートリポジトリで自動アップデートを使う方法

## 🔒 セットアップ手順

### 1. GitHubアクセストークンを作成

1. GitHub → 右上のアイコン → **Settings**
2. 左下の **Developer settings**
3. **Personal access tokens** → **Tokens (classic)**
4. **Generate new token** → **Generate new token (classic)**
5. Note: `electron-builder-private-repo`
6. 権限を選択：
   - ✅ **repo** (Full control of private repositories)
7. **Generate token** をクリック
8. **トークンをコピー**（ghp_xxxxxxxxxx）

⚠️ **重要**: このトークンは二度と表示されないので、必ずコピーしてください！

### 2. 環境変数に設定

#### macOS / Linux:

```bash
# ホームディレクトリの設定ファイルを編集
nano ~/.zshrc
# または
nano ~/.bash_profile

# 以下を追加（トークンを置き換える）
export GH_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxx"

# 保存して反映
source ~/.zshrc
```

#### Windows:

1. スタートメニュー → 「環境変数」で検索
2. 「システム環境変数の編集」
3. 「環境変数」ボタンをクリック
4. 「新規」をクリック
5. 変数名: `GH_TOKEN`
6. 変数値: `ghp_xxxxxxxxxxxxxxxxxxxx`
7. OK → OK → OK

### 3. package.jsonの設定（すでに完了）

`package.json`の設定はそのままでOK：

```json
"publish": [
  {
    "provider": "github",
    "owner": "YOUR_GITHUB_USERNAME",
    "repo": "instagram-live-transcription"
  }
]
```

### 4. ビルド時にトークンを使用

```bash
cd electron-app

# 環境変数が設定されていることを確認
echo $GH_TOKEN  # macOS/Linux
echo %GH_TOKEN%  # Windows

# ビルド（自動的にGH_TOKENを使います）
npm run build:mac
```

### 5. GitHubでプライベートリリースを作成

1. GitHubリポジトリ → **Releases** → **Create a new release**
2. タグを選択（例: v1.0.1）
3. **ビルドファイルをアップロード**：
   - `dist/Instagram Live Transcription-1.0.1-arm64.dmg`
4. **Publish release**

⚠️ リリースは**Draft（下書き）にせず、Published状態**にしてください

## 🎯 main.jsでトークンを設定する方法（オプション）

もし環境変数ではなく、コード内でトークンを設定したい場合：

```javascript
// main.js の checkForUpdates() 関数内
function checkForUpdates() {
  autoUpdater.setFeedURL({
    provider: 'github',
    owner: 'YOUR_GITHUB_USERNAME',
    repo: 'instagram-live-transcription',
    private: true,
    token: process.env.GH_TOKEN || 'ghp_xxxxxxxxxxxxxxxxxxxx'
  });

  autoUpdater.checkForUpdatesAndNotify();
  // ...
}
```

⚠️ **セキュリティ上の注意**：
トークンをコードに直接書くのは避けてください。必ず環境変数を使いましょう！

## 🚀 リリース手順（プライベートリポジトリ）

```bash
# 1. バージョンアップ
cd electron-app
npm version patch

# 2. ビルド（GH_TOKENが自動的に使われます）
npm run build:mac

# 3. Gitにプッシュ
git push --tags

# 4. GitHubでリリースを作成
# - ビルドファイル（dmg/exe）をアップロード
# - 必ずPublishedにする（Draftはダメ）
```

## ✅ 動作確認

1. 古いバージョンのアプリをインストール
2. 新しいバージョンをリリース
3. 古いバージョンのアプリを起動
4. 自動的にアップデート通知が表示されるはず

## 🔧 トラブルシューティング

### アップデートが見つからない

✅ **環境変数の確認**
```bash
echo $GH_TOKEN  # macOS/Linux
```

✅ **GitHubリリースの確認**
- リリースが**Published**になっているか
- dmg/exeファイルがアップロードされているか

✅ **package.jsonの確認**
- `owner`と`repo`が正しいか

### ビルドエラー

```
Error: GitHub token not set
```

→ 環境変数`GH_TOKEN`が設定されていません。上記の手順2を確認してください。

## 📊 公開リポジトリ vs プライベートリポジトリ

| 項目 | 公開リポジトリ | プライベートリポジトリ |
|------|---------------|---------------------|
| トークン | 不要 | **必要** |
| セットアップ | 簡単 | やや複雑 |
| セキュリティ | 誰でもダウンロード可能 | アクセス制限あり |
| 推奨用途 | オープンソース | 社内ツール・有料アプリ |

## 💡 おすすめ

**個人プロジェクト・無料アプリ** → 公開リポジトリがおすすめ（設定が簡単）

**社内ツール・有料アプリ・機密情報あり** → プライベートリポジトリ

---

これでプライベートリポジトリでも自動アップデートが使えます！🎉
