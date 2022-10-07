import json
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Union

from cqhttp_notifier import CqhttpMessage, CqhttpNotifier
from telegram_notifier import TelegramMessage, TelegramNotifier
from twitter_watcher import TwitterWatcher


class MonitorBase(ABC):

    def __init__(self, monitor_type: str, username: str, token_config: dict, cache_dir: str,
                 telegram_chat_id_list: List[int], cqhttp_url_list: List[str]):
        self.twitter_watcher = TwitterWatcher(token_config['twitter_bearer_token_list'])
        self.user_id = self.twitter_watcher.get_id_by_username(username)
        logger_name = '{}-{}'.format(username, monitor_type)
        self.logger = logging.getLogger(logger_name)
        self.cache_file_path = '{}/{}-{}'.format(cache_dir, username, monitor_type)
        self.telegram_chat_id_list = telegram_chat_id_list
        self.cqhttp_url_list = cqhttp_url_list
        self.message_prefix = '[{}][{}]'.format(username, monitor_type)
        self.last_watch_time = datetime.utcnow()

    def update_last_watch_time(self):
        self.last_watch_time = datetime.utcnow()

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
        try:
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
        except Exception as e:
            self.logger.error(e)
            print(e)

    @abstractmethod
    def watch(self):
        pass

    @abstractmethod
    def status(self) -> str:
        pass

    def dump_to_cache(self, data):
        with open(self.cache_file_path, 'w') as cache_file:
            json.dump(data, cache_file, indent=4)

    def load_from_cache(self):
        if not os.path.exists(self.cache_file_path):
            return None
        with open(self.cache_file_path, 'r') as cache_file:
            return json.load(cache_file)
