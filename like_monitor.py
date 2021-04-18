#!/usr/bin/python3
"""
Because the twitter api only allows to query the last 200 tweets sorted by creation time, we cannot know if the user likes a very old tweet.
"""

import click
from datetime import datetime, timedelta
import logging
import json

from sleeper import Sleeper
from telegram_notifier import TelegramNotifier
from utils import send_get_request, get_user_id, get_like_id_set, init_logging


class LikeMonitor:

    def __init__(self, username: str, telegram_chat_ids: str):
        self.sleeper = Sleeper(60)
        self.username = username
        self.existing_like_id_set = get_like_id_set(self.get_likes())
        logging.info('Init monitor succeed.\nUsername: {}\nLike ids: {}'.format(self.username, self.existing_like_id_set))
        self.telegram_notifier = TelegramNotifier(
                chat_ids=telegram_chat_ids, username=username, module='Like')
        self.last_log_time = datetime.now()


    def get_likes(self, max_number: int=200) -> list:
        url = 'https://api.twitter.com/1.1/favorites/list.json'
        params = { 'screen_name': self.username, 'count': max_number }
        json_response = send_get_request(url, params)
        while not json_response:
            self.sleeper.sleep(normal=False)
            json_response = send_get_request(url, params)
        return json_response


    def run(self):
        while True:
            self.sleeper.sleep(normal=True)
            likes = self.get_likes()
            for like in likes:
                if like['id'] not in self.existing_like_id_set:
                    self.telegram_notifier.send_message('@{}: {}'.format(like['user']['screen_name'], like['text']))
            self.existing_like_id_set |= get_like_id_set(likes)
            if datetime.now() - self.last_log_time > timedelta(hours=1):
                logging.info('Existing like id number: {}'.format(len(self.existing_like_id_set)))
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
    like_monitor = LikeMonitor(username, telegram_chat_ids)
    like_monitor.run()


if __name__ == '__main__':
    cli()
