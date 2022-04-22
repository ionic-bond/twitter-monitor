#!/usr/bin/python3

import logging
from datetime import datetime
from functools import cached_property
from typing import List, Union

from monitor_base import MonitorBase
from telegram_notifier import TelegramNotifier
from twitter_watcher import TwitterWatcher

MESSAGE_TEMPLATE = '{} changed\nOld: {}\nNew: {}'


class ProfileParser():

    def __init__(self, user: dict):
        self.user = user

    @cached_property
    def name(self) -> str:
        return self.user.get('name', '')

    @cached_property
    def username(self) -> str:
        return self.user.get('screen_name', '')

    @cached_property
    def location(self) -> str:
        return self.user.get('location', '')

    @cached_property
    def bio(self) -> str:
        return self.user.get('description', '')

    @cached_property
    def website(self) -> str:
        return self.user.get('entities', {}).get('url', {}).get('urls', [{}])[0].get(
            'expanded_url', '')

    @cached_property
    def followers_count(self) -> int:
        return self.user.get('followers_count', 0)

    @cached_property
    def following_count(self) -> int:
        return self.user.get('friends_count', 0)

    @cached_property
    def like_count(self) -> int:
        return self.user.get('favourites_count', 0)

    @cached_property
    def tweet_count(self) -> int:
        return self.user.get('statuses_count', 0)

    @cached_property
    def profile_image_url(self) -> str:
        return self.user.get('profile_image_url', '').replace('_normal', '')

    @cached_property
    def profile_banner_url(self) -> str:
        return self.user.get('profile_banner_url', '')


class ProfileMonitor(MonitorBase):

    def __init__(self, token_config: dict, username: str, telegram_chat_id_list: List[str]):
        self.twitter_watcher = TwitterWatcher(token_config['twitter_bearer_token_list'])
        self.user_id = self.twitter_watcher.get_id_by_username(username)

        user = None
        while not user:
            user = self.get_user()
        parser = ProfileParser(user)
        self.name = parser.name
        self.username = parser.username
        self.location = parser.location
        self.bio = parser.bio
        self.website = parser.website
        self.followers_count = parser.followers_count
        self.following_count = parser.following_count
        self.like_count = parser.like_count
        self.tweet_count = parser.tweet_count
        self.profile_image_url = parser.profile_image_url
        self.profile_banner_url = parser.profile_banner_url

        self.telegram_notifier = TelegramNotifier(
            token=token_config['telegram_bot_token'],
            chat_id_list=telegram_chat_id_list,
            username=username,
            module='Profile')
        self.logger = logging.getLogger('{}-Profile'.format(username))
        self.logger.info('Init profile monitor succeed.\n{}'.format(self.__dict__))
        self.last_watch_time = datetime.now()

    def get_user(self) -> Union[dict, None]:
        # Use v1 API because v2 API doesn't provide like_count.
        url = 'https://api.twitter.com/1.1/users/show.json'
        params = {'user_id': self.user_id}
        user = self.twitter_watcher.query(url, params)
        if user.get('errors', None):
            self.logger.error('\n'.join([error['message'] for error in user['errors']]))
            return None
        return user

    def detect_change_and_update(self, user: dict):
        parser = ProfileParser(user)
        if self.name != parser.name:
            self.logger.info(message=MESSAGE_TEMPLATE.format('Name', self.name, parser.name))
            self.name = parser.name
        if self.username != parser.username:
            self.logger.info(
                message=MESSAGE_TEMPLATE.format('Username', self.username, parser.username))
            self.username = parser.username
        if self.location != parser.location:
            self.logger.info(
                message=MESSAGE_TEMPLATE.format('Location', self.location, parser.location))
            self.location = parser.location
        if self.bio != parser.bio:
            self.logger.info(message=MESSAGE_TEMPLATE.format('Bio', self.bio, parser.bio))
            self.bio = parser.bio
        if self.website != parser.website:
            self.logger.info(
                message=MESSAGE_TEMPLATE.format('Website', self.website, parser.website))
            self.website = parser.website
        if self.followers_count != parser.followers_count:
            self.followers_count = parser.followers_count
        if self.following_count != parser.following_count:
            self.logger.info(
                MESSAGE_TEMPLATE.format('Following count', self.following_count,
                                        parser.following_count))
            self.following_count = parser.following_count
        if self.like_count != parser.like_count:
            self.logger.info(
                MESSAGE_TEMPLATE.format('Like count', self.like_count, parser.like_count))
            self.like_count = parser.like_count
        if self.tweet_count != parser.tweet_count:
            self.logger.info(
                MESSAGE_TEMPLATE.format('Tweet count', self.tweet_count, parser.tweet_count))
            self.tweet_count = parser.tweet_count
        if self.profile_image_url != parser.profile_image_url:
            self.logger.info(
                message=MESSAGE_TEMPLATE.format('Profile image', self.profile_image_url,
                                                parser.profile_image_url))
            self.profile_image_url = parser.profile_image_url
        if self.profile_banner_url != parser.profile_banner_url:
            self.logger.info(
                message=MESSAGE_TEMPLATE.format('Profile banner', self.profile_banner_url,
                                                parser.profile_banner_url))
            self.profile_banner_url = parser.profile_banner_url

    def watch(self):
        user = self.get_user()
        if not user:
            return
        self.detect_change_and_update(user)
        self.last_watch_time = datetime.now()

    def status(self) -> str:
        return 'Last: {}'.format(self.last_watch_time)
