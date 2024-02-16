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
from graphql_api import GraphqlAPI
from like_monitor import LikeMonitor
from monitor_base import MonitorManager
from profile_monitor import ProfileMonitor
from telegram_notifier import TelegramMessage, TelegramNotifier, send_alert
from tweet_monitor import TweetMonitor
from twitter_watcher import TwitterWatcher
from utils import get_auth_handler, dump_auth_handler

CONFIG_FIELD_TO_MONITOR = {
    'monitoring_profile': ProfileMonitor,
    'monitoring_following': FollowingMonitor,
    'monitoring_like': LikeMonitor,
    'monitoring_tweet': TweetMonitor
}


def _get_interval_second(limit_per_minute: int, token_number: int, widget: int, widget_sum: int):
    return max(15, math.ceil((60 * widget_sum) / (limit_per_minute * token_number * widget)))


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
        TelegramNotifier.put_message_into_queue(
            TelegramMessage(chat_id_list=[telegram_chat_id],
                            text='{}: {}'.format(modoule, json.dumps(monitor_status, indent=4))))
    tokens_status = watcher.check_tokens()
    TelegramNotifier.put_message_into_queue(
        TelegramMessage(chat_id_list=[telegram_chat_id],
                        text='Tokens status: {}'.format(json.dumps(tokens_status, indent=4))))


def _check_monitors_status(telegram_token: str, telegram_chat_id: int, monitors: dict):
    time_threshold = datetime.utcnow() - timedelta(hours=6)
    alerts = []
    for modoule, data in monitors.items():
        for username, monitor in data.items():
            if monitor.last_watch_time < time_threshold:
                alerts.append('{}-{}: {}'.format(modoule, username, monitor.last_watch_time))
    for username, monitor in monitors[ProfileMonitor.monitor_type].items():
        if monitor.username.element != username:
            alerts.append('{} username changed to {}'.format(username, monitor.username.element))
    if TelegramNotifier.last_send_time is not None and TelegramNotifier.last_send_time < time_threshold:
        alerts.append('Telegram: {}'.format(TelegramNotifier.last_send_time))
    if CqhttpNotifier.last_send_time is not None and CqhttpNotifier.last_send_time < time_threshold:
        alerts.append('Cqhttp: {}'.format(CqhttpNotifier.last_send_time))
    if alerts:
        send_alert(token=telegram_token, chat_id=telegram_chat_id, message='Alert: \n{}'.format('\n'.join(alerts)))


def _check_tokens_status(telegram_token: str, telegram_chat_id: int, watcher: TwitterWatcher):
    tokens_status = watcher.check_tokens()
    failed_tokens = [token for token, status in tokens_status.items() if status == False]
    if failed_tokens:
        send_alert(token=telegram_token,
                   chat_id=telegram_chat_id,
                   message='Some tokens failed: {}'.format(json.dumps(tokens_status, indent=4)))


@click.group()
def cli():
    pass


@cli.command(context_settings={'show_default': True})
@click.option('--log_dir', default=os.path.join(sys.path[0], 'log'))
@click.option('--cookies_dir', default=os.path.join(sys.path[0], 'cookies'))
@click.option('--token_config_path', default=os.path.join(sys.path[0], 'config/token.json'))
@click.option('--monitoring_config_path', default=os.path.join(sys.path[0], 'config/monitoring.json'))
@click.option('--confirm', is_flag=True, default=False, help="Confirm with the maintainer during initialization")
@click.option('--listen_exit_command',
              is_flag=True,
              default=False,
              help="Liten the \"exit\" command from telegram maintainer chat id")
