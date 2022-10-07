from typing import Tuple

from bs4 import BeautifulSoup


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
