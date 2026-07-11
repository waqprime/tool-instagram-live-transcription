#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Spotify Podcast音声抽出モジュール
SpotifyのPodcast URLからRSSフィード経由でMP3音声URLを取得
"""

import re
import sys
import time
import difflib
import unicodedata
import xml.etree.ElementTree as ET
from typing import Optional, Dict, List
from urllib.parse import quote_plus

import requests as _requests_module

# XML実体展開DoS対策: defusedxmlが利用可能ならそちらを使う。
# PyInstallerバンドル等でdefusedxmlが無い環境では標準ライブラリにフォールバックし、
# その場合はフィードサイズに上限を設けて防御する。
try:
    from defusedxml.ElementTree import fromstring as _safe_xml_fromstring
    _HAS_DEFUSEDXML = True
except ImportError:
    from xml.etree.ElementTree import fromstring as _safe_xml_fromstring
    _HAS_DEFUSEDXML = False

# フォールバック時（defusedxml不在時）のRSSフィード最大サイズ
_MAX_RSS_FEED_BYTES = 20 * 1024 * 1024  # 20MB

# Windows環境での文字化け対策
if sys.platform == 'win32':
    import os
    os.environ['PYTHONIOENCODING'] = 'utf-8'


class SpotifyExtractor:
    """Spotify PodcastからRSSフィード経由で音声URLを取得するクラス"""

    USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    # URL patterns
    _EPISODE_RE = re.compile(r'https?://open\.spotify\.com/(?:intl-[a-z]{2}/)?episode/([A-Za-z0-9]+)')
    _SHOW_RE = re.compile(r'https?://open\.spotify\.com/(?:intl-[a-z]{2}/)?show/([A-Za-z0-9]+)')

    # リクエスト間隔
    REQUEST_INTERVAL = 1.0
    MAX_RETRIES = 3

    def __init__(self):
        self._session = _requests_module.Session()
        self._session.headers.update({"User-Agent": self.USER_AGENT})
        self._last_request_time = 0.0
        self._feed_cache = {}  # show_name -> feed_url
        self._audio_info_cache = {}  # spotify_url -> extract_audio_info結果

    def is_spotify_url(self, url: str) -> bool:
        """URLがSpotify PodcastのURLかどうかを判定"""
        return bool(self._EPISODE_RE.match(url) or self._SHOW_RE.match(url))

    def _is_episode_url(self, url: str) -> bool:
        return bool(self._EPISODE_RE.match(url))

    def _is_show_url(self, url: str) -> bool:
        return bool(self._SHOW_RE.match(url))

    def _get_spotify_id(self, url: str) -> Optional[str]:
        m = self._EPISODE_RE.match(url) or self._SHOW_RE.match(url)
        return m.group(1) if m else None

    def _wait_for_rate_limit(self):
        elapsed = time.time() - self._last_request_time
        if elapsed < self.REQUEST_INTERVAL:
            time.sleep(self.REQUEST_INTERVAL - elapsed)
        self._last_request_time = time.time()

    # ------------------------------------------------------------------ #
    # Step 1: Spotifyからメタデータ取得
    # ------------------------------------------------------------------ #

    def _fetch_embed_metadata(self, spotify_url: str) -> Optional[Dict]:
        """
        Spotify embedページからメタデータを取得

        embedページのJSONには:
        - entity.name: エピソードタイトル
        - entity.subtitle: 番組名
        - entity.type: "episode"
        """
        spotify_id = self._get_spotify_id(spotify_url)
        if not spotify_id:
            return None

        # show/episode どちらもembedページでエピソード情報が取れる
        if self._is_show_url(spotify_url):
            embed_url = f"https://open.spotify.com/embed/show/{spotify_id}"
        else:
            embed_url = f"https://open.spotify.com/embed/episode/{spotify_id}"

        try:
            self._wait_for_rate_limit()
            resp = self._session.get(embed_url, timeout=15)
            if resp.status_code != 200:
                print(f"[WARNING] embedページ応答: {resp.status_code}", flush=True)
                return None

            import json as _json
            match = re.search(r'<script[^>]*>(\{"props".*?})</script>', resp.text, re.DOTALL)
            if not match:
                return None

            data = _json.loads(match.group(1))
            entity = data.get('props', {}).get('pageProps', {}).get('state', {}).get('data', {}).get('entity', {})
            if not entity:
                return None

            return {
                "episode_title": entity.get('name', ''),
                "show_name": entity.get('subtitle', ''),
            }
        except Exception as e:
            print(f"[WARNING] embedメタデータ取得失敗: {e}", flush=True)
            return None

    def _fetch_oembed(self, spotify_url: str) -> Optional[Dict]:
        """Spotify oEmbed APIでメタデータを取得（認証不要、show URLのみ対応）"""
        oembed_url = f"https://open.spotify.com/oembed?url={quote_plus(spotify_url)}"
        try:
            self._wait_for_rate_limit()
            resp = self._session.get(oembed_url, timeout=15)
            if resp.status_code != 200:
                return None
            return resp.json()
        except Exception:
            return None

    def _get_metadata(self, spotify_url: str) -> Optional[Dict]:
        """
        Spotifyメタデータを取得

        Returns:
            {"episode_title": "...", "show_name": "..."} or None
        """
        # 1. embedページから取得（番組名 + エピソード名が確実に取れる）
        meta = self._fetch_embed_metadata(spotify_url)
        if meta and meta.get('show_name'):
            return meta

        # 2. フォールバック: oEmbed API（show URLのみ動作、エピソード名が返る）
        oembed = self._fetch_oembed(spotify_url)
        if oembed:
            title = oembed.get('title', '')
            if self._is_show_url(spotify_url):
                # show URLの場合、oEmbedのtitleはエピソード名だが番組名としても検索に使える場合がある
                return {"episode_title": title, "show_name": title}
            else:
                # episode URLの場合、oEmbedのtitleは番組名ではないのでshow_nameにしない
                return {"episode_title": title, "show_name": ''}

        return None

    # ------------------------------------------------------------------ #
    # Step 2: Apple Podcasts APIでRSSフィード検索
    # ------------------------------------------------------------------ #

    @staticmethod
    def _normalize_title(s: str) -> str:
        """タイトルを正規化（模糊マッチ用）"""
        s = unicodedata.normalize('NFKC', s.lower())
        s = re.sub(r'[^\w\s]', ' ', s)
        s = re.sub(r'\s+', ' ', s).strip()
        return s

    @staticmethod
    def _title_similarity(a: str, b: str) -> float:
        na = SpotifyExtractor._normalize_title(a)
        nb = SpotifyExtractor._normalize_title(b)
        return difflib.SequenceMatcher(None, na, nb).ratio()

    def _search_podcast_feed(self, show_name: str) -> Optional[str]:
        """Apple Podcasts Search APIで番組のRSSフィードURLを検索"""
        if show_name in self._feed_cache:
            return self._feed_cache[show_name]

        search_url = (
            f"https://itunes.apple.com/search"
            f"?term={quote_plus(show_name)}"
            f"&media=podcast&entity=podcast&limit=10"
        )

        try:
            self._wait_for_rate_limit()
            resp = self._session.get(search_url, timeout=15)
            if resp.status_code != 200:
                print(f"[WARNING] Apple Podcasts API応答: {resp.status_code}", flush=True)
                return None

            data = resp.json()
            results = data.get('results', [])
            if not results:
                print(f"[WARNING] Apple Podcastsで見つかりません: {show_name}", flush=True)
                return None

            # 類似度でマッチング
            best_match = None
            best_score = 0.0
            for r in results:
                name = r.get('collectionName', '')
                score = self._title_similarity(show_name, name)
                # 同スコアの場合、エピソード数が多い方を優先
                if score > best_score or (score == best_score and best_match and
                        r.get('trackCount', 0) > best_match.get('trackCount', 0)):
                    best_score = score
                    best_match = r

            if best_match and best_score >= 0.4:
                feed_url = best_match.get('feedUrl')
                if feed_url:
                    print(f"[INFO] RSSフィード発見: {best_match['collectionName']} (類似度: {best_score:.2f})", flush=True)
                    self._feed_cache[show_name] = feed_url
                    return feed_url
                else:
                    print(f"[WARNING] RSSフィードURLがありません: {best_match['collectionName']}", flush=True)
            else:
                print(f"[WARNING] 十分な類似度の番組が見つかりません (最高: {best_score:.2f})", flush=True)

        except Exception as e:
            print(f"[ERROR] Apple Podcasts検索エラー: {e}", flush=True)

        # リトライ: タイトルを短くして再検索
        shortened = re.sub(r'\s*[\(（【\[].*$', '', show_name).strip()
        if shortened and shortened != show_name:
            print(f"[INFO] 短縮タイトルで再検索: {shortened}", flush=True)
            return self._search_podcast_feed(shortened)

        return None

    # ------------------------------------------------------------------ #
    # Step 3: RSSフィード解析
    # ------------------------------------------------------------------ #

    def _fetch_and_parse_rss(self, feed_url: str) -> Optional[ET.Element]:
        """RSSフィードを取得してパース"""
        try:
            self._wait_for_rate_limit()
            resp = self._session.get(feed_url, timeout=30, stream=True)
            if resp.status_code == 401 or resp.status_code == 403:
                print(f"[ERROR] RSSフィードへのアクセスが拒否されました（認証が必要な可能性があります）", flush=True)
                resp.close()
                return None
            if resp.status_code != 200:
                print(f"[WARNING] RSSフィード取得失敗: {resp.status_code}", flush=True)
                resp.close()
                return None

            # サイズガード: 全量ダウンロード後にチェックすると上限の意味が無いため、
            # ストリーミングでチャンクごとに読み、上限超過時点で打ち切る。
            # defusedxmlの有無に関わらず常に適用する（多層防御）。
            chunks = []
            total = 0
            for chunk in resp.iter_content(chunk_size=65536):
                total += len(chunk)
                if total > _MAX_RSS_FEED_BYTES:
                    print(
                        f"[ERROR] RSSフィードがサイズ上限を超えています "
                        f"({_MAX_RSS_FEED_BYTES}バイト超)。安全のため打ち切ります",
                        flush=True,
                    )
                    resp.close()
                    return None
                chunks.append(chunk)

            return _safe_xml_fromstring(b''.join(chunks))
        except ET.ParseError as e:
            print(f"[ERROR] RSS XMLパースエラー: {e}", flush=True)
            return None
        except Exception as e:
            print(f"[ERROR] RSSフィード取得エラー: {e}", flush=True)
            return None

    def _extract_episode_from_item(self, item: ET.Element, ns: dict) -> Optional[Dict]:
        """RSS <item>要素からエピソード情報を抽出"""
        title_el = item.find('title')
        title = title_el.text.strip() if title_el is not None and title_el.text else ''

        enclosure = item.find('enclosure')
        if enclosure is None:
            return None

        audio_url = enclosure.get('url', '')
        if not audio_url:
            return None

        audio_type = enclosure.get('type', '')
        # 拡張子判定
        if 'mp3' in audio_type or audio_url.lower().endswith('.mp3'):
            ext = 'mp3'
        elif 'm4a' in audio_type or 'mp4' in audio_type:
            ext = 'm4a'
        else:
            ext = 'mp3'  # デフォルト

        pub_date = ''
        pub_el = item.find('pubDate')
        if pub_el is not None and pub_el.text:
            pub_date = pub_el.text.strip()

        return {
            "title": title,
            "url": audio_url,
            "ext": ext,
            "pub_date": pub_date,
        }

    def _get_rss_show_name(self, root: ET.Element) -> str:
        """RSSフィードから番組名を取得"""
        channel = root.find('channel')
        if channel is not None:
            title_el = channel.find('title')
            if title_el is not None and title_el.text:
                return title_el.text.strip()
        return ''

    def _find_episode_in_rss(self, root: ET.Element, episode_title: str) -> Optional[Dict]:
        """RSSフィード内でタイトルが一致するエピソードを検索"""
        ns = {'itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd'}
        channel = root.find('channel')
        if channel is None:
            return None

        best_match = None
        best_score = 0.0

        for item in channel.findall('item'):
            ep = self._extract_episode_from_item(item, ns)
            if not ep:
                continue

            score = self._title_similarity(episode_title, ep['title'])
            if score > best_score:
                best_score = score
                best_match = ep

        if best_match and best_score >= 0.6:
            print(f"[INFO] エピソード一致: {best_match['title']} (類似度: {best_score:.2f})", flush=True)
            return best_match
        elif best_match:
            print(f"[WARNING] 最も近いエピソード: {best_match['title']} (類似度: {best_score:.2f} < 0.6)", flush=True)

        return None

    def _get_latest_episode(self, root: ET.Element) -> Optional[Dict]:
        """RSSフィードから最新エピソードを取得（pubDateでソート）"""
        from datetime import timezone
        from email.utils import parsedate_to_datetime
        ns = {'itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd'}
        channel = root.find('channel')
        if channel is None:
            return None

        episodes = []
        for item in channel.findall('item'):
            ep = self._extract_episode_from_item(item, ns)
            if ep:
                episodes.append(ep)

        if not episodes:
            return None

        # pubDateでソート（新しい順）、パース失敗時は元の順序を維持
        # tz付き/naiveなdatetimeが混在するとsort時にTypeErrorになるため、
        # naiveなものはUTC扱いに正規化して比較可能にする
        def parse_date(ep):
            try:
                dt = parsedate_to_datetime(ep['pub_date'])
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except Exception:
                return None

        dated = [(ep, parse_date(ep)) for ep in episodes]
        dated_valid = [(ep, dt) for ep, dt in dated if dt is not None]

        if dated_valid:
            dated_valid.sort(key=lambda x: x[1], reverse=True)
            return dated_valid[0][0]

        # pubDateがパースできない場合は最初のエピソードを返す
        return episodes[0]

    # ------------------------------------------------------------------ #
    # 公開API
    # ------------------------------------------------------------------ #

    def extract_audio_info(self, spotify_url: str) -> Optional[Dict]:
        """
        Spotify Podcast URLから音声情報を取得

        Returns:
            {"url": "...mp3", "title": "...", "ext": "mp3", "channel": "..."} or None
        """
        if spotify_url in self._audio_info_cache:
            cached = self._audio_info_cache[spotify_url]
            print(f"[INFO] キャッシュから音声情報を取得: {cached.get('title', '')}", flush=True)
            return cached

        print(f"[INFO] Spotify Podcastの音声を検索中...", flush=True)

        # Step 1: メタデータ取得
        meta = self._get_metadata(spotify_url)
        if not meta:
            print(f"[ERROR] Spotifyメタデータの取得に失敗しました", flush=True)
            return None

        is_episode = self._is_episode_url(spotify_url)
        episode_title = meta.get('episode_title', '')
        show_name = meta.get('show_name', '')

        if show_name:
            print(f"[INFO] 番組: {show_name}", flush=True)
        if episode_title and episode_title != show_name:
            print(f"[INFO] エピソード: {episode_title}", flush=True)

        # Step 2: 番組名でRSSフィード検索
        feed_url = None
        if show_name:
            feed_url = self._search_podcast_feed(show_name)

        if not feed_url and episode_title and episode_title != show_name:
            feed_url = self._search_podcast_feed(episode_title)

        if not feed_url:
            print(f"[ERROR] RSSフィードが見つかりません。このPodcastはApple Podcastsに登録されていない可能性があります", flush=True)
            return None

        # Step 3: RSSフィード解析
        print(f"[INFO] RSSフィードを取得中...", flush=True)
        root = self._fetch_and_parse_rss(feed_url)
        if root is None:
            return None

        show_name_from_rss = self._get_rss_show_name(root)
        if show_name_from_rss:
            print(f"[INFO] 番組名: {show_name_from_rss}", flush=True)

        if is_episode:
            # エピソードURLの場合: タイトルマッチ
            episode = self._find_episode_in_rss(root, episode_title)
            if not episode:
                print(f"[ERROR] RSSフィード内に一致するエピソードが見つかりません", flush=True)
                print(f"[INFO] 検索タイトル: {episode_title}", flush=True)
                return None
        else:
            # 番組URLの場合: 最新エピソード
            episode = self._get_latest_episode(root)
            if not episode:
                print(f"[ERROR] RSSフィードにエピソードがありません", flush=True)
                return None
            print(f"[INFO] 最新エピソード: {episode['title']}", flush=True)

        result = {
            "url": episode['url'],
            "title": episode['title'],
            "ext": episode.get('ext', 'mp3'),
            "channel": show_name_from_rss or show_name or '',
        }

        print(f"[OK] 音声URL発見: {result['url'][:80]}...", flush=True)
        self._audio_info_cache[spotify_url] = result
        return result

    def get_video_info(self, url: str) -> Optional[Dict]:
        """yt-dlp互換の情報取得"""
        result = self.extract_audio_info(url)
        if result:
            return {
                'title': result['title'],
                'uploader': result.get('channel', ''),
                'id': self._get_spotify_id(url) or '',
            }
        return None


def main():
    """テスト用のメイン関数"""
    import argparse

    parser = argparse.ArgumentParser(description="Spotify Podcast音声URL抽出ツール")
    parser.add_argument("url", help="Spotify PodcastのURL")
    args = parser.parse_args()

    extractor = SpotifyExtractor()
    if not extractor.is_spotify_url(args.url):
        print("[WARNING] このURLはSpotify Podcastではない可能性があります")

    result = extractor.extract_audio_info(args.url)
    if result:
        print(f"\n音声URL: {result['url']}")
        print(f"タイトル: {result['title']}")
        print(f"形式: {result['ext']}")
        if result.get('channel'):
            print(f"番組名: {result['channel']}")
        return 0
    else:
        print("\n音声URLの抽出に失敗しました")
        return 1


if __name__ == "__main__":
    sys.exit(main())
