#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UTAGE動画URL抽出モジュール
UTAGEページからHLS(.m3u8)動画URLを抽出
"""

import re
import sys
from typing import Optional
from urllib.parse import urljoin, urlparse

# Windows環境での文字化け対策
if sys.platform == 'win32':
    import os
    os.environ['PYTHONIOENCODING'] = 'utf-8'


class UtageExtractor:
    """UTAGEページから動画URLを抽出するクラス"""

    def __init__(self):
        pass

    def is_utage_url(self, url: str) -> bool:
        """
        URLがUTAGEページかどうかを判定
        HTMLの内容をチェックしてUTAGE特有の要素があるか確認

        Args:
            url: チェックするURL

        Returns:
            UTAGEページの場合True
        """
        # パターン1: 公式UTAGEドメイン
        if re.search(r'\.utage-system\.com', url):
            return True

        # パターン2: HTMLの内容からUTAGEか判定
        try:
            import requests

            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            html = response.text.lower()

            # UTAGE特有の文字列をチェック
            utage_indicators = [
                'utagesystem',
                'utage-system',
                'wasabisys.com/utagesystem'
            ]

            # 2つ以上の指標が見つかればUTAGEと判定
            matches = sum(1 for indicator in utage_indicators if indicator in html)

            if matches >= 2:
                return True

        except:
            pass

        return False

    def extract_video_url(self, page_url: str) -> Optional[str]:
        """
        UTAGEページから動画のm3u8 URLを抽出
        Seleniumを使用してブラウザを自動化し、ネットワークリクエストから動画URLを取得

        Args:
            page_url: UTAGEページのURL

        Returns:
            video.m3u8のURL、失敗時はNone
        """
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.common.exceptions import TimeoutException
            from webdriver_manager.chrome import ChromeDriverManager
            import time

            print(f"[INFO] UTAGEページにアクセス (ブラウザ自動化): {page_url}")

            # Chromeオプションを設定
            chrome_options = Options()
            chrome_options.add_argument('--headless')  # ヘッドレスモード
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

            # ネットワークログを有効化
            chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

            # WebDriverを起動（webdriver-managerで自動的にChromeDriverをインストール）
            print("[INFO] ChromeDriverを準備中...")
            service = Service(ChromeDriverManager().install())
            print("[INFO] ブラウザを起動中...")
            driver = webdriver.Chrome(service=service, options=chrome_options)

            try:
                # ページにアクセス
                driver.get(page_url)
                print("[INFO] ページ読み込み中...")

                # 動画要素が読み込まれるまで待機（最大30秒）
                try:
                    WebDriverWait(driver, 30).until(
                        EC.presence_of_element_located((By.TAG_NAME, "video"))
                    )
                    print("[INFO] 動画要素を検出")
                except TimeoutException:
                    print("[WARNING] 動画要素が見つかりませんでした")

                # 少し待機して動画リクエストが発生するのを待つ
                time.sleep(5)

                # ネットワークログから.m3u8 URLを抽出
                logs = driver.get_log('performance')
                video_url = None

                for log in logs:
                    import json
                    message = json.loads(log['message'])

                    if message['message']['method'] == 'Network.requestWillBeSent':
                        url = message['message']['params']['request']['url']

                        # video.m3u8を含むURLを探す
                        if 'video.m3u8' in url or '.m3u8' in url:
                            video_url = url
                            print(f"[OK] 動画URL発見: {video_url}")
                            break

                if not video_url:
                    # ページソースから直接検索（フォールバック）
                    print("[INFO] ネットワークログから見つからず、ページソースを検索中...")
                    page_source = driver.page_source

                    # .m3u8 URLのパターンを検索
                    m3u8_pattern = r'https://[^\s"\']+\.m3u8'
                    matches = re.findall(m3u8_pattern, page_source)

                    if matches:
                        video_url = matches[0]
                        print(f"[OK] ページソースから動画URL発見: {video_url}")
                    else:
                        # Wasabi S3のベースURLから構築を試みる
                        wasabi_pattern = r'https://s3\.ap-northeast-1\.wasabisys\.com/utagesystem-video/([^/\s"\']+)/([^/\s"\']+)'
                        matches = re.findall(wasabi_pattern, page_source)

                        if matches:
                            folder1, folder2 = matches[0]
                            video_url = f"https://s3.ap-northeast-1.wasabisys.com/utagesystem-video/{folder1}/{folder2}/video.m3u8"
                            print(f"[INFO] S3パスから構築: {video_url}")

                return video_url

            finally:
                driver.quit()
                print("[INFO] ブラウザを終了")

        except ImportError as e:
            print(f"[ERROR] Seleniumがインストールされていません: {e}")
            print("[INFO] pip install selenium でインストールしてください")
            return None
        except Exception as e:
            print(f"[ERROR] 予期しないエラー: {e}")
            import traceback
            traceback.print_exc()
            return None


def main():
    """テスト用のメイン関数"""
    import argparse

    parser = argparse.ArgumentParser(description="UTAGE動画URL抽出ツール")
    parser.add_argument("url", help="UTAGEページのURL")

    args = parser.parse_args()

    extractor = UtageExtractor()

    if not extractor.is_utage_url(args.url):
        print("[WARNING] このURLはUTAGEページではない可能性があります")

    video_url = extractor.extract_video_url(args.url)

    if video_url:
        print(f"\n動画URL: {video_url}")
        print("\nyt-dlpでダウンロード:")
        print(f"yt-dlp '{video_url}'")
        return 0
    else:
        print("\n動画URLの抽出に失敗しました")
        return 1


if __name__ == "__main__":
    sys.exit(main())
