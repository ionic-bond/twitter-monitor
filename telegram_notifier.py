#!/usr/bin/python3

import logging
import time
from datetime import datetime, timezone
from typing import List, Union

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
    def _send_message_to_single_chat(self, chat_id: str, message: str,
                                     photo_url_list: Union[List[str], None], disable_preview: bool):
        if photo_url_list:
            if len(photo_url_list) == 1:
                self.bot.send_photo(
                    chat_id=chat_id, photo=photo_url_list[0], caption=message, timeout=60)
            else:
                media_group = [telegram.InputMediaPhoto(media=photo_url_list[0], caption=message)]
                for photo_url in photo_url_list[1:10]:
                    media_group.append(telegram.InputMediaPhoto(media=photo_url))
                self.bot.send_media_group(chat_id=chat_id, media=media_group, timeout=60)
        else:
            self.bot.send_message(
                chat_id=chat_id, text=message, disable_web_page_preview=disable_preview, timeout=60)

    def send_message(self,
                     message: str,
                     photo_url_list: Union[List[str], None] = None,
                     disable_preview: bool = False):
        message = '[{}][{}] {}'.format(self.username, self.module, message)
        self.logger.info('Sending message: {}\n'.format(message))
        if photo_url_list:
            self.logger.info('Photo: {}'.format(', '.join(photo_url_list)))
        for chat_id in self.chat_id_list:
            self._send_message_to_single_chat(chat_id, message, photo_url_list, disable_preview)

    @retry((BadRequest, RetryAfter, TimedOut, NetworkError), delay=5)
    def _get_updates(self, offset=None) -> List[telegram.Update]:
        return self.bot.get_updates(offset=offset)

    @staticmethod
    def _get_new_update_offset(updates: List[telegram.Update]) -> Union[int, None]:
        if not updates:
            return None
        return updates[-1].update_id + 1

    def confirm(self, message: str) -> bool:
        updates = self._get_updates()
        update_offset = self._get_new_update_offset(updates)
        message = '{}\nPlease reply Y/N'.format(message)
        self.send_message(message)
        sending_time = datetime.utcnow().replace(tzinfo=timezone.utc)
        while True:
            updates = self._get_updates(offset=update_offset)
            update_offset = self._get_new_update_offset(updates)
            for update in updates:
                message = update.message
                if message.date < sending_time:
                    continue
                if message.chat.id not in self.chat_id_list:
                    continue
                text = message.text.upper()
                if text == 'Y':
                    return True
                if text == 'N':
                    return False
            time.sleep(10)
