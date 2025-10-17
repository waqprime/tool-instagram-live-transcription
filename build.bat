@echo off
chcp 65001 > nul
echo ============================================================
echo Instagram Transcriber ビルドスクリプト
echo ============================================================
echo.

echo [1/3] 古いビルドファイルを削除中...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
echo 完了

echo.
echo [2/3] PyInstallerでビルド中...
pyinstaller instagram-transcriber.spec
if errorlevel 1 (
    echo.
    echo [ERROR] ビルドに失敗しました
    pause
    exit /b 1
)

echo.
echo [3/3] 実行ファイルを確認中...
if exist dist\instagram-transcriber.exe (
    echo.
    echo ============================================================
    echo ビルド成功！
    echo ============================================================
    echo 実行ファイル: dist\instagram-transcriber.exe
    echo.
) else (
    echo.
    echo [ERROR] 実行ファイルが生成されませんでした
    pause
    exit /b 1
)

pause
