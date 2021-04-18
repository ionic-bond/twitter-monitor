#!/usr/bin/python3

import click
import logging

from sleeper import Sleeper
from telegram_notifier import TelegramNotifier
from utils import send_get_request, get_user_id, init_logging


class FollowingMonitor:

    def __init__(self, username: str, telegram_chat_ids: str):
        self.sleeper = Sleeper(60)
        self.user_id = get_user_id(username)
        self.following_users = self.get_all_following_users()
        logging.info('Init monitor succeed.\nUsername: {}\nUser id: {}\nFollowing users: {}'.format(
            username, self.user_id, self.following_users))
        self.telegram_notifier = TelegramNotifier(
                chat_ids=telegram_chat_ids, username=username, module='Following')


    def get_all_following_users(self) -> set:
        url = 'https://api.twitter.com/2/users/{}/following'.format(self.user_id)
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


    def detect_changes(self, old_following_users: set, new_following_users: set):
        if old_following_users == new_following_users:
            return
        max_changes = max(len(old_following_users) / 2, 10)
        if abs(len(old_following_users) - len(new_following_users)) > max_changes:
            return
        dec_users = old_following_users - new_following_users
        if dec_users:
            self.telegram_notifier.send_message('Unfollow: {}'.format(dec_users))
        inc_users = new_following_users - old_following_users
        if inc_users:
            self.telegram_notifier.send_message('Follow: {}'.format(inc_users))


    def run(self):
        count = 0
        while True:
            self.sleeper.sleep(normal=True)
            following_users = self.get_all_following_users()
            count += 1
            if count % 10 == 0:
                logging.info('Number of following users: {}'.format(len(following_users)))
            self.detect_changes(self.following_users, following_users)
            self.following_users = following_users


@click.group()
def cli():
    pass


@cli.command()
@click.option('--username', required=True, help="Monitoring username.")
@click.option('--log_path', default=None, help="Path to output logging's log.")
@click.option('--telegram_chat_ids', required=False, help="Telegram char ids, separate by comma.")
def run(username, log_path, telegram_chat_ids):
    init_logging(log_path)
    following_monitor = FollowingMonitor(username, telegram_chat_ids)
    following_monitor.run()


if __name__ == "__main__":
    cli()
