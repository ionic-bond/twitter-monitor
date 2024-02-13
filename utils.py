import json
import os
from collections import deque
from typing import Tuple

from bs4 import BeautifulSoup
from requests.cookies import RequestsCookieJar
from tweepy_authlib import CookieSessionUserHandler


def convert_html_to_text(html: str) -> str:
    bs = BeautifulSoup(html, "html.parser")
    return bs.get_text()


def get_photo_url_from_media(media: dict) -> str:
    return media.get('media_url_https', '')


def get_video_url_from_media(media: dict) -> str:
    video_info = media.get('video_info', {})
    variants = video_info.get('variants', [])
    max_bitrate = -1
    video_url = ''
    for variant in variants:
        bitrate = variant.get('bitrate', 0)
        if bitrate > max_bitrate:
            max_bitrate = bitrate
            video_url = variant.get('url', '')
    return video_url


def parse_media_from_tweet(tweet: dict) -> Tuple[list, list]:
    photo_url_list = []
    video_url_list = []
    tweet_content = get_content(tweet)
    medias = tweet_content.get('extended_entities', {}).get('media', [])
    for media in medias:
        media_type = media.get('type', '')
        if media_type == 'photo':
            photo_url_list.append(get_photo_url_from_media(media))
        elif media_type in ['video', 'animated_gif']:
            video_url_list.append(get_video_url_from_media(media))
    return photo_url_list, video_url_list


def parse_text_from_tweet(tweet: dict) -> str:
    tweet_content = get_content(tweet)
    return convert_html_to_text(tweet_content.get('full_text', ''))


def parse_username_from_tweet(tweet: dict) -> str:
    user = find_one(tweet, 'user_results')
    return find_one(user, 'rest_id')


def get_auth_handler(username: str, password: str):
    auth_handler = CookieSessionUserHandler(screen_name=username, password=password)
    return auth_handler


def dump_auth_handler(auth_handler: CookieSessionUserHandler, path: str):
    cookies = auth_handler.get_cookies()
    with open(path, 'w') as f:
        json.dump(cookies.get_dict(), f, ensure_ascii=False, indent=4)


def find_all(obj: any, key: str) -> list:
    # DFS
    def dfs(obj: any, key: str, res: list) -> list:
        if not obj:
            return res
        if isinstance(obj, list):
            for e in obj:
                res.extend(dfs(e, key, []))
            return res
        if isinstance(obj, dict):
            if key in obj:
                res.append(obj[key])
            for v in obj.values():
                res.extend(dfs(v, key, []))
        return res

    return dfs(obj, key, [])


def find_one(obj: any, key: str) -> any:
    # BFS
    que = deque([obj])
    while len(que):
        obj = que.popleft()
        if isinstance(obj, list):
            que.extend(obj)
        if isinstance(obj, dict):
            if key in obj:
                return obj[key]
            for v in obj.values():
                que.append(v)
    return None


def get_content(obj: dict) -> dict:
    return find_one(obj, 'legacy')


def get_cursor(obj: any) -> str:
    entries = find_one(obj, 'entries')
    for entry in entries:
        entry_id = entry.get('entryId', '')
        if entry_id.startswith('cursor-bottom'):
            return entry.get('content', {}).get('value', '')
