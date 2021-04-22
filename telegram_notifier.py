#!/usr/bin/python3

import logging
import os
import telegram

from sleeper import Sleeper
from utils import get_token


class TelegramNotifier:

    def __init__(self, chat_ids: str, username: str, module: str):
        if not chat_ids:
            logging.warning('Telegram id not set, skip initialization of telegram notifier.')
            self.bot = None
            return
        token = get_token('TELEGRAM_TOKEN')
        if not token:
            raise ValueError('TELEGRAM_TOKEN is null, please fill in it.')
        self.bot = telegram.Bot(token=token)
        self.chat_ids = chat_ids.split(',')
        self.username = username
        self.module = module
        self.sleeper = Sleeper(1)
        self.send_message('Init telegram bot succeed.')

    def send_message(self, message: str):
        if not self.bot:
            logging.warning('Telegram notifier not initialized, skip.')
            return
        try:
            for chat_id in self.chat_ids:
                self.bot.send_message(chat_id=chat_id,
                                      text='[{}][{}] {}'.format(self.username, self.module, message),
                                      timeout=50)
            self.sleeper.sleep(normal=True)
        except telegram.error as e:
            logging.error('Sending message error {}, retrying...'.format(e))
            self.sleeper.sleep(normal=False)
            self.send_message(message)
