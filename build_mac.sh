#!/bin/bash
# macOS用ビルドスクリプト

echo "================================"
echo "macOS版アプリケーションのビルド"
echo "================================"

# 仮想環境の確認
if [ ! -d "venv" ]; then
    echo "仮想環境が見つかりません。作成します..."
    python3 -m venv venv
fi

# 仮想環境をアクティベート
source venv/bin/activate

# 依存関係のインストール
echo "依存関係をインストール中..."
pip install -r requirements.txt

# PyInstallerでビルド
echo "アプリケーションをビルド中..."
pyinstaller --name="InstagramLiveTranscriber" \
    --windowed \
    --onefile \
    --add-data="downloader.py:." \
    --add-data="audio_converter.py:." \
    --add-data="transcriber.py:." \
    --icon=app_icon.icns \
    --osx-bundle-identifier=com.instagramlive.transcriber \
    --target-arch=universal2 \
    app.py

echo ""
echo "✓ ビルド完了！"
echo "アプリケーションは dist/InstagramLiveTranscriber.app にあります"
echo ""
echo "配布方法:"
echo "1. dist/InstagramLiveTranscriber.app を zip で圧縮"
echo "2. ユーザーに配布"
echo "3. 初回起動時に「開発元を確認できないため開けません」と表示される場合："
echo "   右クリック → 開く → 開く をクリック"
