# Windows版 ビルド・使用ガイド

## 修正内容

このバージョンでは、Windows環境での以下の問題を修正しました:

### 1. 文字化け問題の解決
- **問題**: WindowsのデフォルトエンコーディングCP932により日本語が文字化け
- **修正**: すべてのPythonファイルでUTF-8エンコーディングを強制設定
- **実装場所**:
  - `main.py:15-30`
  - `transcriber.py:15-26`
  - `audio_converter.py:14-25`
  - `downloader.py:14-25`

### 2. コンソール出力の問題解決
- **問題**: PyInstallerビルド時に`console=False`でエラーが表示されない
- **修正**: `instagram-transcriber.spec:52`を`console=True`に変更
- **効果**: 実行時にコンソールウィンドウが表示され、進捗とエラーが確認可能

### 3. subprocess呼び出しの安定化
- **問題**: ffmpeg/yt-dlpの出力がエンコーディングエラーで失敗
- **修正**: すべての`subprocess.run()`に`encoding='utf-8', errors='replace'`を追加
- **対象**:
  - `audio_converter.py:40-46, 99-105, 143-149`
  - `downloader.py:79-85`

## ビルド方法

### 前提条件
```bash
# Python 3.8以上
python --version

# 依存パッケージのインストール
pip install -r requirements.txt
```

### ビルド実行
```bash
# 方法1: バッチファイルを使用（推奨）
build.bat

# 方法2: 直接PyInstallerを実行
pyinstaller instagram-transcriber.spec
```

### ビルド成功後
実行ファイルは `dist\instagram-transcriber.exe` に生成されます。

## 使用方法

### 1. 基本的な使い方
```bash
# link.txtのURLを一括処理
instagram-transcriber.exe

# 単一URLを処理
instagram-transcriber.exe --url "https://www.instagram.com/reel/..."
```

### 2. モデル指定
```bash
# 高精度モデルを使用
instagram-transcriber.exe --model medium

# 高速モデルを使用
instagram-transcriber.exe --model tiny
```

### 3. 出力ディレクトリ指定
```bash
instagram-transcriber.exe --output-dir "C:\Users\YourName\Videos\transcripts"
```

## エンコーディングテスト

修正が正しく動作しているか確認するには:

```bash
# テストスクリプトを実行
python test_encoding.py
```

以下が正しく表示されれば成功:
- `エンコーディングテスト`
- `stdout エンコーディング: utf-8`
- 日本語テキストが文字化けせず表示される

## トラブルシューティング

### 文字化けが発生する場合

1. **コマンドプロンプトの設定を確認**
   ```bash
   # UTF-8に変更
   chcp 65001
   ```

2. **環境変数を設定**
   ```bash
   set PYTHONIOENCODING=utf-8
   ```

3. **PowerShellを使用する場合**
   ```powershell
   # UTF-8に設定
   [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
   ```

### ffmpegエラーが発生する場合

Whisperの文字起こしで`ffmpeg`エラーが発生する場合:

1. ffmpegをインストール: https://ffmpeg.org/download.html
2. システムPATHに追加
3. または、アプリと同じフォルダに`ffmpeg.exe`を配置

### メモリ不足エラー

大きなモデル（medium/large）使用時にメモリ不足が発生する場合:
- より小さなモデル（base/small）を使用
- 他のアプリケーションを終了してメモリを確保

## 技術仕様

### エンコーディング処理の詳細

すべてのモジュールで以下の処理を実行:

```python
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        if hasattr(sys.stdout, 'buffer') and sys.stdout.encoding.lower() != 'utf-8':
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        if hasattr(sys.stderr, 'buffer') and sys.stderr.encoding.lower() != 'utf-8':
            import io
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except (AttributeError, OSError):
        pass
```

### 主な改善点

1. **`PYTHONIOENCODING`環境変数**: Pythonの全I/O操作でUTF-8を使用
2. **TextIOWrapperのラップ**: stdoutとstderrをUTF-8に強制変換
3. **line_buffering=True**: リアルタイムでログを表示
4. **errors='replace'**: デコードエラー時に文字を置換（クラッシュ防止）
5. **例外処理**: PyInstallerやリダイレクト環境での互換性を確保

## 配布方法

### 単体実行ファイルとして配布

`dist\instagram-transcriber.exe`を配布すればOK（依存関係は全て含まれています）

### 注意事項

- **ffmpeg**: 別途インストールが必要（またはexeと同梱）
- **Whisperモデル**: 初回実行時に自動ダウンロード（インターネット接続が必要）
- **ファイルサイズ**: 実行ファイルは大きくなります（約200-300MB）

## ライセンス

このプロジェクトは元のライセンスに従います。
