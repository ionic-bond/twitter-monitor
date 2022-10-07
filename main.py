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

from cqhttp_notifier import CqhttpNotifier
from following_monitor import FollowingMonitor
from like_monitor import LikeMonitor
from profile_monitor import ProfileMonitor
from telegram_notifier import TelegramMessage, TelegramNotifier
from tweet_monitor import TweetMonitor
from twitter_watcher import TwitterWatcher

CONFIG_FIELD_TO_MONITOR = {
    'monitoring_profile': ProfileMonitor,
    'monitoring_following': FollowingMonitor,
    'monitoring_like': LikeMonitor,
    'monitoring_tweet': TweetMonitor
}


def _get_interval_second(limit_per_minute: int, token_number: int, widget: int, widget_sum: int):
    return max(10, math.ceil((60 * widget_sum) / (limit_per_minute * token_number * widget)))


def _setup_logger(name: str, log_file_path: str, level=logging.INFO):
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(file_handler)


def _send_summary(telegram_chat_id: str, monitors: dict, watcher: TwitterWatcher):
    for modoule, data in monitors.items():
        monitor_status = {}
        for username, monitor in data.items():
            monitor_status[username] = monitor.status()
        TelegramNotifier.put_message_into_queue(TelegramMessage(chat_id_list=[telegram_chat_id], text='{}: {}'.format(modoule, json.dumps(monitor_status, indent=4))))
    token_status = watcher.check_token()
    TelegramNotifier.put_message_into_queue(TelegramMessage(chat_id_list=[telegram_chat_id], text='Token status: {}'.format(json.dumps(token_status, indent=4))))


def _check_monitors_status(telegram_chat_id: str, monitors: dict):
    time_threshold = datetime.utcnow() - timedelta(minutes=30)
    alerts = []
    for modoule, data in monitors.items():
        for username, monitor in data.items():
            if monitor.last_watch_time < time_threshold:
                alerts.append('{}-{}: {}'.format(modoule, username, monitor.last_watch_time))
    for username, monitor in monitors[ProfileMonitor.monitor_type].items():
        if monitor.username.element != username:
            alerts.append('{} username changed to {}'.format(username, monitor.username.element))
    if alerts:
        TelegramNotifier.put_message_into_queue(TelegramMessage(chat_id_list=[telegram_chat_id], text='Alert: \n{}'.format('\n'.join(alerts))))


@click.group()
def cli():
    pass


@cli.command()
@click.option('--log_dir', default=os.path.join(sys.path[0], 'log'))
@click.option('--token_config_path', default=os.path.join(sys.path[0], 'config/token.json'))
@click.option('--monitoring_config_path',
              default=os.path.join(sys.path[0], 'config/monitoring.json'))
@click.option('--confirm/--no-confirm',
              default=False,
              help="Confirm with the maintainer during initialization")
def run(log_dir, token_config_path, monitoring_config_path, confirm):
    os.makedirs(log_dir, exist_ok=True)
    logging.basicConfig(filename=os.path.join(log_dir, 'main'),
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

    _setup_logger('telegram', os.path.join(log_dir, 'telegram'))
    _setup_logger('cqhttp', os.path.join(log_dir, 'cqhttp'))
    TelegramNotifier.init(token=token_config['telegram_bot_token'], logger_name='telegram')
    CqhttpNotifier.init(token=token_config.get('cqhttp_access_token', ''), logger_name='cqhttp')

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
    monitors = dict()
    intervals = dict()
    for monitor_cls in CONFIG_FIELD_TO_MONITOR.values():
        monitors[monitor_cls.monitor_type] = dict()
        intervals[monitor_cls.monitor_type] = dict()
    executors = {'default': ThreadPoolExecutor(len(monitoring_config['monitoring_user_list']) * 3)}
    scheduler = BlockingScheduler(executors=executors)
    for monitoring_user in monitoring_config['monitoring_user_list']:
        username = monitoring_user['username']
        telegram_chat_id_list = monitoring_user.get('telegram_chat_id_list', None)
        cqhttp_url_list = monitoring_user.get('cqhttp_url_list', None)
        assert telegram_chat_id_list or cqhttp_url_list
        weight = monitoring_user['weight']
        for config_field, monitor_cls in CONFIG_FIELD_TO_MONITOR.items():
            if monitoring_user.get(config_field, False):
                monitor_type = monitor_cls.monitor_type
                logger_name = '{}-{}'.format(username, monitor_type)
                _setup_logger(logger_name, os.path.join(log_dir, logger_name))
                intervals[monitor_type][username] = _get_interval_second(
                    monitor_cls.rate_limit, token_number, weight, profile_weight_sum)
                monitors[monitor_type][username] = monitor_cls(username, token_config,
                                                               telegram_chat_id_list,
                                                               cqhttp_url_list)
                scheduler.add_job(monitors[monitor_type][username].watch,
                                  trigger='interval',
                                  seconds=intervals[monitor_type][username])

    if monitoring_config['maintainer_chat_id']:
        # maintainer_chat_id should be telegram chat id.
        maintainer_chat_id = monitoring_config['maintainer_chat_id']
        twitter_watcher = TwitterWatcher(token_config['twitter_bearer_token_list'])
        TelegramNotifier.put_message_into_queue(TelegramMessage(chat_id_list=[maintainer_chat_id], text='Interval: {}'.format(json.dumps(intervals, indent=4))))
        _send_summary(maintainer_chat_id, monitors, twitter_watcher)
        if confirm:
            if not TelegramNotifier.confirm(TelegramMessage(chat_id_list=[maintainer_chat_id], text='Please confirm the initialization information')):
                TelegramNotifier.put_message_into_queue(TelegramMessage(chat_id_list=[maintainer_chat_id], text='Monitor will exit now.'))
                raise RuntimeError('Initialization information confirm error')
            TelegramNotifier.put_message_into_queue(TelegramMessage(chat_id_list=[maintainer_chat_id], text='Monitor initialization succeeded.'))
        scheduler.add_job(_send_summary,
                          trigger='cron',
                          hour='6',
                          args=[maintainer_chat_id, monitors, twitter_watcher])
        scheduler.add_job(_check_monitors_status,
                          trigger='cron',
                          hour='*',
                          args=[maintainer_chat_id, monitors])

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
        TelegramNotifier.init(token_config['telegram_bot_token'], '')
        TelegramNotifier.send_message(TelegramMessage(chat_id_list=[telegram_chat_id], text=result))


if __name__ == '__main__':
    cli()
