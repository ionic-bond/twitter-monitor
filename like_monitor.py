#!/usr/bin/python3
"""
Because the twitter api only allows to query the last 200 tweets sorted by creation time,
we cannot know if the user likes a very old tweet.
"""

import logging
from datetime import datetime
from typing import List, Union, Set

from telegram_notifier import TelegramNotifier
from twitter_watcher import TwitterWatcher


def _get_like_id_set(like_list: list) -> Set[str]:
    return set(like['id'] for like in like_list)


class LikeMonitor:

    def __init__(self, token_config: dict, username: str, telegram_chat_id_list: List[str]):
        self.username = username
        self.twitter_watcher = TwitterWatcher(token_config['twitter_bearer_token_list'])
        like_list = self.get_like_list()
        while not like_list:
            like_list = self.get_like_list()
        self.existing_like_id_set = _get_like_id_set(like_list)
        self.telegram_notifier = TelegramNotifier(
            token=token_config['telegram_bot_token'],
            chat_id_list=telegram_chat_id_list,
            username=username,
            module='Like')
        self.logger = logging.getLogger('{}-Like'.format(username))
        self.logger.info('Init like monitor succeed.\nUsername: {}\nExisting likes: {}'.format(
            self.username, self.existing_like_id_set))
        self.last_watch_time = datetime.now()

    def get_like_list(self) -> Union[list, None]:
        url = 'https://api.twitter.com/1.1/favorites/list.json'
        params = {'screen_name': self.username, 'count': 200}
        return self.twitter_watcher.query(url, params)

    def watch(self):
        like_list = self.get_like_list()
        if not like_list:
            return
        for like in reversed(like_list[:-10]):
            if like['id'] not in self.existing_like_id_set:
                self.telegram_notifier.send_message('@{}: {}'.format(like['user']['screen_name'],
                                                                     like['text']))
        self.existing_like_id_set |= _get_like_id_set(like_list)
        self.last_watch_time = datetime.now()

    def status(self) -> str:
        return 'Last watch time: {}, existing like number: {}'.format(
            self.last_watch_time, len(self.existing_like_id_set))
