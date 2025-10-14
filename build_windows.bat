@echo off
REM Windows用ビルドスクリプト

echo ========================================
echo Windows版アプリケーションのビルド
echo ========================================

REM 仮想環境の確認
if not exist venv (
    echo 仮想環境が見つかりません。作成します...
    python -m venv venv
)

REM 仮想環境をアクティベート
call venv\Scripts\activate.bat

REM 依存関係のインストール
echo 依存関係をインストール中...
pip install -r requirements.txt

REM PyInstallerでビルド
echo アプリケーションをビルド中...
pyinstaller --name=InstagramLiveTranscriber ^
    --windowed ^
    --onefile ^
    --add-data="downloader.py;." ^
    --add-data="audio_converter.py;." ^
    --add-data="transcriber.py;." ^
    --icon=app_icon.ico ^
    app.py

echo.
echo ✓ ビルド完了！
echo アプリケーションは dist\InstagramLiveTranscriber.exe にあります
echo.
echo 配布方法:
echo 1. dist\InstagramLiveTranscriber.exe を zip で圧縮
echo 2. ユーザーに配布
echo 3. Windows Defenderの警告が出る場合は「詳細情報」→「実行」をクリック
pause
