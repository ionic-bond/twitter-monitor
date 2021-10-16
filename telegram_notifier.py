#!/usr/bin/python3

import logging
from typing import List

import telegram
from retry import retry
from telegram.error import BadRequest, RetryAfter, TimedOut, NetworkError


class TelegramNotifier:

    def __init__(self, token: str, chat_id_list: List[str], username: str, module: str):
        assert token
        assert chat_id_list
        self.bot = telegram.Bot(token=token)
        self.chat_id_list = chat_id_list
        self.username = username
        self.module = module
        self.logger = logging.getLogger('{}-{}'.format(username, module))
        self.logger.info('Init telegram bot [{}][{}] succeed.'.format(username, module))

    @retry((BadRequest, RetryAfter, TimedOut, NetworkError), delay=5)
    def _send_message_to_single_chat(self, chat_id: str, message: str, disable_preview: bool):
        self.bot.send_message(chat_id=chat_id,
                              text=message,
                              disable_web_page_preview=disable_preview,
                              timeout=60)

    def send_message(self, message: str, disable_preview: bool=False):
        message = '[{}][{}] {}'.format(self.username, self.module, message)
        self.logger.info('Sending message: {}'.format(message))
        for chat_id in self.chat_id_list:
            self._send_message_to_single_chat(chat_id, message, disable_preview)
