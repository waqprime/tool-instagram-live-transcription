#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Voicy音声URL抽出モジュール
VoicyページからHLS音声URLを抽出（yt-dlpのVoicyエクストラクタが壊れているため独自実装）
"""

import re
import sys
import json
import uuid
from typing import Optional, Dict
from urllib.parse import urlparse

# Windows環境での文字化け対策
if sys.platform == 'win32':
    import os
    os.environ['PYTHONIOENCODING'] = 'utf-8'


FIREBASE_API_KEY = "AIzaSyC5Rg-sxiYu6ySD8V-f6Eljwll8gHvgUK4"
VOICY_PLAYER_API = "https://vmedia-player-api.voicy.jp/v1"


class VoicyExtractor:
    """Voicyページから音声URLを抽出するクラス"""

    def __init__(self):
        self._token = None
        self._uuid = str(uuid.uuid4())

    def is_voicy_url(self, url: str) -> bool:
        """URLがVoicyかどうかを判定"""
        return bool(re.match(r'https?://voicy\.jp/channel/\d+', url))

    def _parse_url(self, url: str) -> Optional[Dict[str, str]]:
        """VoicyのURLからchannel_idとvoice_idを抽出"""
        match = re.match(r'https?://voicy\.jp/channel/(?P<channel_id>\d+)(?:/(?P<voice_id>\d+))?', url)
        if match:
            return match.groupdict()
        return None

    def _get_firebase_token(self) -> Optional[str]:
        """Firebase匿名認証でトークンを取得"""
        if self._token:
            return self._token

        try:
            import requests
            response = requests.post(
                f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_API_KEY}",
                json={"returnSecureToken": True},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            self._token = data.get("idToken")
            return self._token
        except Exception as e:
            print(f"[WARNING] Firebase認証失敗: {e}", flush=True)
            return None

    def _api_get(self, path: str) -> Optional[dict]:
        """Voicy APIを呼び出す"""
        token = self._get_firebase_token()
        if not token:
            return None

        try:
            import requests
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "X-Identify": self._uuid,
                "X-Platform": "3",
                "Authorization": f"Bearer {token}",
                "Origin": "https://voicy.jp",
                "Accept": "application/json",
            }
            url = f"{VOICY_PLAYER_API}{path}"
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception:
            return None

    def extract_audio_url_via_selenium(self, page_url: str) -> Optional[Dict]:
        """
        Seleniumでページを開き、再生ボタンをクリックして音声URLをキャプチャ

        Returns:
            {"url": "...", "title": "...", "ext": "m4a"} or None
        """
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from webdriver_manager.chrome import ChromeDriverManager
            import time

            print(f"[INFO] Voicyページにアクセス (ブラウザ自動化): {page_url}", flush=True)

            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

            print("[INFO] ChromeDriverを準備中...", flush=True)
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)

            try:
                driver.get(page_url)
                print("[INFO] ページ読み込み中...", flush=True)

                # ページが完全に読み込まれるまで待機
                time.sleep(8)

                # タイトルを取得
                title = driver.title or "voicy_audio"
                title = re.sub(r'\s*[|-]\s*Voicy.*$', '', title).strip()

                # 再生ボタンを探してクリック
                play_buttons = driver.find_elements(By.CSS_SELECTOR, '[aria-label="再生"]')
                if play_buttons:
                    driver.execute_script("arguments[0].click();", play_buttons[0])
                    print("[INFO] 再生ボタンをクリック", flush=True)
                    time.sleep(5)
                else:
                    print("[WARNING] 再生ボタンが見つかりません", flush=True)

                # ネットワークログからHLS m3u8 URLを抽出
                logs = driver.get_log('performance')
                m3u8_urls = []
                mp3_urls = []

                for log in logs:
                    try:
                        message = json.loads(log['message'])
                        if message['message']['method'] == 'Network.requestWillBeSent':
                            req_url = message['message']['params']['request']['url']
                            # files.voicy.jp の音声URLを探す（ダミー音声を除外）
                            if 'files.voicy.jp' in req_url:
                                if '.m3u8' in req_url:
                                    if req_url not in m3u8_urls:
                                        m3u8_urls.append(req_url)
                                elif '.mp3' in req_url:
                                    if req_url not in mp3_urls:
                                        mp3_urls.append(req_url)
                            elif req_url.endswith('.mp3') and 'no-sound' not in req_url:
                                if req_url not in mp3_urls:
                                    mp3_urls.append(req_url)
                    except (KeyError, json.JSONDecodeError):
                        continue

                if m3u8_urls:
                    url = m3u8_urls[0]
                    print(f"[OK] HLS音声URL発見: {url}", flush=True)
                    return {"url": url, "title": title, "ext": "m4a"}

                if mp3_urls:
                    url = mp3_urls[0]
                    print(f"[OK] MP3音声URL発見: {url}", flush=True)
                    return {"url": url, "title": title, "ext": "mp3"}

                print("[WARNING] 音声URLが見つかりませんでした", flush=True)
                return None

            finally:
                driver.quit()
                print("[INFO] ブラウザを終了", flush=True)

        except ImportError as e:
            print(f"[ERROR] Seleniumがインストールされていません: {e}", flush=True)
            return None
        except Exception as e:
            print(f"[ERROR] Selenium処理エラー: {e}", flush=True)
            return None

    def extract_audio_info(self, page_url: str) -> Optional[Dict]:
        """
        VoicyのURLから音声情報を取得

        Returns:
            {"url": "...", "title": "...", "ext": "m4a"} or None
        """
        params = self._parse_url(page_url)
        if not params:
            print("[ERROR] 無効なVoicy URLです", flush=True)
            return None

        channel_id = params.get('channel_id')

        # APIでチャンネル情報を取得（タイトル用）
        channel_info = self._api_get(f"/channel/{channel_id}")
        if channel_info:
            channel_name = channel_info.get('name', '')
            print(f"[INFO] チャンネル: {channel_name}", flush=True)

        # Seleniumで再生ボタンクリック→音声URLキャプチャ
        return self.extract_audio_url_via_selenium(page_url)


def main():
    """テスト用のメイン関数"""
    import argparse

    parser = argparse.ArgumentParser(description="Voicy音声URL抽出ツール")
    parser.add_argument("url", help="VoicyページのURL")
    args = parser.parse_args()

    extractor = VoicyExtractor()
    if not extractor.is_voicy_url(args.url):
        print("[WARNING] このURLはVoicyページではない可能性があります")

    result = extractor.extract_audio_info(args.url)
    if result:
        print(f"\n音声URL: {result['url']}")
        print(f"タイトル: {result['title']}")
        print(f"形式: {result['ext']}")
        return 0
    else:
        print("\n音声URLの抽出に失敗しました")
        return 1


if __name__ == "__main__":
    sys.exit(main())
