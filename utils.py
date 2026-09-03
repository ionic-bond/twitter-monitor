from collections import deque
from datetime import datetime, timezone
from functools import cached_property
from typing import Any, Callable

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
        bitrate = variant.get('bitrate', 0)
        if bitrate > max_bitrate:
            max_bitrate = bitrate
            video_url = variant.get('url', '')
    return video_url


def parse_media_from_tweet(tweet: dict) -> tuple[list[str], list[str]]:
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


def parse_create_time_from_tweet(tweet: dict) -> datetime:
    created_at = find_one(get_content(tweet), 'created_at')
    if not created_at:
        return datetime.fromtimestamp(0).replace(tzinfo=timezone.utc)
    return datetime.strptime(created_at, '%a %b %d %H:%M:%S %z %Y')


def find_all(obj: object, key: str) -> list[Any]:
    # DFS
    def dfs(obj: object, key: str, res: list[Any]) -> list[Any]:
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


def find_one(obj: object, key: str) -> Any:
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


class ProfileParser():

    def __init__(self, json_response: dict) -> None:
        self.json_response = json_response

    @cached_property
    def name(self) -> str:
        return find_one(self.json_response, 'core').get('name', '')

    @cached_property
    def username(self) -> str:
        return find_one(self.json_response, 'core').get('screen_name', '')

    @cached_property
    def location(self) -> str:
        return find_one(self.json_response, 'location').get('location', '')

    @cached_property
    def created_at(self) -> str:
        return find_one(self.json_response, 'core').get('created_at', '')

    @cached_property
    def bio(self) -> str:
        return find_one(self.json_response, 'profile_bio').get('description', '')

    @cached_property
    def website(self) -> str:
        return find_one(self.json_response,
                        'profile_bio').get('entities', {}).get('url', {}).get('urls', [{}])[0].get('expanded_url', '')

    @cached_property
    def followers_count(self) -> int:
        return find_one(self.json_response, 'relationship_counts').get('followers', 0)

    @cached_property
    def following_count(self) -> int:
        return find_one(self.json_response, 'relationship_counts').get('following', 0)

    @cached_property
    def like_count(self) -> int:
        return find_one(self.json_response, 'action_counts').get('favorites_count', 0)

    @cached_property
    def tweet_count(self) -> int:
        return find_one(self.json_response, 'tweet_counts').get('tweets', 0)

    @cached_property
    def profile_image_url(self) -> str:
        return find_one(self.json_response, 'avatar').get('image_url', '').replace('_normal', '')

    @cached_property
    def profile_banner_url(self) -> str:
        banner = find_one(self.json_response, 'banner')
        return banner.get('image_url', '') if banner else ''

    @cached_property
    def pinned_tweet(self) -> str | None:
        pinned_items = find_one(self.json_response, 'pinned_items')
        pinned_tweet = pinned_items.get('tweet_ids_str', []) if pinned_items else []
        if not pinned_tweet:
            return None
        if isinstance(pinned_tweet, list):
            return pinned_tweet[0]
        return pinned_tweet

    @cached_property
    def highlighted_tweet_count(self) -> str:
        highlights = find_one(self.json_response, 'highlights_info')
        return highlights.get('highlighted_tweets', '0') if highlights else '0'


def get_content(obj: dict) -> dict:
    return find_one(obj, 'legacy')


def get_cursor(obj: object) -> str | None:
    entries = find_one(obj, 'entries')
    for entry in entries:
        entry_id = entry.get('entryId', '')
        if entry_id.startswith('cursor-bottom'):
            return entry.get('content', {}).get('value', '')


def check_initialized(cls_method: Callable[..., Any]) -> Callable[..., Any]:

    def wrapper(cls: type[Any], *args: object, **kwargs: object) -> Any:
        if cls.initialized:
            return cls_method(cls, *args, **kwargs)
        else:
            raise RuntimeError('Class has not initialized!')

    return wrapper
