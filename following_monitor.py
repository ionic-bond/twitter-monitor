#!/usr/bin/python3

import click
from datetime import datetime, timedelta
import json
import logging

from sleeper import Sleeper
from telegram_notifier import TelegramNotifier
from utils import send_get_request, get_user_id, init_logging


class FollowingMonitor:

    def __init__(self, username: str, telegram_chat_ids: str):
        self.sleeper = Sleeper(120)
        self.username = username
        self.user_id = get_user_id(username)
        self.following_users = self.get_all_following_users(self.user_id)
        logging.info('Init monitor succeed.\nUsername: {}\nUser id: {}\nFollowing users: {}'.format(
            username, self.user_id, self.following_users))
        self.telegram_notifier = TelegramNotifier(chat_ids=telegram_chat_ids,
                                                  username=username,
                                                  module='Following')
        self.last_log_time = datetime.now()

    def get_all_following_users(self, user_id: str) -> set:
        url = 'https://api.twitter.com/2/users/{}/following'.format(user_id)
        params = {'max_results': 1000}
        json_response = send_get_request(url, params)
        while not json_response:
            self.sleeper.sleep(normal=False)
            json_response = send_get_request(url, params)
        results = json_response.get('data', [])
        next_token = json_response.get('meta', {}).get('next_token', '')
        while next_token:
            params['pagination_token'] = next_token
            json_response = send_get_request(url, params)
            while not json_response:
                self.sleeper.sleep(normal=False)
                json_response = send_get_request(url, params)
            results.extend(json_response.get('data', []))
            next_token = json_response.get('meta', {}).get('next_token', '')
        return set([result.get('username', '') for result in results])

    def get_user_details(self, username: str) -> str:
        url = 'https://api.twitter.com/2/users/by/username/{}'.format(username)
        params = {'user.fields': 'name,description,url,created_at,public_metrics'}
        json_response = send_get_request(url, params)
        errors = json_response.get('errors', None)
        if errors:
            return errors.get('detail', '')
        data = json_response.get('data', {})
        details_str = 'Name: {}'.format(data.get('name', ''))
        details_str += '\nBio: {}'.format(data.get('description', ''))
        details_str += '\nWebsite: {}'.format(data.get('url', ''))
        details_str += '\nJoined at: {}'.format(data.get('created_at', ''))
        public_metrics = data.get('public_metrics', {})
        details_str += '\nFollowing: {}'.format(public_metrics.get('following_count', -1))
        details_str += '\nFollowers: {}'.format(public_metrics.get('followers_count', -1))
        details_str += '\nTweets: {}'.format(public_metrics.get('tweet_count', -1))
        if public_metrics.get('following_count', 2000) < 2000:
            following_users = self.get_all_following_users(get_user_id(username))
            details_str += '\nFollow each other: {}'.format('Yes' if self.username in following_users else 'No')
        return details_str

    def detect_changes(self, old_following_users: set, new_following_users: set):
        if old_following_users == new_following_users:
            return
        max_changes = max(len(old_following_users) / 2, 10)
        if abs(len(old_following_users) - len(new_following_users)) > max_changes:
            return
        dec_users = old_following_users - new_following_users
        if dec_users:
            logging.info('Unfollow: {}'.format(dec_users))
            for dec_user in dec_users:
                self.telegram_notifier.send_message('Unfollow: @{}\n{}'.format(dec_user, self.get_user_details(dec_user)), disable_preview=True)
        inc_users = new_following_users - old_following_users
        if inc_users:
            logging.info('Follow: {}'.format(inc_users))
            for inc_user in inc_users:
                self.telegram_notifier.send_message('Follow: @{}\n{}'.format(inc_user, self.get_user_details(inc_user)), disable_preview=True)

    def run(self):
        while True:
            self.sleeper.sleep(normal=True)
            following_users = self.get_all_following_users(self.user_id)
            self.detect_changes(self.following_users, following_users)
            self.following_users = following_users
            if datetime.now() - self.last_log_time > timedelta(hours=1):
                logging.info('Number of following users: {}'.format(len(self.following_users)))
                self.last_log_time = datetime.now()


@click.group()
def cli():
    pass


@cli.command()
@click.option('--username', required=True, help='Monitoring username.')
@click.option('--log_path', default=None, help='Path to output logging\'s log.')
@click.option('--telegram_chat_ids', required=False, help='Telegram char ids, separate by comma.')
def run(username, log_path, telegram_chat_ids):
    init_logging(log_path)
    following_monitor = FollowingMonitor(username, telegram_chat_ids)
    following_monitor.run()


if __name__ == '__main__':
    cli()
