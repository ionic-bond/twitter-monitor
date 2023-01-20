import logging
import time
from datetime import datetime, timezone
from typing import List, Union

import telegram
from retry import retry
from telegram.error import BadRequest, RetryAfter, TimedOut, NetworkError

from notifier_base import Message, NotifierBase


class TelegramMessage(Message):

    def __init__(self,
                 chat_id_list: List[int],
                 text: str,
                 photo_url_list: Union[List[str], None] = None,
                 video_url_list: Union[List[str], None] = None):
        super().__init__(text, photo_url_list, video_url_list)
        self.chat_id_list = chat_id_list


class TelegramNotifier(NotifierBase):

    @classmethod
    def init(cls, token: str, logger_name: str):
        assert token
        cls.bot = telegram.Bot(token=token, request=telegram.utils.request.Request(con_pool_size=2))
        cls.logger = logging.getLogger('{}'.format(logger_name))
        cls.logger.info('Init telegram notifier succeed.')
        super().init()

    @classmethod
    @retry((RetryAfter, TimedOut, NetworkError), delay=10, tries=30)
    def _send_message_to_single_chat(cls, chat_id: str, text: str, photo_url_list: Union[List[str],
                                                                                         None],
                                     video_url_list: Union[List[str], None]):
        if video_url_list:
            cls.bot.send_video(chat_id=chat_id, video=video_url_list[0], caption=text, timeout=60)
        elif photo_url_list:
            if len(photo_url_list) == 1:
                cls.bot.send_photo(chat_id=chat_id,
                                   photo=photo_url_list[0],
                                   caption=text,
                                   timeout=60)
            else:
                media_group = [telegram.InputMediaPhoto(media=photo_url_list[0], caption=text)]
                for photo_url in photo_url_list[1:10]:
                    media_group.append(telegram.InputMediaPhoto(media=photo_url))
                cls.bot.send_media_group(chat_id=chat_id, media=media_group, timeout=60)
        else:
            cls.bot.send_message(chat_id=chat_id,
                                 text=text,
                                 disable_web_page_preview=True,
                                 timeout=60)

    @classmethod
    def send_message(cls, message: TelegramMessage):
        assert cls.initialized
        assert isinstance(message, TelegramMessage)
        for chat_id in message.chat_id_list:
            try:
                cls._send_message_to_single_chat(chat_id, message.text, message.photo_url_list,
                                                 message.video_url_list)
            except BadRequest as e:
                # Telegram cannot send some photos/videos for unknown reasons.
                cls.logger.error('{}, trying to send message without media.'.format(e))
                cls._send_message_to_single_chat(chat_id, message.text, None, None)

    @classmethod
    @retry((RetryAfter, TimedOut), delay=10)
    def _get_updates(cls, offset=None) -> List[telegram.Update]:
        return cls.bot.get_updates(offset=offset)

    @staticmethod
    def _get_new_update_offset(updates: List[telegram.Update]) -> Union[int, None]:
        if not updates:
            return None
        return updates[-1].update_id + 1

    @classmethod
    def confirm(cls, message: TelegramMessage) -> bool:
        assert cls.initialized
        assert isinstance(message, TelegramMessage)
        updates = cls._get_updates()
        update_offset = cls._get_new_update_offset(updates)
        message.text = '{}\nPlease reply Y/N'.format(message.text)
        cls.put_message_into_queue(message)
        sending_time = datetime.utcnow().replace(tzinfo=timezone.utc)
        while True:
            updates = cls._get_updates(offset=update_offset)
            update_offset = cls._get_new_update_offset(updates)
            for update in updates:
                received_message = update.message
                if received_message.date < sending_time:
                    continue
                if received_message.chat.id not in message.chat_id_list:
                    continue
                text = received_message.text.upper()
                if text == 'Y':
                    return True
                if text == 'N':
                    return False
            time.sleep(10)


def send_alert(token: str, chat_id: int, message: str):
    # The telegram notifier may also be wrong, so initialize the telegram bot separately.
    bot = telegram.Bot(token=token)
    bot.send_message(chat_id=chat_id, text=message, timeout=60)
