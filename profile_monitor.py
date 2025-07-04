import time
from functools import cached_property
from typing import Union

from following_monitor import FollowingMonitor
from like_monitor import LikeMonitor
from monitor_base import MonitorBase, MonitorManager
from tweet_monitor import TweetMonitor
from utils import find_one, get_content

MESSAGE_TEMPLATE = '{} changed\nOld: {}\nNew: {}'
SUB_MONITOR_LIST = [FollowingMonitor, LikeMonitor, TweetMonitor]


class ProfileParser():

    def __init__(self, json_response: dict):
        self.content = get_content(find_one(json_response, 'user'))
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
    def bio(self) -> str:
        return self.content.get('description', '')

    @cached_property
    def website(self) -> str:
        return self.content.get('entities', {}).get('url', {}).get('urls', [{}])[0].get('expanded_url', '')

    @cached_property
    def followers_count(self) -> int:
        return self.content.get('followers_count', 0)

    @cached_property
    def following_count(self) -> int:
        return self.content.get('friends_count', 0)

    @cached_property
    def like_count(self) -> int:
        return self.content.get('favourites_count', 0)

    @cached_property
    def tweet_count(self) -> int:
        return self.content.get('statuses_count', 0)

    @cached_property
    def profile_image_url(self) -> str:
        return find_one(self.json_response, 'avatar').get('image_url', '').replace('_normal', '')

    @cached_property
    def profile_banner_url(self) -> str:
        return self.content.get('profile_banner_url', '')

    @cached_property
    def pinned_tweet(self) -> str:
        pinned_tweet = self.content.get('pinned_tweet_ids_str', [])
        if not pinned_tweet:
            return None
        if isinstance(pinned_tweet, list):
            return pinned_tweet[0]
        return pinned_tweet

    @cached_property
    def highlighted_tweet_count(self) -> str:
        return find_one(self.json_response, 'highlighted_tweets')


class ElementBuffer():
    # For handling unstable twitter API results

    def __init__(self, element, change_threshold: int = 2):
        self.element = element
        self.change_threshold = change_threshold
        self.change_count = 0

    def __str__(self):
        return str(self.element)

    def __repr__(self):
        return str(self.element)

    def push(self, element) -> Union[dict, None]:
        if element == self.element:
            self.change_count = 0
            return None
        self.change_count += 1
        if self.change_count >= self.change_threshold:
            result = {'old': self.element, 'new': element}
            self.element = element
            self.change_count = 0
            return result
        return None


