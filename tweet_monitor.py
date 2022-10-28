from typing import List, Union

from monitor_base import MonitorBase
from utils import convert_html_to_text, parse_media_from_tweet


class TweetMonitor(MonitorBase):
    monitor_type = 'Tweet'
    rate_limit = 60

    def __init__(self, username: str, token_config: dict, cache_dir: str,
                 telegram_chat_id_list: List[int], cqhttp_url_list: List[str]):
        super().__init__(monitor_type=self.monitor_type,
                         username=username,
                         token_config=token_config,
                         cache_dir=cache_dir,
                         telegram_chat_id_list=telegram_chat_id_list,
                         cqhttp_url_list=cqhttp_url_list)

        tweet_list = None
        while tweet_list is None:
            tweet_list = self.get_tweet_list()
        self.last_tweet_id = tweet_list[0]['id'] if tweet_list else 0

        self.logger.info('Init tweet monitor succeed.\nUser id: {}\nLast tweet: {}'.format(
            self.user_id, tweet_list[0]))

    def get_tweet_list(self, since_id: str = None) -> Union[list, None]:
        # Tweet API V2 is harder to parse media
        url = 'https://api.twitter.com/1.1/statuses/user_timeline.json'
        params = {'user_id': self.user_id, 'count': 200, 'trim_user': True}
        if since_id:
            params['since_id'] = since_id
        return self.twitter_watcher.query(url, params)

    def watch(self) -> bool:
        tweet_list = self.get_tweet_list(since_id=self.last_tweet_id)
        if tweet_list is None:
            return False
        for tweet in tweet_list:
            photo_url_list, video_url_list = parse_media_from_tweet(tweet)
            if not photo_url_list and not video_url_list:
                retweeted_status = tweet.get('retweeted_status', None)
                if retweeted_status:
                    photo_url_list, video_url_list = parse_media_from_tweet(retweeted_status)
            self.send_message(convert_html_to_text(tweet['text']), photo_url_list, video_url_list)
        if tweet_list:
            self.last_tweet_id = tweet_list[0]['id']
        self.update_last_watch_time()
        return True

    def status(self) -> str:
        return 'Last: {}, id: {}'.format(self.last_watch_time, self.last_tweet_id)
