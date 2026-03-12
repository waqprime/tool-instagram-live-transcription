#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
stand.fm音声抽出モジュール
stand.fmページから音声URLを抽出（yt-dlpの汎用エクストラクタより確実な専用実装）
"""

import re
import sys
import json
from typing import Optional, Dict, List
from urllib.parse import urlparse

# Windows環境での文字化け対策
if sys.platform == 'win32':
    import os
    os.environ['PYTHONIOENCODING'] = 'utf-8'


class StandfmExtractor:
    """stand.fmページから音声URLを抽出するクラス"""

    USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

    def is_standfm_url(self, url: str) -> bool:
        """URLがstand.fmかどうかを判定"""
        return bool(re.match(r'https?://stand\.fm/(episodes|channels)/', url))

    def _is_episode_url(self, url: str) -> bool:
        """エピソードURLかどうか"""
        return bool(re.match(r'https?://stand\.fm/episodes/[a-f0-9]+', url))

    def _is_channel_url(self, url: str) -> bool:
        """チャンネルURLかどうか"""
        return bool(re.match(r'https?://stand\.fm/channels/[a-f0-9]+', url))

    def _fetch_server_state(self, page_url: str) -> Optional[dict]:
        """ページHTMLからwindow.__SERVER_STATE__のJSONを取得"""
        try:
            import requests
            response = requests.get(
                page_url,
                headers={"User-Agent": self.USER_AGENT},
                timeout=15,
            )
            response.raise_for_status()
            html = response.text

            idx = html.find('__SERVER_STATE__')
            if idx < 0:
                print("[WARNING] __SERVER_STATE__が見つかりません", flush=True)
                return None

            start = html.find('{', idx)
            if start < 0:
                return None

            # 波括弧の対応でJSON終端を探す
            depth = 0
            end = start
            for i in range(start, min(start + 500000, len(html))):
                if html[i] == '{':
                    depth += 1
                elif html[i] == '}':
                    depth -= 1
                if depth == 0:
                    end = i + 1
                    break

            return json.loads(html[start:end])

        except Exception as e:
            print(f"[ERROR] ページ取得エラー: {e}", flush=True)
            return None

    def extract_audio_info(self, page_url: str) -> Optional[Dict]:
        """
        stand.fmのエピソードURLから音声情報を取得

        Returns:
            {"url": "...", "title": "...", "ext": "m4a", "channel": "..."} or None
        """
        if not self._is_episode_url(page_url):
            print(f"[ERROR] エピソードURLではありません: {page_url}", flush=True)
            return None

        print(f"[INFO] stand.fmページを取得中: {page_url}", flush=True)
        data = self._fetch_server_state(page_url)
        if not data:
            return None

        # エピソードIDをURLから抽出
        match = re.search(r'/episodes/([a-f0-9]+)', page_url)
        if not match:
            return None
        episode_id = match.group(1)

        # エピソード情報を取得
        episodes = data.get('episodes', {})
        episode = episodes.get(episode_id, {})
        title = episode.get('title', 'standfm_audio')
        channel_id = episode.get('channelId', '')

        # チャンネル名を取得
        channels = data.get('channels', {})
        channel = channels.get(channel_id, {})
        channel_name = channel.get('title', '')

        # topicsからdownloadUrlを探す
        topics = data.get('topics', {})
        download_url = None
        hls_url = None

        for topic_id, topic in topics.items():
            if topic.get('episodeId') == episode_id:
                download_url = topic.get('downloadUrl')
                hls_url = topic.get('hlsPlaylistUrl')
                break

        if download_url:
            print(f"[OK] 音声URL発見: {download_url}", flush=True)
            if channel_name:
                print(f"[INFO] チャンネル: {channel_name}", flush=True)
            return {
                "url": download_url,
                "title": title,
                "ext": "m4a",
                "channel": channel_name,
            }

        if hls_url:
            print(f"[OK] HLS URL発見: {hls_url}", flush=True)
            return {
                "url": hls_url,
                "title": title,
                "ext": "m4a",
                "channel": channel_name,
            }

        print("[ERROR] 音声URLが見つかりませんでした", flush=True)
        return None

    def extract_channel_episodes(self, channel_url: str) -> List[Dict]:
        """
        チャンネルURLからエピソード一覧を取得

        Returns:
            [{"episode_id": "...", "title": "...", "url": "..."}, ...]
        """
        if not self._is_channel_url(channel_url):
            print(f"[ERROR] チャンネルURLではありません: {channel_url}", flush=True)
            return []

        print(f"[INFO] stand.fmチャンネルを取得中: {channel_url}", flush=True)
        data = self._fetch_server_state(channel_url)
        if not data:
            return []

        episodes = data.get('episodes', {})
        result = []
        for ep_id, ep in episodes.items():
            result.append({
                "episode_id": ep_id,
                "title": ep.get('title', ''),
                "url": f"https://stand.fm/episodes/{ep_id}",
                "duration": ep.get('totalDuration', 0),
            })

        print(f"[OK] {len(result)}件のエピソードを取得", flush=True)
        return result

    def get_video_info(self, url: str) -> Optional[Dict]:
        """yt-dlp互換の情報取得"""
        if self._is_episode_url(url):
            result = self.extract_audio_info(url)
            if result:
                return {
                    'title': result['title'],
                    'uploader': result.get('channel', ''),
                    'id': re.search(r'/episodes/([a-f0-9]+)', url).group(1),
                }
        elif self._is_channel_url(url):
            data = self._fetch_server_state(url)
            if data:
                channels = data.get('channels', {})
                for ch_id, ch in channels.items():
                    return {
                        'title': ch.get('title', ''),
                        'uploader': ch.get('title', ''),
                        'id': ch_id,
                    }
        return None


def main():
    """テスト用のメイン関数"""
    import argparse

    parser = argparse.ArgumentParser(description="stand.fm音声URL抽出ツール")
    parser.add_argument("url", help="stand.fmページのURL")
    args = parser.parse_args()

    extractor = StandfmExtractor()
    if not extractor.is_standfm_url(args.url):
        print("[WARNING] このURLはstand.fmページではない可能性があります")

    result = extractor.extract_audio_info(args.url)
    if result:
        print(f"\n音声URL: {result['url']}")
        print(f"タイトル: {result['title']}")
        print(f"形式: {result['ext']}")
        if result.get('channel'):
            print(f"チャンネル: {result['channel']}")
        return 0
    else:
        print("\n音声URLの抽出に失敗しました")
        return 1


if __name__ == "__main__":
    sys.exit(main())
