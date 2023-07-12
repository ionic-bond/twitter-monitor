import json
import os
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
        bitrate = variant.get('bitrate', -1)
        if bitrate > max_bitrate:
            max_bitrate = bitrate
            video_url = variant.get('url', '')
    return video_url


def parse_media_from_tweet(tweet: dict) -> Tuple[list, list]:
    photo_url_list = []
    video_url_list = []
    medias = tweet.get('extended_entities', {}).get('media', [])
    for media in medias:
        media_type = media.get('type', '')
        if media_type == 'photo':
            photo_url_list.append(get_photo_url_from_media(media))
        elif media_type in ['video', 'animated_gif']:
            video_url_list.append(get_video_url_from_media(media))
    return photo_url_list, video_url_list


def get_auth_handler(username: str, password: str):
    auth_handler = CookieSessionUserHandler(screen_name=username, password=password)
    return auth_handler


def dump_auth_handler(auth_handler: CookieSessionUserHandler, path: str):
    cookies = auth_handler.get_cookies()
    with open(path, 'w') as f:
        json.dump(cookies.get_dict(), f, ensure_ascii=False, indent=4)


def load_auth_handler(cookie_path: str) -> CookieSessionUserHandler:
    assert os.path.exists(cookie_path)
    with open(cookie_path, 'r') as f:
        cookies_dict = json.load(f)
    cookies = RequestsCookieJar()
    for key, value in cookies_dict.items():
        cookies.set(key, value)
    auth_handler = CookieSessionUserHandler(cookies=cookies)
    return auth_handler
