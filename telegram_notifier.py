#!/usr/bin/python3

import logging
import os
import telegram

class TelegramNotifier:

    def __init__(self, chat_id: str, bot_name: str):
        if not chat_id:
            logging.warning('Telegram id not set, skip initialization of telegram notifier.')
            self.bot = None
            return
        token = os.environ.get("TELEGRAM_TOKEN")
        self.bot = telegram.Bot(token=token)
        self.chat_id = chat_id
        self.bot_name = bot_name
        self.send_message('Init telegram bot succeed: {}'.format(self.bot.get_me()))


    def send_message(self, message: str):
        logging.info('Sending message: {}'.format(message))
        if not self.bot:
            logging.warning('Telegram notifier not initialized, skip.')
            return
        self.bot.send_message(chat_id=self.chat_id, text='[{}] {}'.format(self.bot_name, message))
