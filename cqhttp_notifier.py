import logging
import requests

from typing import List, Union

from notifier_base import Message, NotifierBase


class CqhttpMessage(Message):

    def __init__(self,
                 url_list: List[str],
                 text: str,
                 photo_url_list: Union[List[str], None] = None,
                 video_url_list: Union[List[str], None] = None):
        super().__init__(text, photo_url_list, video_url_list)
        self.url_list = url_list


class CqhttpNotifier(NotifierBase):

    @classmethod
    def init(cls, token: str, logger_name: str):
        cls.headers = {'Authorization': 'Bearer {}'.format(token)} if token else None
        cls.logger = logging.getLogger('{}'.format(logger_name))
        cls.logger.info('Init cqhttp notifier succeed.')
        super().init()

    @classmethod
    def _post_request_to_cqhttp(cls, url: str, data: dict):
        response = requests.post(url, headers=cls.headers, data=data)
        if response.status_code != 200:
            cls.logger.error('Post request error: {}, {}\nurl: {}\ndata: {}'.format(
                response.status_code, response.text, url, str(data)))

    @classmethod
    def _send_text_to_single_chat(cls, url: str, text: str):
        data = {'message': text}
        cls._post_request_to_cqhttp(url, data)

    @classmethod
    def _send_photo_to_single_chat(cls, url: str, photo_url: str):
        data = {'message': '[CQ:image,file={}]'.format(photo_url)}
        cls._post_request_to_cqhttp(url, data)

    @classmethod
    def _send_video_to_single_chat(cls, url: str, video_url: str):
        data = {'message': '[CQ:video,file={}]'.format(video_url)}
        cls._post_request_to_cqhttp(url, data)

    @classmethod
    def send_message(cls, message: CqhttpMessage):
        assert cls.initialized
        assert isinstance(message, CqhttpMessage)
        for url in message.url_list:
            cls._send_text_to_single_chat(url, message.text)
            if message.photo_url_list:
                for photo_url in message.photo_url_list:
                    cls._send_photo_to_single_chat(url, photo_url)
            if message.video_url_list:
                for video_url in message.video_url_list:
                    cls._send_video_to_single_chat(url, video_url)
