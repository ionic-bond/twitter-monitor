#!/usr/bin/python3

import json
import logging
import os
import sys

import click
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.background import BlockingScheduler

from cqhttp_notifier import CqhttpNotifier
from following_monitor import FollowingMonitor
from graphql_api import GraphqlAPI
from like_monitor import LikeMonitor
from login import login
from monitor_base import MonitorManager
from profile_monitor import ProfileMonitor
from status_tracker import StatusTracker
from telegram_notifier import TelegramMessage, TelegramNotifier, send_alert
from tweet_monitor import TweetMonitor
from twitter_watcher import TwitterWatcher

CONFIG_FIELD_TO_MONITOR = {
    'monitoring_profile': ProfileMonitor,
    'monitoring_following': FollowingMonitor,
    'monitoring_like': LikeMonitor,
    'monitoring_tweet': TweetMonitor
}


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
    alerts = StatusTracker.check()
    for username, monitor in monitors[ProfileMonitor.monitor_type].items():
        if monitor.username.element != username:
            alerts.append('{} username changed to {}'.format(username, monitor.username.element))
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
@click.option('--interval', default=15, help="Monitor run interval")
@click.option('--confirm', is_flag=True, default=False, help="Confirm with the maintainer during initialization")
@click.option('--listen_exit_command',
              is_flag=True,
              default=False,
              help="Liten the \"exit\" command from telegram maintainer chat id")
@click.option('--send_daily_summary', is_flag=True, default=False, help="Send daily summary to telegram maintainer")
def run(log_dir, cookies_dir, token_config_path, monitoring_config_path, interval, confirm, listen_exit_command,
        send_daily_summary):
    os.makedirs(log_dir, exist_ok=True)
    logging.basicConfig(filename=os.path.join(log_dir, 'main'),
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        level=logging.WARNING)
    _setup_logger('api', os.path.join(log_dir, 'twitter-api'))
    _setup_logger('status', os.path.join(log_dir, 'status-tracker'))

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

    monitors = dict()
    for monitor_cls in CONFIG_FIELD_TO_MONITOR.values():
        monitors[monitor_cls.monitor_type] = dict()
    executors = {'default': ThreadPoolExecutor(len(monitoring_config['monitoring_user_list']))}
    scheduler = BlockingScheduler(executors=executors)
    for monitoring_user in monitoring_config['monitoring_user_list']:
        username = monitoring_user['username']
        for config_field, monitor_cls in CONFIG_FIELD_TO_MONITOR.items():
            if monitoring_user.get(config_field, False) or monitor_cls is ProfileMonitor:
                monitor_type = monitor_cls.monitor_type
                logger_name = '{}-{}'.format(username, monitor_type)
                _setup_logger(logger_name, os.path.join(log_dir, logger_name))
                monitors[monitor_type][username] = monitor_cls(username, token_config, monitoring_user, cookies_dir)
                if monitor_cls is ProfileMonitor:
                    scheduler.add_job(monitors[monitor_type][username].watch, trigger='interval', seconds=interval)
    _setup_logger('monitor-caller', os.path.join(log_dir, 'monitor-caller'))
    MonitorManager.init(monitors=monitors)

    scheduler.add_job(GraphqlAPI.update_api_data, trigger='cron', hour='*')

    if monitoring_config['maintainer_chat_id']:
        # maintainer_chat_id should be telegram chat id.
        maintainer_chat_id = monitoring_config['maintainer_chat_id']
        twitter_watcher = TwitterWatcher(twitter_auth_username_list, cookies_dir)
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
    client = login(username=username, password=password)
    cookies = client.cookies
    dump_path = os.path.join(cookies_dir, '{}.json'.format(username))
    with open(dump_path, 'w') as f:
        f.write(json.dumps(dict(cookies), indent=2))
    print('Saved to {}'.format(dump_path))


if __name__ == '__main__':
    cli()
