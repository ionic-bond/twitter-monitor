import time
from datetime import datetime, timedelta, timezone

from monitor_base import MonitorBase
from utils import parse_media_from_tweet, parse_text_from_tweet, parse_create_time_from_tweet, find_all, find_one, get_content, convert_html_to_text


def _verify_tweet_user_id(tweet: dict, user_id: str) -> bool:
    user = find_one(tweet, 'user_results')
    return find_one(user, 'rest_id') == user_id


class TweetMonitor(MonitorBase):
    monitor_type = 'Tweet'

    def __init__(self, username: str, title: str, token_config: dict, user_config: dict, cookies_dir: str):
        super().__init__(monitor_type=self.monitor_type,
                         username=username,
                         title=title,
                         token_config=token_config,
                         user_config=user_config,
                         cookies_dir=cookies_dir)

        tweet_list = self.get_tweet_list()
        while tweet_list is None:
            time.sleep(60)
            tweet_list = self.get_tweet_list()

        self.last_tweet_id = -1
        for tweet in tweet_list:
            if _verify_tweet_user_id(tweet, self.user_id):
                self.last_tweet_id = max(self.last_tweet_id, int(find_one(tweet, 'rest_id')))

        self.logger.info('Init tweet monitor succeed.\nUser id: {}\nLast tweet: {}'.format(
            self.user_id, self.last_tweet_id))

    def get_tweet_list(self) -> dict:
        api_name = 'UserTweetsAndReplies'
        params = {'userId': self.user_id, 'includePromotedContent': True, 'withVoice': True, 'count': 1000}
        json_response = self.twitter_watcher.query(api_name, params)
        if json_response is None:
            return None
        return find_all(json_response, 'tweet_results')

    def get_tweet_detail(self, tweet_id: str) -> dict:
        api_name = 'TweetDetail'
        params = {
            'focalTweetId': tweet_id,
            'withVoice': True,
            "includePromotedContent": True,
            "withCommunity": True,
            "withBirdwatchNotes": True
        }
        json_response = self.twitter_watcher.query(api_name, params)
        return json_response

    def watch(self) -> bool:
        tweet_list = self.get_tweet_list()
        if tweet_list is None:
            return False

        max_tweet_id = -1
        new_tweet_list = []
        time_threshold = datetime.now(timezone.utc) - timedelta(minutes=5)
        for tweet in tweet_list:
            if not _verify_tweet_user_id(tweet, self.user_id):
                continue
            tweet_id = int(find_one(tweet, 'rest_id'))
            if tweet_id <= self.last_tweet_id:
                continue
            if parse_create_time_from_tweet(tweet) < time_threshold:
                continue

            new_tweet_list.append(tweet)
            max_tweet_id = max(max_tweet_id, tweet_id)

        self.last_tweet_id = max(self.last_tweet_id, max_tweet_id)

        for tweet in reversed(new_tweet_list):
            tweet_id = find_one(tweet, 'rest_id')
            tweet_detail = self.get_tweet_detail(tweet_id)
            text = parse_text_from_tweet(tweet_detail)
            retweet = find_one(tweet_detail, 'retweeted_status_result')
            quote = find_one(tweet_detail, 'quoted_status_result')
            if retweet:
                photo_url_list, video_url_list = parse_media_from_tweet(retweet)
            else:
                photo_url_list, video_url_list = parse_media_from_tweet(tweet_detail)
                if quote:
                    quote_text = get_content(quote).get('full_text', '')
                    quote_user = find_one(quote, 'user_results')
                    quote_username = find_one(quote_user, 'screen_name')
                    text += '\n\nQuote: @{}: {}'.format(quote_username, quote_text)
            source = find_one(tweet_detail, 'source')
            text += '\n\nSource: {}'.format(convert_html_to_text(source))
            tweet_link = "https://x.com/{}/status/{}".format(self.user_id, tweet_id)
            text += f"\nLink: {tweet_link}"
            self.send_message(text, photo_url_list, video_url_list)

        self.update_last_watch_time()
        return True

    def status(self) -> str:
        return 'Last: {}, id: {}'.format(self.get_last_watch_time(), self.last_tweet_id)