class ProfileMonitor(MonitorBase):
    monitor_type = 'Profile'

    def __init__(self, username: str, title: str, token_config: dict, user_config: dict, cookies_dir: str):
        super().__init__(monitor_type=self.monitor_type,
                         username=username,
                         title=title,
                         token_config=token_config,
                         user_config=user_config,
                         cookies_dir=cookies_dir)

        json_response = self.get_user()
        while not json_response:
            time.sleep(60)
            json_response = self.get_user()
        parser = ProfileParser(json_response)
        self.name = ElementBuffer(parser.name)
        self.username = ElementBuffer(parser.username)
        self.location = ElementBuffer(parser.location)
        self.bio = ElementBuffer(parser.bio)
        self.website = ElementBuffer(parser.website)
        self.followers_count = ElementBuffer(parser.followers_count)
        self.following_count = ElementBuffer(parser.following_count)
        self.like_count = ElementBuffer(parser.like_count)
        self.tweet_count = ElementBuffer(parser.tweet_count, change_threshold=1)
        self.profile_image_url = ElementBuffer(parser.profile_image_url)
        self.profile_banner_url = ElementBuffer(parser.profile_banner_url)
        self.pinned_tweet = ElementBuffer(parser.pinned_tweet)
        self.highlighted_tweet_count = ElementBuffer(parser.highlighted_tweet_count)

        self.monitoring_following_count = user_config.get('monitoring_following_count', False)
        self.monitoring_tweet_count = user_config.get('monitoring_tweet_count', False)
        self.monitoring_like_count = user_config.get('monitoring_like_count', False)

        self.title = title
        self.original_username = username
        self.sub_monitor_up_to_date = {}
        for sub_monitor in SUB_MONITOR_LIST:
            self.sub_monitor_up_to_date[sub_monitor.monitor_type] = True

        self.logger.info('Init profile monitor succeed.\n{}'.format(self.__dict__))

    def get_user(self) -> Union[dict, None]:
        params = {'userId': self.user_id}
        json_response = self.twitter_watcher.query('UserByRestId', params)
        if not find_one(json_response, 'user'):
            return None
        return json_response

    def detect_change_and_update(self, user: dict):
        parser = ProfileParser(user)

        result = self.name.push(parser.name)
        if result:
            self.send_message(message=MESSAGE_TEMPLATE.format('Name', result['old'], result['new']))

        result = self.username.push(parser.username)
        if result:
            self.send_message(message=MESSAGE_TEMPLATE.format('Username', result['old'], result['new']))

        result = self.location.push(parser.location)
        if result:
            self.send_message(message=MESSAGE_TEMPLATE.format('Location', result['old'], result['new']))

        result = self.bio.push(parser.bio)
        if result:
            self.send_message(message=MESSAGE_TEMPLATE.format('Bio', result['old'], result['new']))

        result = self.website.push(parser.website)
        if result:
            self.send_message(message=MESSAGE_TEMPLATE.format('Website', result['old'], result['new']))

        result = self.followers_count.push(parser.followers_count)

        result = self.following_count.push(parser.following_count)
        if result:
            if self.monitoring_following_count:
                self.send_message(message=MESSAGE_TEMPLATE.format('Following count', result['old'], result['new']))
            else:
                self.logger.info(MESSAGE_TEMPLATE.format('Following count', result['old'], result['new']))
            self.sub_monitor_up_to_date[FollowingMonitor.monitor_type] = False

        result = self.like_count.push(parser.like_count)
        if result:
            if self.monitoring_like_count:
                self.send_message(message=MESSAGE_TEMPLATE.format('Like count', result['old'], result['new']))
            else:
                self.logger.info(MESSAGE_TEMPLATE.format('Like count', result['old'], result['new']))
            if result['new'] > result['old']:
                self.sub_monitor_up_to_date[LikeMonitor.monitor_type] = False

        result = self.tweet_count.push(parser.tweet_count)
        if result:
            if self.monitoring_tweet_count:
                self.send_message(message=MESSAGE_TEMPLATE.format('Tweet count', result['old'], result['new']))
            else:
                self.logger.info(MESSAGE_TEMPLATE.format('Tweet count', result['old'], result['new']))
            if result['new'] > result['old']:
                self.sub_monitor_up_to_date[TweetMonitor.monitor_type] = False

        result = self.profile_image_url.push(parser.profile_image_url)
        if result:
            self.send_message(message=MESSAGE_TEMPLATE.format('Profile image', result['old'], result['new']),
                              photo_url_list=[result['old'], result['new']])

        result = self.profile_banner_url.push(parser.profile_banner_url)
        if result:
            self.send_message(message=MESSAGE_TEMPLATE.format('Profile banner', result['old'], result['new']),
                              photo_url_list=[result['old'], result['new']])

        result = self.pinned_tweet.push(parser.pinned_tweet)
        if result:
            self.send_message(message=MESSAGE_TEMPLATE.format('Pinned tweet', result['old'], result['new']))

        result = self.highlighted_tweet_count.push(parser.highlighted_tweet_count)
        if result:
            self.send_message(message=MESSAGE_TEMPLATE.format('Highlighted tweet', result['old'], result['new']))

    def watch_sub_monitor(self):
        for sub_monitor in SUB_MONITOR_LIST:
            sub_monitor_type = sub_monitor.monitor_type
            sub_monitor_instance = MonitorManager.get(monitor_type=sub_monitor_type, username=self.title)
            if sub_monitor_instance:
                if not self.sub_monitor_up_to_date[sub_monitor_type]:
                    self.sub_monitor_up_to_date[sub_monitor_type] = MonitorManager.call(monitor_type=sub_monitor_type,
                                                                                        username=self.title)
                else:
                    sub_monitor_instance.update_last_watch_time()

    def watch(self) -> bool:
        user = self.get_user()
        if not user:
            return False
        self.detect_change_and_update(user)
        self.watch_sub_monitor()
        self.update_last_watch_time()
        return True

    def status(self) -> str:
        return 'Last: {}, username: {}'.format(self.get_last_watch_time(), self.username.element)
