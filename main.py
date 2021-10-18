#!/usr/bin/python3

import json
import logging
import math
import os
import sys

import click
from apscheduler.schedulers.background import BlockingScheduler

from following_monitor import FollowingMonitor
from like_monitor import LikeMonitor
from telegram_notifier import TelegramNotifier
from tweet_monitor import TweetMonitor
from twitter_watcher import TwitterWatcher

FOLLOWING_LIMIT = 1
LIKE_LIMIT = 5
TWEET_LIMIT = 60


def _get_interval_second(limit_per_minute: int, token_number: int, widget: int, widget_sum: int):
    return max(5, math.ceil((60 * widget_sum) / (limit_per_minute * token_number * widget)))


def _setup_logger(name: str, log_file_path: str, level=logging.INFO):
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(file_handler)


def _summary_status(monitors: dict) -> str:
    result = dict()
    for modoule, data in monitors.items():
        result[modoule] = {}
        for username, monitor in data.items():
            result[modoule][username] = monitor.status()
    return json.dumps(result, indent=4)


@click.group()
def cli():
    pass


@cli.command()
@click.option('--log_dir', default=os.path.join(sys.path[0], 'log'))
@click.option('--token_config_path', default=os.path.join(sys.path[0], 'config/token.json'))
@click.option(
    '--monitoring_config_path', default=os.path.join(sys.path[0], 'config/monitoring.json'))
def run(log_dir, token_config_path, monitoring_config_path):
    os.makedirs(log_dir, exist_ok=True)
    logging.basicConfig(
        filename=os.path.join(log_dir, 'main'),
        format='%(asctime)s - %(levelname)s - %(message)s',
        level=logging.WARNING)
    _setup_logger('twitter', os.path.join(log_dir, 'twitter-api'))
    _setup_logger('Maintainer-Scheduler', os.path.join(log_dir, 'scheduler'))

    with open(os.path.join(token_config_path), 'r') as token_config_file:
        token_config = json.load(token_config_file)
        assert token_config['telegram_bot_token']
        assert token_config['twitter_bearer_token_list']
    with open(os.path.join(monitoring_config_path), 'r') as monitoring_config_file:
        monitoring_config = json.load(monitoring_config_file)
        assert monitoring_config['monitoring_user_list']

    following_weight_sum = 0
    like_weight_sum = 0
    tweet_weight_sum = 0
    for monitoring_user in monitoring_config['monitoring_user_list']:
        if monitoring_user.get('monitoring_following', False):
            following_weight_sum += monitoring_user['weight']
        if monitoring_user.get('monitoring_like', False):
            like_weight_sum += monitoring_user['weight']
        if monitoring_user.get('monitoring_tweet', False):
            tweet_weight_sum += monitoring_user['weight']

    token_number = len(token_config['twitter_bearer_token_list'])
    monitors = {
        'following': {},
        'like': {},
        'tweet': {},
    }
    intervals = {
        'following': {},
        'like': {},
        'tweet': {},
    }
    scheduler = BlockingScheduler()
    for monitoring_user in monitoring_config['monitoring_user_list']:
        username = monitoring_user['username']
        telegram_chat_id_list = monitoring_user['telegram_chat_id_list']
        weight = monitoring_user['weight']
        if monitoring_user.get('monitoring_following', False):
            logger_name = '{}-Following'.format(username)
            _setup_logger(logger_name, os.path.join(log_dir, logger_name))
            intervals['following'][username] = _get_interval_second(FOLLOWING_LIMIT, token_number,
                                                                    weight, following_weight_sum)
            monitors['following'][username] = FollowingMonitor(token_config, username,
                                                               telegram_chat_id_list)
            scheduler.add_job(
                monitors['following'][username].watch,
                trigger='interval',
                seconds=intervals['following'][username])
        if monitoring_user.get('monitoring_like', False):
            logger_name = '{}-Like'.format(username)
            _setup_logger(logger_name, os.path.join(log_dir, logger_name))
            intervals['like'][username] = _get_interval_second(LIKE_LIMIT, token_number, weight,
                                                               like_weight_sum)
            monitors['like'][username] = LikeMonitor(token_config, username, telegram_chat_id_list)
            scheduler.add_job(
                monitors['like'][username].watch,
                trigger='interval',
                seconds=intervals['like'][username])
        if monitoring_user.get('monitoring_tweet', False):
            logger_name = '{}-Tweet'.format(username)
            _setup_logger(logger_name, os.path.join(log_dir, logger_name))
            intervals['tweet'][username] = _get_interval_second(TWEET_LIMIT, token_number, weight,
                                                                tweet_weight_sum)
            monitors['tweet'][username] = TweetMonitor(token_config, username,
                                                       telegram_chat_id_list)
            scheduler.add_job(
                monitors['tweet'][username].watch,
                trigger='interval',
                seconds=intervals['tweet'][username])

    if monitoring_config['maintainer_chat_id']:
        telegram_notifier = TelegramNotifier(token_config['telegram_bot_token'],
                                             [monitoring_config['maintainer_chat_id']],
                                             'Maintainer', 'Scheduler')
        telegram_notifier.send_message('Interval:\n{}'.format(json.dumps(intervals, indent=4)))
        scheduler.add_job(
            lambda tg_notifier, monitors: tg_notifier.send_message(_summary_status(monitors)),
            trigger='cron',
            hour='0,12',
            args=[telegram_notifier, monitors])

    scheduler.start()


@cli.command()
@click.option('--token_config_path', default=os.path.join(sys.path[0], 'config/token.json'))
@click.option('--telegram_chat_id')
def check_token(token_config_path, telegram_chat_id):
    with open(os.path.join(token_config_path), 'r') as token_config_file:
        token_config = json.load(token_config_file)
        assert token_config['telegram_bot_token']
        assert token_config['twitter_bearer_token_list']
    twitter_watcher = TwitterWatcher(token_config['twitter_bearer_token_list'])
    result = json.dumps(twitter_watcher.check_token(), indent=4)
    print(result)
    if telegram_chat_id:
        telegram_notifier = TelegramNotifier(token_config['telegram_bot_token'], [telegram_chat_id],
                                             '', '')
        telegram_notifier.send_message(result)


if __name__ == '__main__':
    cli()
