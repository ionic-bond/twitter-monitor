#!/usr/bin/python3

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List

from telegram_notifier import TelegramNotifier
from twitter_watcher import TwitterWatcher


class MonitorBase(ABC):

    def __init__(self, module: str, token_config: dict, username: str, telegram_chat_id_list: List[str]):
        self.twitter_watcher = TwitterWatcher(token_config['twitter_bearer_token_list'])
        self.user_id = self.twitter_watcher.get_id_by_username(username)
        self.telegram_notifier = TelegramNotifier(token=token_config['telegram_bot_token'],
                                                  chat_id_list=telegram_chat_id_list,
                                                  username=username,
                                                  module=module)
        self.logger = logging.getLogger('{}-{}'.format(username, module))
        self.last_watch_time = datetime.utcnow()

    def update_last_watch_time(self):
        self.last_watch_time = datetime.utcnow()

    @abstractmethod
    def watch(self):
        pass

    @abstractmethod
    def status(self) -> str:
        pass
