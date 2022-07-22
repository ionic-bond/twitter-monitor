#!/usr/bin/python3

from typing import List, Union

from monitor_base import MonitorBase
from utils import convert_html_to_text


class TweetMonitor(MonitorBase):
    monitor_type = 'Tweet'
    rate_limit = 60

    def __init__(self, username: str, token_config: dict, telegram_chat_id_list: List[str],
                 cqhttp_url_list: List[str]):
        super().__init__(monitor_type=self.monitor_type,
                         username=username,
                         token_config=token_config,
                         telegram_chat_id_list=telegram_chat_id_list,
                         cqhttp_url_list=cqhttp_url_list)

        tweet_list = None
        while tweet_list is None:
            tweet_list = self.get_tweet_list()
        self.last_tweet_id = tweet_list[0]['id'] if tweet_list else 0

        self.logger.info('Init tweet monitor succeed.\nUser id: {}\nLast tweet: {}'.format(
            self.user_id, tweet_list[0]))

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
            self.send_message(convert_html_to_text(tweet['text']))
        if tweet_list:
            self.last_tweet_id = tweet_list[0]['id']
        self.update_last_watch_time()

    def status(self) -> str:
        return 'Last: {}, id: {}'.format(self.last_watch_time, self.last_tweet_id)
