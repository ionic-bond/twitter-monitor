#!/usr/bin/python3

import click
from datetime import datetime, timedelta
import logging

from sleeper import Sleeper
from telegram_notifier import TelegramNotifier
from utils import send_get_request, get_user_id, init_logging


class TweetMonitor:

    def __init__(self, username: str, telegram_chat_ids: str):
        self.sleeper = Sleeper(10)
        self.user_id = get_user_id(username)
        tweets = self.get_tweets()
        self.last_tweet_id = tweets[0]['id']
        logging.info('Init monitor succeed.\nUsername: {}\nUser id: {}\nLast tweet: {}'.format(
            username, self.user_id, tweets[0]))
        self.telegram_notifier = TelegramNotifier(chat_ids=telegram_chat_ids,
                                                  username=username,
                                                  module='Tweet')
        self.last_log_time = datetime.now()

    def get_tweets(self, since_id: str = None) -> list:
        url = 'https://api.twitter.com/2/users/{}/tweets'.format(self.user_id)
        params = {'max_results': 100}
        if since_id:
            params['since_id'] = since_id
        json_response = send_get_request(url, params)
        while not json_response:
            self.sleeper.sleep(normal=False)
            json_response = send_get_request(url, params)
        return json_response.get('data', [])

    def run(self):
        while True:
            self.sleeper.sleep(normal=True)
            tweets = self.get_tweets(since_id=self.last_tweet_id)
            if tweets:
                for tweet in tweets:
                    self.telegram_notifier.send_message(tweet['text'])
                self.last_tweet_id = tweets[0]['id']
            if datetime.now() - self.last_log_time > timedelta(hours=1):
                logging.info('Last tweet id: {}'.format(self.last_tweet_id))
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
    tweet_monitor = TweetMonitor(username, telegram_chat_ids)
    tweet_monitor.run()


if __name__ == '__main__':
    cli()
