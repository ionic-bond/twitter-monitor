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


class ElementBuffer():
    # For handling unstable twitter API results

    def __init__(self, element, change_threshold: int = 2):
        self.element = element
        self.change_threshold = change_threshold
        self.change_count = 0

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

    def __init__(self, token_config: dict, username: str, telegram_chat_id_list: List[str]):
        self.twitter_watcher = TwitterWatcher(token_config['twitter_bearer_token_list'])
        self.user_id = self.twitter_watcher.get_id_by_username(username)

        user = None
        while not user:
            user = self.get_user()
        parser = ProfileParser(user)
        self.name = ElementBuffer(parser.name)
        self.username = ElementBuffer(parser.username)
        self.location = ElementBuffer(parser.location)
        self.bio = ElementBuffer(parser.bio)
        self.website = ElementBuffer(parser.website)
        self.followers_count = ElementBuffer(parser.followers_count)
        self.following_count = ElementBuffer(parser.following_count)
        self.like_count = ElementBuffer(parser.like_count)
        self.tweet_count = ElementBuffer(parser.tweet_count)
        self.profile_image_url = ElementBuffer(parser.profile_image_url)
        self.profile_banner_url = ElementBuffer(parser.profile_banner_url)

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

        result = self.name.push(parser.name)
        if result:
            self.telegram_notifier.send_message(
                message=MESSAGE_TEMPLATE.format('Name', result['old'], result['new']),
                disable_preview=True)

        result = self.username.push(parser.username)
        if result:
            self.telegram_notifier.send_message(
                message=MESSAGE_TEMPLATE.format('Username', result['old'], result['new']),
                disable_preview=True)

        result = self.location.push(parser.location)
        if result:
            self.telegram_notifier.send_message(
                message=MESSAGE_TEMPLATE.format('Location', result['old'], result['new']),
                disable_preview=True)

        result = self.bio.push(parser.bio)
        if result:
            self.telegram_notifier.send_message(
                message=MESSAGE_TEMPLATE.format('Bio', result['old'], result['new']),
                disable_preview=True)

        result = self.website.push(parser.website)
        if result:
            self.telegram_notifier.send_message(
                message=MESSAGE_TEMPLATE.format('Website', result['old'], result['new']),
                disable_preview=True)

        result = self.followers_count.push(parser.followers_count)

        result = self.following_count.push(parser.following_count)
        if result:
            self.logger.info(
                MESSAGE_TEMPLATE.format('Following count', result['old'], result['new']))

        result = self.like_count.push(parser.like_count)
        if result:
            self.logger.info(MESSAGE_TEMPLATE.format('Like count', result['old'], result['new']))

        result = self.tweet_count.push(parser.tweet_count)
        if result:
            self.logger.info(MESSAGE_TEMPLATE.format('Tweet count', result['old'], result['new']))

        result = self.profile_image_url.push(parser.profile_image_url)
        if result:
            self.telegram_notifier.send_message(
                message=MESSAGE_TEMPLATE.format('Profile image', result['old'], result['new']),
                photo_url_list=[result['old'], result['new']])

        result = self.profile_banner_url.push(parser.profile_banner_url)
        if result:
            self.telegram_notifier.send_message(
                message=MESSAGE_TEMPLATE.format('Profile banner', result['old'], result['new']),
                photo_url_list=[result['old'], result['new']])

    def watch(self):
        user = self.get_user()
        if not user:
            return
        self.detect_change_and_update(user)
        self.last_watch_time = datetime.now()

    def status(self) -> str:
        return 'Last: {}'.format(self.last_watch_time)
