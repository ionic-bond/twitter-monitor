import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Union

from cqhttp_notifier import CqhttpMessage, CqhttpNotifier
from discord_notifier import DiscordMessage, DiscordNotifier
from status_tracker import StatusTracker
from telegram_notifier import TelegramMessage, TelegramNotifier
from twitter_watcher import TwitterWatcher


class MonitorBase(ABC):

    def __init__(self, monitor_type: str, username: str, title: str, token_config: dict, user_config: dict,
                 cookies_dir: str):
        logger_name = '{}-{}'.format(title, monitor_type)
        self.logger = logging.getLogger(logger_name)
        self.twitter_watcher = TwitterWatcher(token_config.get('twitter_auth_username_list', []), cookies_dir)
        self.username = username
        self.user_id = self.twitter_watcher.get_id_by_username(username)
        if not self.user_id:
            raise RuntimeError('Initialization error, please check if username {} exists'.format(username))
        self.telegram_chat_id_list = user_config.get('telegram_chat_id_list', None)
        self.cqhttp_url_list = user_config.get('cqhttp_url_list', None)
        self.discord_webhook_url_list = user_config.get('discord_webhook_url_list', None)
        self.message_prefix = '[{}][{}]'.format(username, monitor_type)
        self.update_last_watch_time()

    def update_last_watch_time(self):
        StatusTracker.update_monitor_status(self.monitor_type, self.username)

    def get_last_watch_time(self):
        return StatusTracker.get_monitor_status(self.monitor_type, self.username)

    def send_message(self,
                     message: str,
                     photo_url_list: Union[List[str], None] = None,
                     video_url_list: Union[List[str], None] = None):
        message = '{} {}'.format(self.message_prefix, message)
        self.logger.info('Sending message: {}\n'.format(message))
        if photo_url_list:
            photo_url_list = [photo_url for photo_url in photo_url_list if photo_url]
        if video_url_list:
            video_url_list = [video_url for video_url in video_url_list if video_url]
        if photo_url_list:
            self.logger.info('Photo: {}'.format(', '.join(photo_url_list)))
        if video_url_list:
            self.logger.info('Video: {}'.format(', '.join(video_url_list)))
        if self.telegram_chat_id_list:
            TelegramNotifier.put_message_into_queue(
                TelegramMessage(chat_id_list=self.telegram_chat_id_list,
                                text=message,
                                photo_url_list=photo_url_list,
                                video_url_list=video_url_list))
        if self.cqhttp_url_list:
            CqhttpNotifier.put_message_into_queue(
                CqhttpMessage(url_list=self.cqhttp_url_list,
                              text=message,
                              photo_url_list=photo_url_list,
                              video_url_list=video_url_list))
        if self.discord_webhook_url_list:
            DiscordNotifier.put_message_into_queue(
                DiscordMessage(webhook_url_list=self.discord_webhook_url_list,
                               text=message,
                               photo_url_list=photo_url_list,
                               video_url_list=video_url_list))

    @abstractmethod
    def watch(self) -> bool:
        pass

    @abstractmethod
    def status(self) -> str:
        pass


class MonitorManager():
    monitors = None

    def __new__(self):
        raise Exception('Do not instantiate this class!')

    @classmethod
    def init(cls, monitors: dict):
        cls.monitors = monitors
        cls.logger = logging.getLogger('monitor-caller')

    @classmethod
    def get(cls, monitor_type: str, username: str) -> Union[MonitorBase, None]:
        assert cls.monitors is not None
        monitors_by_type = cls.monitors.get(monitor_type, None)
        assert monitors_by_type is not None
        monitor = monitors_by_type.get(username, None)
        return monitor

    @classmethod
    def call(cls, monitor_type: str, username: str) -> bool:
        monitor = cls.get(monitor_type, username)
        if not monitor:
            return True
        return monitor.watch()
