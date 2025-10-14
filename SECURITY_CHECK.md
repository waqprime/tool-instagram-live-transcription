# セキュリティチェックリスト - GitHubプッシュ前

## ✅ 完了した項目

### 1. 機密情報の除外
- [x] `.gitignore`を更新
  - `venv_new/` を追加
  - 環境変数ファイル (`.env`, `.env.*`) を追加
  - シークレットファイル (`*secret*`, `*token*`, `*.pem`, `*.key`) を追加

- [x] `link.txt`をクリーンアップ
  - 個人のInstagram URLを削除
  - サンプル形式に変更

- [x] `output/`ディレクトリを除外
  - `.gitignore`で除外済み
  - 大きなmp3ファイルがプッシュされない

### 2. ビルド成果物の除外
- [x] `dist/` - ビルド済みアプリケーション
- [x] `node_modules/` - Nodeパッケージ
- [x] `venv/`, `venv_new/` - Python仮想環境

### 3. プレースホルダーの設定
- [x] `package.json` - `YOUR_GITHUB_USERNAME`をプレースホルダーとして残す
- [x] `README.md` - GitHubユーザー名をプレースホルダーとして残す

### 4. ドキュメントの整備
- [x] `README.md` - Electronアプリ向けに更新
- [x] `RELEASE_GUIDE.md` - リリース手順を文書化
- [x] `PRIVATE_REPO_GUIDE.md` - プライベートリポジトリ用ガイド
- [x] `AUTO_UPDATE_GUIDE.md` - 自動アップデート実装ガイド

## 🔍 含まれていないもの（確認済み）

✅ APIキーやトークン
✅ パスワード
✅ 個人情報
✅ 環境変数ファイル
✅ 大きなバイナリファイル
✅ 一時ファイル

## ✅ 含まれているもの（公開OK）

- ソースコード (Python, JavaScript, HTML, CSS)
- 設定ファイル (`package.json`, `requirements.txt`)
- ドキュメント (`README.md`, ガイド類)
- サンプルファイル (`link.txt` - サンプルのみ)
- 開発補助ファイル (`.gitignore`, `CLAUDE.md`)

## 📋 プッシュ前の最終確認

```bash
# 1. .gitignoreが正しく機能しているか確認
git status

# 以下のファイル/フォルダが表示されないことを確認:
# - venv_new/
# - output/
# - node_modules/
# - dist/
# - *.mp3, *.mp4
# - .env*

# 2. 機密情報が含まれていないか確認
git diff

# 3. コミット前の最終チェック
git add .
git status

# 問題なければコミット
git commit -m "Initial public release"
```

## 🚨 絶対にプッシュしてはいけないもの

❌ GitHub Personal Access Token
❌ AWSキー、Azure キー
❌ データベースパスワード
❌ 個人のInstagram URL
❌ ユーザーデータ（mp3, 文字起こし結果）
❌ 大きなバイナリファイル (>100MB)

## ✅ 公開しても問題ないもの

✅ アプリケーションのソースコード
✅ 依存関係の定義 (package.json, requirements.txt)
✅ ドキュメント
✅ サンプル設定ファイル
✅ ビルドスクリプト
✅ 開発ガイドライン

## 🎯 次のステップ

リポジトリ作成後：
1. `package.json`の`YOUR_GITHUB_USERNAME`を実際のユーザー名に変更
2. `README.md`のGitHubリンクを更新
3. リポジトリの説明を追加
4. トピックタグを設定（electron, whisper, instagram, transcription）

## 🔒 リポジトリ設定（公開後）

推奨設定：
- **Branch protection**: mainブランチを保護
- **Security**: Dependabotを有効化
- **Actions**: GitHub Actionsを有効化（自動ビルド用）
- **Issues**: イシュートラッカーを有効化
- **Discussions**: コミュニティ機能を有効化（オプション）

---

**結論**: ✅ **このコードベースは公開リポジトリにプッシュしても安全です！**
