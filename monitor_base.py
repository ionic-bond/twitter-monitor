#!/usr/bin/python3

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Union

from cqhttp_notifier import CqhttpNotifier
from telegram_notifier import TelegramNotifier
from twitter_watcher import TwitterWatcher


class MonitorBase(ABC):

    def __init__(self, monitor_type: str, username: str, token_config: dict,
                 telegram_chat_id_list: List[str], cqhttp_url_list: List[str]):
        self.twitter_watcher = TwitterWatcher(token_config['twitter_bearer_token_list'])
        self.user_id = self.twitter_watcher.get_id_by_username(username)
        logger_name = '{}-{}'.format(username, monitor_type)
        self.logger = logging.getLogger(logger_name)
        self.telegram_notifier = (TelegramNotifier(token=token_config['telegram_bot_token'],
                                                   chat_id_list=telegram_chat_id_list,
                                                   logger_name=logger_name)
                                  if telegram_chat_id_list else None)
        self.cqhttp_notifier = (CqhttpNotifier(token=token_config.get('cqhttp_access_token', ''),
                                               url_list=cqhttp_url_list,
                                               logger_name=logger_name)
                                if cqhttp_url_list else None)
        self.message_prefix = '[{}][{}]'.format(username, monitor_type)
        self.last_watch_time = datetime.utcnow()

    def update_last_watch_time(self):
        self.last_watch_time = datetime.utcnow()

    def send_message(self,
                     message: str,
                     photo_url_list: Union[List[str], None] = None,
                     video_url_list: Union[List[str], None] = None,
                     disable_preview: bool = True):
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
        if self.telegram_notifier:
            self.telegram_notifier.send_message(message, photo_url_list, video_url_list, disable_preview)
        if self.cqhttp_notifier:
            self.cqhttp_notifier.send_message(message, photo_url_list, video_url_list)

    @abstractmethod
    def watch(self):
        pass

    @abstractmethod
    def status(self) -> str:
        pass