@click.option('--send_daily_summary', is_flag=True, default=False, help="Send daily summary to telegram maintainer")
def run(log_dir, cookies_dir, token_config_path, monitoring_config_path, confirm, listen_exit_command,
        send_daily_summary):
    os.makedirs(log_dir, exist_ok=True)
    logging.basicConfig(filename=os.path.join(log_dir, 'main'),
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        level=logging.WARNING)
    _setup_logger('api', os.path.join(log_dir, 'twitter-api'))

    with open(os.path.join(token_config_path), 'r') as token_config_file:
        token_config = json.load(token_config_file)
        telegram_bot_token = token_config.get('telegram_bot_token', '')
        twitter_auth_username_list = token_config.get('twitter_auth_username_list', [])
        assert twitter_auth_username_list
    with open(os.path.join(monitoring_config_path), 'r') as monitoring_config_file:
        monitoring_config = json.load(monitoring_config_file)
        assert monitoring_config['monitoring_user_list']

    _setup_logger('telegram', os.path.join(log_dir, 'telegram'))
    _setup_logger('cqhttp', os.path.join(log_dir, 'cqhttp'))
    TelegramNotifier.init(token=telegram_bot_token, logger_name='telegram')
    CqhttpNotifier.init(token=token_config.get('cqhttp_access_token', ''), logger_name='cqhttp')

    weight_sum = monitoring_config.get('weight_sum_offset', 0)
    for monitoring_user in monitoring_config['monitoring_user_list']:
        weight_sum += monitoring_user['weight']

    token_number = len(twitter_auth_username_list)
    monitors = dict()
    for monitor_cls in CONFIG_FIELD_TO_MONITOR.values():
        monitors[monitor_cls.monitor_type] = dict()
    intervals = dict()
    executors = {'default': ThreadPoolExecutor(len(monitoring_config['monitoring_user_list']))}
    scheduler = BlockingScheduler(executors=executors)
    for monitoring_user in monitoring_config['monitoring_user_list']:
        username = monitoring_user['username']
        telegram_chat_id_list = monitoring_user.get('telegram_chat_id_list', None)
        cqhttp_url_list = monitoring_user.get('cqhttp_url_list', None)
        assert telegram_chat_id_list or cqhttp_url_list
        weight = monitoring_user['weight']
        for config_field, monitor_cls in CONFIG_FIELD_TO_MONITOR.items():
            if monitoring_user.get(config_field, False) or monitor_cls is ProfileMonitor:
                monitor_type = monitor_cls.monitor_type
                logger_name = '{}-{}'.format(username, monitor_type)
                _setup_logger(logger_name, os.path.join(log_dir, logger_name))
                monitor_interval = _get_interval_second(monitor_cls.rate_limit, token_number, weight, weight_sum)
                monitors[monitor_type][username] = monitor_cls(username, token_config, cookies_dir, monitor_interval,
                                                               telegram_chat_id_list, cqhttp_url_list)
                if monitor_cls is ProfileMonitor:
                    intervals[username] = monitors[monitor_type][username].interval
                    scheduler.add_job(monitors[monitor_type][username].watch,
                                      trigger='interval',
                                      seconds=monitors[monitor_type][username].interval)
    _setup_logger('monitor-caller', os.path.join(log_dir, 'monitor-caller'))
    MonitorManager.init(monitors=monitors)

    scheduler.add_job(GraphqlAPI.update_api_data, trigger='cron', hour='0')

    if monitoring_config['maintainer_chat_id']:
        # maintainer_chat_id should be telegram chat id.
        maintainer_chat_id = monitoring_config['maintainer_chat_id']
        twitter_watcher = TwitterWatcher(twitter_auth_username_list, cookies_dir)
        TelegramNotifier.put_message_into_queue(
            TelegramMessage(chat_id_list=[maintainer_chat_id],
                            text='Interval: {}'.format(json.dumps(intervals, indent=4))))
        _send_summary(maintainer_chat_id, monitors, twitter_watcher)
        scheduler.add_job(_check_monitors_status,
                          trigger='cron',
                          hour='*',
                          args=[telegram_bot_token, maintainer_chat_id, monitors])
        scheduler.add_job(_check_tokens_status,
                          trigger='cron',
                          hour='*',
                          args=[telegram_bot_token, maintainer_chat_id, twitter_watcher])
        if send_daily_summary:
            scheduler.add_job(_send_summary,
                              trigger='cron',
                              hour='6',
                              args=[maintainer_chat_id, monitors, twitter_watcher])
        if confirm:
            if not TelegramNotifier.confirm(
                    TelegramMessage(chat_id_list=[maintainer_chat_id],
                                    text='Please confirm the initialization information')):
                TelegramNotifier.put_message_into_queue(
                    TelegramMessage(chat_id_list=[maintainer_chat_id], text='Monitor will exit now.'))
                raise RuntimeError('Initialization information confirm error')
            TelegramNotifier.put_message_into_queue(
                TelegramMessage(chat_id_list=[maintainer_chat_id], text='Monitor initialization succeeded.'))
        if listen_exit_command:
            TelegramNotifier.listen_exit_command(maintainer_chat_id)

    scheduler.start()


@cli.command(context_settings={'show_default': True})
@click.option('--cookies_dir', default=os.path.join(sys.path[0], 'cookies'))
@click.option('--token_config_path', default=os.path.join(sys.path[0], 'config/token.json'))
@click.option('--telegram_chat_id')
@click.option('--test_username', default='X')
@click.option('--output_response', is_flag=True, default=False)
def check_tokens(cookies_dir, token_config_path, telegram_chat_id, test_username, output_response):
    with open(os.path.join(token_config_path), 'r') as token_config_file:
        token_config = json.load(token_config_file)
        telegram_bot_token = token_config.get('telegram_bot_token', '')
        twitter_auth_username_list = token_config.get('twitter_auth_username_list', [])
        assert twitter_auth_username_list
    twitter_watcher = TwitterWatcher(twitter_auth_username_list, cookies_dir)
    result = json.dumps(twitter_watcher.check_tokens(test_username, output_response), indent=4)
    print(result)
    if telegram_chat_id:
        TelegramNotifier.init(telegram_bot_token, '')
        TelegramNotifier.send_message(TelegramMessage(chat_id_list=[telegram_chat_id], text=result))


@cli.command(context_settings={'show_default': True})
@click.option('--cookies_dir', default=os.path.join(sys.path[0], 'cookies'))
@click.option('--username', required=True)
@click.option('--password', required=True)
def generate_auth_cookie(cookies_dir, username, password):
    os.makedirs(cookies_dir, exist_ok=True)
    auth_handler = get_auth_handler(username, password)
    dump_path = os.path.join(cookies_dir, '{}.json'.format(username))
    dump_auth_handler(auth_handler, dump_path)
    print('Saved to {}'.format(dump_path))


if __name__ == '__main__':
    cli()
