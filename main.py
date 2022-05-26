#!/usr/bin/python3

import json
import logging
import math
import os
import sys
from datetime import datetime, timedelta

import click
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.background import BlockingScheduler

from following_monitor import FollowingMonitor
from like_monitor import LikeMonitor
from profile_monitor import ProfileMonitor
from telegram_notifier import TelegramNotifier
from tweet_monitor import TweetMonitor
from twitter_watcher import TwitterWatcher

PROFILE_LIMIT = 60
FOLLOWING_LIMIT = 1
LIKE_LIMIT = 5
TWEET_LIMIT = 60


def _get_interval_second(limit_per_minute: int, token_number: int, widget: int, widget_sum: int):
    return max(10, math.ceil((60 * widget_sum) / (limit_per_minute * token_number * widget)))


def _setup_logger(name: str, log_file_path: str, level=logging.INFO):
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(file_handler)


def _send_summary(notifier: TelegramNotifier, monitors: dict, watcher: TwitterWatcher):
    for modoule, data in monitors.items():
        monitor_status = {}
        for username, monitor in data.items():
            monitor_status[username] = monitor.status()
        notifier.send_message('{}: {}'.format(modoule, json.dumps(monitor_status, indent=4)))
    token_status = watcher.check_token()
    notifier.send_message('Token status: {}'.format(json.dumps(token_status, indent=4)))


def _check_monitors_are_working(notifier: TelegramNotifier, monitors: dict):
    time_threshold = datetime.utcnow() - timedelta(minutes=30)
    alerts = []
    for modoule, data in monitors.items():
        for username, monitor in data.items():
            if monitor.last_watch_time < time_threshold:
                alerts.append('{}-{}: {}'.format(modoule, username, monitor.last_watch_time))
    if alerts:
        notifier.send_message('Alert: \n{}'.format('\n'.join(alerts)))


@click.group()
def cli():
    pass


@cli.command()
@click.option('--log_dir', default=os.path.join(sys.path[0], 'log'))
@click.option('--token_config_path', default=os.path.join(sys.path[0], 'config/token.json'))
@click.option(
    '--monitoring_config_path', default=os.path.join(sys.path[0], 'config/monitoring.json'))
@click.option(
    '--confirm/--no-confirm',
    default=False,
    help="Confirm with the maintainer during initialization")
def run(log_dir, token_config_path, monitoring_config_path, confirm):
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

    weight_sum_offset = monitoring_config.get('weight_sum_offset', 0)
    profile_weight_sum = weight_sum_offset
    following_weight_sum = weight_sum_offset
    like_weight_sum = weight_sum_offset
    tweet_weight_sum = weight_sum_offset
    for monitoring_user in monitoring_config['monitoring_user_list']:
        if monitoring_user.get('monitoring_profile', False):
            profile_weight_sum += monitoring_user['weight']
        if monitoring_user.get('monitoring_following', False):
            following_weight_sum += monitoring_user['weight']
        if monitoring_user.get('monitoring_like', False):
            like_weight_sum += monitoring_user['weight']
        if monitoring_user.get('monitoring_tweet', False):
            tweet_weight_sum += monitoring_user['weight']

    token_number = len(token_config['twitter_bearer_token_list'])
    monitors = {
        'profile': {},
        'following': {},
        'like': {},
        'tweet': {},
    }
    intervals = {
        'profile': {},
        'following': {},
        'like': {},
        'tweet': {},
    }
    executors = {'default': ThreadPoolExecutor(len(monitoring_config['monitoring_user_list']) * 3)}
    scheduler = BlockingScheduler(executors=executors)
    for monitoring_user in monitoring_config['monitoring_user_list']:
        username = monitoring_user['username']
        telegram_chat_id_list = monitoring_user['telegram_chat_id_list']
        weight = monitoring_user['weight']
        if monitoring_user.get('monitoring_profile', False):
            logger_name = '{}-Profile'.format(username)
            _setup_logger(logger_name, os.path.join(log_dir, logger_name))
            intervals['profile'][username] = _get_interval_second(PROFILE_LIMIT, token_number,
                                                                  weight, profile_weight_sum)
            monitors['profile'][username] = ProfileMonitor(token_config, username,
                                                           telegram_chat_id_list)
            scheduler.add_job(
                monitors['profile'][username].watch,
                trigger='interval',
                seconds=intervals['profile'][username])
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
        twitter_watcher = TwitterWatcher(token_config['twitter_bearer_token_list'])
        telegram_notifier.send_message('Interval: {}'.format(json.dumps(intervals, indent=4)))
        _send_summary(telegram_notifier, monitors, twitter_watcher)
        if confirm:
            if not telegram_notifier.confirm('Please confirm the initialization information'):
                telegram_notifier.send_message('Monitor will exit now.')
                raise RuntimeError('Initialization information confirm error')
            telegram_notifier.send_message('Monitor initialization succeeded.')
        scheduler.add_job(
            _send_summary,
            trigger='cron',
            hour='6',
            args=[telegram_notifier, monitors, twitter_watcher])
        scheduler.add_job(
            _check_monitors_are_working,
            trigger='cron',
            hour='*',
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
