#!/usr/bin/python3

import logging
from datetime import datetime
from typing import List, Union, Tuple, Dict

from telegram_notifier import TelegramNotifier
from twitter_watcher import TwitterWatcher


class FollowingMonitor:

    def __init__(self, token_config: dict, username: str, telegram_chat_id_list: List[str]):
        self.twitter_watcher = TwitterWatcher(token_config['twitter_bearer_token_list'])
        self.user_id = self.twitter_watcher.get_id_by_username(username, {})
        self.following_dict = None
        while self.following_dict is None:
            self.following_dict = self.get_all_following(self.user_id)
        self.telegram_notifier = TelegramNotifier(
            token=token_config['telegram_bot_token'],
            chat_id_list=telegram_chat_id_list,
            username=username,
            module='Following')
        self.logger = logging.getLogger('{}-Following'.format(username))
        self.logger.info(
            'Init following monitor succeed.\nUsername: {}\nUser id: {}\nFollowing users: {}'.
            format(username, self.user_id,
                   [user['username'] for user in self.following_dict.values()]))
        self.last_watch_time = datetime.now()

    def get_all_following(self, user_id: str) -> Union[Dict[str, dict], None]:
        url = 'https://api.twitter.com/2/users/{}/following'.format(user_id)
        params = {'max_results': 1000}
        json_response = self.twitter_watcher.query(url, params)
        if not json_response:
            return None
        users = json_response['data']
        next_token = json_response['meta'].get('next_token', '')
        while next_token:
            params['pagination_token'] = next_token
            json_response = self.twitter_watcher.query(url, params)
            if not json_response:
                return None
            users.extend(json_response['data'])
            next_token = json_response['meta'].get('next_token', '')
        result = dict()
        for user in users:
            result[user['id']] = user
        return result

    def get_user_details(self, user_id: str) -> Tuple[str, str]:
        params = {'user.fields': 'name,description,url,created_at,public_metrics,profile_image_url'}
        user = self.twitter_watcher.get_user_by_id(user_id, params)
        if user.get('errors', None):
            return '\n'.join([error['detail'] for error in user['errors']])
        data = user['data']
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
            following_dict = None
            while following_dict is None:
                following_dict = self.get_all_following(user_id)
            details_str += '\nFollow each other: {}'.format(self.user_id in following_dict.keys())
        return details_str, data.get('profile_image_url', '')

    def detect_changes(self, old_following_dict: set, new_following_dict: set):
        if old_following_dict.keys() == new_following_dict.keys():
            return
        max_changes = max(len(old_following_dict) / 2, 10)
        dec_user_ids = old_following_dict.keys() - new_following_dict.keys()
        inc_user_ids = new_following_dict.keys() - old_following_dict.keys()
        if len(dec_user_ids) > max_changes or len(inc_user_ids) > max_changes:
            return
        if dec_user_ids:
            for dec_user_id in dec_user_ids:
                message = 'Unfollow: @{}'.format(old_following_dict[dec_user_id]['username'])
                details_str, profile_image_url = self.get_user_details(dec_user_id)
                if details_str:
                    message += '\n{}'.format(details_str)
                self.telegram_notifier.send_message(
                    message=message, photo_url=profile_image_url, disable_preview=True)
        if inc_user_ids:
            for inc_user_id in inc_user_ids:
                message = 'Follow: @{}'.format(new_following_dict[inc_user_id]['username'])
                details_str, profile_image_url = self.get_user_details(inc_user_id)
                if details_str:
                    message += '\n{}'.format(details_str)
                self.telegram_notifier.send_message(
                    message=message, photo_url=profile_image_url, disable_preview=True)

    def watch(self):
        following_dict = self.get_all_following(self.user_id)
        if not following_dict:
            return
        self.detect_changes(self.following_dict, following_dict)
        self.following_dict = following_dict
        self.last_watch_time = datetime.now()

    def status(self) -> str:
        return 'Last watch time: {}, number of following users: {}'.format(
            self.last_watch_time, len(self.following_dict))
