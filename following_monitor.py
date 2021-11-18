#!/usr/bin/python3

import logging
from datetime import datetime
from typing import List, Union

from telegram_notifier import TelegramNotifier
from twitter_watcher import TwitterWatcher


class FollowingMonitor:

    def __init__(self, token_config: dict, username: str, telegram_chat_id_list: List[str]):
        self.username = username
        self.twitter_watcher = TwitterWatcher(token_config['twitter_bearer_token_list'])
        self.user_id = self.twitter_watcher.get_user_id(username)
        self.following_users = None
        while self.following_users is None:
            self.following_users = self.get_all_following_users(self.user_id)
        self.telegram_notifier = TelegramNotifier(
            token=token_config['telegram_bot_token'],
            chat_id_list=telegram_chat_id_list,
            username=username,
            module='Following')
        self.logger = logging.getLogger('{}-Following'.format(username))
        self.logger.info(
            'Init following monitor succeed.\nUsername: {}\nUser id: {}\nFollowing users: {}'.
            format(username, self.user_id, self.following_users))
        self.last_watch_time = datetime.now()

    def get_all_following_users(self, user_id: str) -> Union[set, None]:
        url = 'https://api.twitter.com/2/users/{}/following'.format(user_id)
        params = {'max_results': 1000}
        json_response = self.twitter_watcher.query(url, params)
        if not json_response:
            return None
        results = json_response['data']
        next_token = json_response['meta'].get('next_token', '')
        while next_token:
            params['pagination_token'] = next_token
            json_response = self.twitter_watcher.query(url, params)
            if not json_response:
                return None
            results.extend(json_response['data'])
            next_token = json_response['meta'].get('next_token', '')
        return set(result['username'] for result in results)

    def get_user_details(self, username: str) -> Union[str, None]:
        url = 'https://api.twitter.com/2/users/by/username/{}'.format(username)
        params = {'user.fields': 'name,description,url,created_at,public_metrics'}
        json_response = self.twitter_watcher.query(url, params)
        if not json_response:
            return None
        errors = json_response.get('errors', None)
        if errors:
            return '\n'.join([error['detail'] for error in errors])
        data = json_response['data']
        details_str = 'Name: {}'.format(data.get('name', ''))
        details_str += '\nBio: {}'.format(data.get('description', ''))
        website = data.get('url', '')
        if website:
            details_str += '\nWebsite: {}'.format(website)
        details_str += '\nJoined at: {}'.format(data.get('created_at', ''))
        public_metrics = data.get('public_metrics', {})
        details_str += '\nFollowing: {}'.format(public_metrics.get('following_count', -1))
        details_str += '\nFollowers: {}'.format(public_metrics.get('followers_count', -1))
        details_str += '\nTweets: {}'.format(public_metrics.get('tweet_count', -1))
        if public_metrics.get('following_count', 2000) < 2000:
            following_users = None
            while following_users is None:
                following_users = self.get_all_following_users(self.twitter_watcher.get_user_id(username))
            details_str += '\nFollow each other: {}'.format(self.username in following_users)
        return details_str

    def detect_changes(self, old_following_users: set, new_following_users: set):
        if old_following_users == new_following_users:
            return
        max_changes = max(len(old_following_users) / 2, 10)
        dec_users = old_following_users - new_following_users
        inc_users = new_following_users - old_following_users
        if len(dec_users) > max_changes or len(inc_users) > max_changes:
            return
        if dec_users:
            for dec_user in dec_users:
                message = 'Unfollow: @{}'.format(dec_user)
                details_str = self.get_user_details(dec_user)
                if details_str:
                    message += '\n{}'.format(details_str)
                self.telegram_notifier.send_message(message, disable_preview=True)
        if inc_users:
            for inc_user in inc_users:
                message = 'Follow: @{}'.format(inc_user)
                details_str = self.get_user_details(inc_user)
                if details_str:
                    message += '\n{}'.format(details_str)
                self.telegram_notifier.send_message(message, disable_preview=True)

    def watch(self):
        following_users = self.get_all_following_users(self.user_id)
        if not following_users:
            return
        self.detect_changes(self.following_users, following_users)
        self.following_users = following_users
        self.last_watch_time = datetime.now()

    def status(self) -> str:
        return 'Last watch time: {}, number of following users: {}'.format(
            self.last_watch_time, len(self.following_users))
