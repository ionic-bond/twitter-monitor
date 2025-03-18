import logging
from typing import List, Union

import requests

from notifier_base import Message, NotifierBase


class DiscordMessage(Message):

    def __init__(self,
                 webhook_url_list: List[str],
                 text: str,
                 photo_url_list: Union[List[str], None] = None,
                 video_url_list: Union[List[str], None] = None):
        super().__init__(text, photo_url_list, video_url_list)
        self.webhook_url_list = webhook_url_list


class DiscordNotifier(NotifierBase):
    notifier_name = 'Discord'

    @classmethod
    def init(cls, logger_name: str):
        cls.logger = logging.getLogger('{}'.format(logger_name))
        cls.logger.info('Init discord notifier succeed.')
        super().init()

    @classmethod
    def _post_request_to_discord(cls, url: str, data: dict):
        response = requests.post(url, json=data, timeout=60)
        if response.status_code != 204:  # Discord webhook returns 204 No Content on success
            raise RuntimeError('Post request error: {}, {}\nurl: {}\ndata: {}'.format(
                response.status_code, response.text, url, str(data)))

    @classmethod
    def _send_text_to_discord(cls, url: str, text: str):
        data = {'content': text}
        cls._post_request_to_discord(url, data)

    @classmethod
    def send_message(cls, message: DiscordMessage):
        assert cls.initialized
        assert isinstance(message, DiscordMessage)
        for url in message.webhook_url_list:
            cls._send_text_to_discord(url, message.text)
            if message.photo_url_list:
                for photo_url in message.photo_url_list:
                    cls._send_text_to_discord(url, photo_url)
            if message.video_url_list:
                for video_url in message.video_url_list:
                    cls._send_text_to_discord(url, video_url)