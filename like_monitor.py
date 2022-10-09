"""
Because the twitter api only allows to query the last 200 tweets sorted by creation time,
we cannot know if the user likes a very old tweet.
"""

import json
import os

from typing import List, Union, Set

from monitor_base import MonitorBase
from utils import convert_html_to_text, parse_media_from_tweet


def _get_like_id_set(like_list: list) -> Set[str]:
    return set(like['id'] for like in like_list)


def _get_max_k_set(like_id_set: Set[str], k: int) -> Set[str]:
    like_id_list = list(like_id_set)
    like_id_list.sort()
    return set(like_id_list[-k:])


class LikeMonitor(MonitorBase):
    monitor_type = 'Like'
    rate_limit = 5
    like_id_set_max_size = 1000

    def __init__(self, username: str, token_config: dict, cache_dir: str,
                 telegram_chat_id_list: List[int], cqhttp_url_list: List[str]):
        super().__init__(monitor_type=self.monitor_type,
                         username=username,
                         token_config=token_config,
                         cache_dir=cache_dir,
                         telegram_chat_id_list=telegram_chat_id_list,
                         cqhttp_url_list=cqhttp_url_list)
        
        self.load_existing_like_id()
        like_list = None
        while like_list is None:
            like_list = self.get_like_list()
        like_id_set = _get_like_id_set(like_list)
        self.existing_like_id_set |= like_id_set
        self.min_like_id = min(like_id_set) if like_id_set else 0
        self.dump_existing_like_id()

        self.logger.info('Init like monitor succeed.\nUser id: {}\nExisting likes: {}'.format(
            self.user_id, self.existing_like_id_set))

    def get_like_list(self) -> Union[list, None]:
        url = 'https://api.twitter.com/1.1/favorites/list.json'
        params = {'user_id': self.user_id, 'count': 200}
        return self.twitter_watcher.query(url, params)

    def watch(self):
        like_list = self.get_like_list()
        if like_list is None:
            return
        for like in reversed(like_list):
            if like['id'] not in self.existing_like_id_set and like['id'] > self.min_like_id:
                # Debug log
                self.logger.info('Like: {}, num: {}'.format(like['id'], len(like_list)))
                photo_url_list, video_url_list = parse_media_from_tweet(like)
                self.send_message(
                    '@{}: {}'.format(like['user']['screen_name'],
                                     convert_html_to_text(like['text'])), photo_url_list,
                    video_url_list)
        like_id_set = _get_like_id_set(like_list)
        if len(like_id_set) > 150:
            self.min_like_id = max(self.min_like_id, min(like_id_set))
        self.existing_like_id_set |= like_id_set
        self.dump_existing_like_id()
        self.update_last_watch_time()

    def status(self) -> str:
        return 'Last: {}, num: {}, min: {}'.format(self.last_watch_time,
                                                   len(self.existing_like_id_set), self.min_like_id)

    def dump_existing_like_id(self):
        self.existing_like_id_set = _get_max_k_set(self.existing_like_id_set,
                                                   LikeMonitor.like_id_set_max_size)
        with open(self.cache_file_path, 'w') as cache_file:
            json.dump(list(self.existing_like_id_set), cache_file, indent=4)

    def load_existing_like_id(self):
        if not os.path.exists(self.cache_file_path):
            self.existing_like_id_set = set()
            return
        with open(self.cache_file_path, 'r') as cache_file:
            self.existing_like_id_set = set(json.load(cache_file))
            self.logger.info('Loaded {} like ids from cache.'.format(len(self.existing_like_id_set)))
