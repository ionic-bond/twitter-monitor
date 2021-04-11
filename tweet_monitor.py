#!/usr/bin/python3

import click
import logging

from sleeper import Sleeper
from telegram_notifier import TelegramNotifier
from utils import send_get_request, get_user_id


class Monitor:

    def __init__(self, username: str, telegram_chat_id: str):
        self.sleeper = Sleeper(10)
        self.user_id = get_user_id(username)
        tweets = self.get_tweets()
        self.last_tweet_id = tweets[0]['id']
        logging.info('Init monitor succeed.\nUsername: {}\nUser id: {}\nLast tweet: {}'.format(
            username, self.user_id, tweets[0]))
        self.telegram_notifier = TelegramNotifier(chat_id=telegram_chat_id, bot_name=username)


    def get_tweets(self, since_id: str=None) -> set:
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
        count = 0
        while True:
            self.sleeper.sleep(normal=True)
            tweets = self.get_tweets(since_id=self.last_tweet_id)
            if tweets:
                for tweet in tweets:
                    self.telegram_notifier.send_message(tweet['text'])
                self.last_tweet_id = tweets[0]['id']
            count += 1
            if count % 10 == 0:
                logging.info('Last tweet id: {}'.format(self.last_tweet_id))


@click.group()
def cli():
    pass


@cli.command()
@click.option('--username', required=True, help="Monitoring username.")
@click.option('--log_path',
              default='/tmp/twitter_following_monitor.log',
              help="Path to output logging's log.")
@click.option('--telegram_chat_id', required=False, help="Telegram char id.")
def run(username, log_path, telegram_chat_id):
    logging.basicConfig(filename=log_path, format='%(asctime)s - %(message)s', level=logging.INFO)
    monitor = Monitor(username, telegram_chat_id)
    monitor.run()


if __name__ == "__main__":
    cli()
