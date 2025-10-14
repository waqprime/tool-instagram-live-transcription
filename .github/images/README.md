# スクリーンショット配置ガイド

このディレクトリには、README.mdで使用するスクリーンショットを配置します。

## 必要なスクリーンショット

### 1. `app-main.png` (必須)
- **内容**: アプリのメイン画面
- **推奨サイズ**: 1200x800px
- **説明**: URLを入力する画面、設定オプションが見える状態

### 2. `app-processing.png` (推奨)
- **内容**: 処理中の画面
- **推奨サイズ**: 1200x800px
- **説明**: プログレスバーと進捗状況が表示されている状態

### 3. `app-complete.png` (推奨)
- **内容**: 処理完了画面
- **推奨サイズ**: 1200x800px
- **説明**: 完了メッセージと「フォルダを開く」ボタンが表示されている状態

### 4. `output-folder.png` (オプション)
- **内容**: 出力フォルダの中身
- **推奨サイズ**: 800x600px
- **説明**: MP3ファイルと文字起こしファイルが整理されている状態

## スクリーンショットの撮り方

### macOS
1. アプリを起動
2. `Command + Shift + 4` → `Space` → ウィンドウをクリック
3. デスクトップに保存されたファイルを、このフォルダに移動

### Windows
1. アプリを起動
2. `Alt + PrintScreen`（アクティブウィンドウのみキャプチャ）
3. ペイントに貼り付けて保存
4. このフォルダに移動

## ファイル名ルール

- すべて小文字
- ハイフンで区切る
- PNG形式推奨（透明背景に対応）

例: `app-main.png`, `app-processing.png`

## README.mdでの参照方法

```markdown
![メイン画面](.github/images/app-main.png)
```

または、中央寄せで表示：

```markdown
<div align="center">
  <img src=".github/images/app-main.png" width="800" alt="メイン画面">
</div>
```

## 画像の最適化（推奨）

大きな画像はリポジトリサイズを増やすため、以下のツールで圧縮を推奨：

- **macOS**: ImageOptim (https://imageoptim.com/)
- **Windows**: TinyPNG (https://tinypng.com/)
- **オンライン**: Squoosh (https://squoosh.app/)

目標: 各画像100KB以下
