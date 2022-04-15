#!/usr/bin/python3

import logging
from datetime import datetime
from typing import List, Union

from monitor_base import MonitorBase
from telegram_notifier import TelegramNotifier
from twitter_watcher import TwitterWatcher


class TweetMonitor(MonitorBase):

    def __init__(self, token_config: dict, username: str, telegram_chat_id_list: List[str]):
        self.twitter_watcher = TwitterWatcher(token_config['twitter_bearer_token_list'])
        self.user_id = self.twitter_watcher.get_id_by_username(username)
        tweet_list = None
        while tweet_list is None:
            tweet_list = self.get_tweet_list()
        self.last_tweet_id = tweet_list[0]['id'] if tweet_list else 0
        self.telegram_notifier = TelegramNotifier(
            token=token_config['telegram_bot_token'],
            chat_id_list=telegram_chat_id_list,
            username=username,
            module='Tweet')
        self.logger = logging.getLogger('{}-Tweet'.format(username))
        self.logger.info(
            'Init tweet monitor succeed.\nUsername: {}\nUser id: {}\nLast tweet: {}'.format(
                username, self.user_id, tweet_list[0]))
        self.last_watch_time = datetime.now()

    def get_tweet_list(self, since_id: str = None) -> Union[list, None]:
        url = 'https://api.twitter.com/2/users/{}/tweets'.format(self.user_id)
        params = {'max_results': 100}
        if since_id:
            params['since_id'] = since_id
        json_response = self.twitter_watcher.query(url, params)
        if json_response:
            return json_response.get('data', [])
        return None

    def watch(self):
        tweet_list = self.get_tweet_list(since_id=self.last_tweet_id)
        if tweet_list is None:
            return
        for tweet in tweet_list:
            self.telegram_notifier.send_message(tweet['text'])
        if tweet_list:
            self.last_tweet_id = tweet_list[0]['id']
        self.last_watch_time = datetime.now()

    def status(self) -> str:
        return 'Last: {}, id: {}'.format(self.last_watch_time, self.last_tweet_id)
