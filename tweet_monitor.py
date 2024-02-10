from typing import List

from monitor_base import MonitorBase
from utils import parse_media_from_tweet, parse_text_from_tweet, parse_username_from_tweet, find_all, find_one, get_content


def _verify_tweet_user_id(tweet: dict, user_id: str) -> bool:
    return parse_username_from_tweet(tweet) == user_id


class TweetMonitor(MonitorBase):
    monitor_type = 'Tweet'
    rate_limit = 60

    def __init__(self, username: str, token_config: dict, cookies_dir: str, interval: int,
                 telegram_chat_id_list: List[int], cqhttp_url_list: List[str]):
        super().__init__(monitor_type=self.monitor_type,
                         username=username,
                         token_config=token_config,
                         cookies_dir=cookies_dir,
                         interval=interval,
                         telegram_chat_id_list=telegram_chat_id_list,
                         cqhttp_url_list=cqhttp_url_list)

        tweet_list = self.get_tweet_list()
        self.last_tweet_id = -1
        for tweet in tweet_list:
            if _verify_tweet_user_id(tweet, self.user_id):
                self.last_tweet_id = max(self.last_tweet_id, int(find_one(tweet, 'rest_id')))

        self.logger.info('Init tweet monitor succeed.\nUser id: {}\nLast tweet: {}'.format(self.user_id, self.last_tweet_id))

    def get_tweet_list(self) -> dict:
        api_name = 'UserTweetsAndReplies'
        params = {'userId': self.user_id, 'includePromotedContent': True, 'withVoice': True, 'count': 1000}
        json_response = self.twitter_watcher.query(api_name, params)
        if json_response is None:
            return None
        return find_all(json_response, 'tweet_results')

    def watch(self) -> bool:
        tweet_list = self.get_tweet_list()
        if tweet_list is None:
            return False

        max_tweet_id = -1
        for tweet in tweet_list:
            if not _verify_tweet_user_id(tweet, self.user_id):
                continue
            tweet_id = int(find_one(tweet, 'rest_id'))
            if tweet_id <= self.last_tweet_id:
                continue

            text = parse_text_from_tweet(tweet)
            retweet = find_one(tweet, 'retweeted_status_result')
            quote = find_one(tweet, 'quoted_status_result')
            if retweet:
                photo_url_list, video_url_list = parse_media_from_tweet(retweet)
            else:
                photo_url_list, video_url_list = parse_media_from_tweet(tweet)
                if quote:
                    quote_photo_url_list, quote_video_url_list = parse_media_from_tweet(quote)
                    photo_url_list.extend(quote_photo_url_list)
                    video_url_list.extend(quote_video_url_list)
                    quote_text = get_content(quote).get('full_text', '')
                    quote_user = find_one(quote, 'user_results')
                    quote_username = get_content(quote_user).get('screen_name', '')
                    text += '\nQuote: @{}: {}'.format(quote_username, quote_text)
            self.send_message(text, photo_url_list, video_url_list)

            max_tweet_id = max(max_tweet_id, tweet_id)

        self.last_tweet_id = max(self.last_tweet_id, max_tweet_id)
        self.update_last_watch_time()
        return True

    def status(self) -> str:
        return 'Last: {}, id: {}'.format(self.last_watch_time, self.last_tweet_id)
