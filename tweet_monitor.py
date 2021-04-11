#!/usr/bin/python3

import click
import json
import logging
import os
import requests
import telegram
import time

MIN_SLEEP_SECOND = 30


class Sleeper:

    def __init__(self):
        self.sleep_second = MIN_SLEEP_SECOND
        self.normal_count = 0


    def sleep(self, normal: bool):
        if normal:
            self.normal_count += 1
            if self.normal_count > 20 and self.sleep_second > MIN_SLEEP_SECOND:
                self.sleep_second /= 2
                logging.info('Changed sleep second to {}'.format(self.sleep_second))
        else:
            self.normal_count = 0
            self.sleep_second *= 2
            logging.info('Changed sleep second to {}'.format(self.sleep_second))
        time.sleep(self.sleep_second)


class TelegramNotifier:

    def __init__(self, chat_id: str, bot_name: str):
        if not chat_id:
            logging.warning('Telegram id not set, skip initialization of telegram notifier.')
            self.bot = None
            return
        token = os.environ.get("TELEGRAM_TOKEN")
        self.bot = telegram.Bot(token=token)
        self.chat_id = chat_id
        self.bot_name = bot_name
        self.send_message('Init telegram bot succeed: {}'.format(self.bot.get_me()))


    def send_message(self, message: str):
        logging.info('Sending message: {}'.format(message))
        if not self.bot:
            logging.warning('Telegram notifier not initialized, skip.')
            return
        self.bot.send_message(chat_id=self.chat_id, text='[{}] {}'.format(self.bot_name, message))


class Monitor:

    def __init__(self, username: str, telegram_chat_id: str):
        self.sleeper = Sleeper()
        self.user_id = self.get_user_id(username)
        tweets = self.get_tweets()
        self.last_tweet_id = tweets[0]['id']
        logging.info('Init monitor succeed.\nUsername: {}\nUser id: {}\nLast tweet: {}'.format(
            username, self.user_id, tweets[0]))
        self.telegram_notifier = TelegramNotifier(chat_id=telegram_chat_id, bot_name=username)


    @staticmethod
    def get_headers():
        token = os.environ.get("BEARER_TOKEN")
        return {"Authorization": "Bearer {}".format(token)}


    def send_get_request(self, url: str, params: dict={}):
        headers = self.get_headers()
        response = requests.request("GET", url, headers=headers, params=params)
        while response.status_code != 200:
            logging.error("Request returned an error: {} {}".format(
                response.status_code, response.text))
            self.sleeper.sleep(normal=False)
            response = requests.request("GET", url, headers=headers, params=params)
        return response.json()


    def get_user_id(self, username: str) -> str:
        url = "https://api.twitter.com/2/users/by/username/{}".format(username)
        user = self.send_get_request(url)
        return user['data']['id']


    def get_tweets(self, since_id: str=None) -> set:
        url = 'https://api.twitter.com/2/users/{}/tweets'.format(self.user_id)
        params = {'max_results': 100}
        if since_id:
            params['since_id'] = since_id
        json_response = self.send_get_request(url, params)
        results = json_response.get('data', [])
        return results


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
