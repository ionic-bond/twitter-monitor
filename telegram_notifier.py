#!/usr/bin/python3

import logging
import os
import telegram

class TelegramNotifier:

    def __init__(self, chat_ids: str, username: str, module: str):
        if not chat_ids:
            logging.warning('Telegram id not set, skip initialization of telegram notifier.')
            self.bot = None
            return
        token = os.environ.get("TELEGRAM_TOKEN")
        self.bot = telegram.Bot(token=token)
        self.chat_ids = chat_ids.split(',')
        self.username = username
        self.module = module
        self.send_message('Init telegram bot succeed.')


    def send_message(self, message: str):
        logging.info('Sending message: {}'.format(message))
        if not self.bot:
            logging.warning('Telegram notifier not initialized, skip.')
            return
        for chat_id in self.chat_ids:
            self.bot.send_message(chat_id=chat_id, text='[{}][{}] {}'.format(
                self.username, self.module, message))
