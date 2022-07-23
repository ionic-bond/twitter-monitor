#!/usr/bin/python3

import logging
import requests

from typing import List, Union


class CqhttpNotifier:

    def __init__(self, token: str, url_list: List[str], logger_name: str):
        assert url_list
        self.token = token
        self.url_list = url_list
        self.logger = logging.getLogger('{}'.format(logger_name))
        self.logger.info('Init cqhttp notifier succeed: {}'.format(str(url_list)))

    def _get_headers(self) -> Union[str, None]:
        if not self.token:
            return None
        return {'Authorization': 'Bearer {}'.format(self.token)}

    def _send_text_to_single_chat(self, url: str, message: str):
        data = {'message': message}
        response = requests.post(url, headers=self._get_headers(), data=data)
        if response.status_code != 200:
            self.logger.error('Cqhttp send text error: {}'.format(response.text))

    def _send_photo_to_single_chat(self, url: str, photo_url: str):
        data = {'message': '[CQ:image,file={}]'.format(photo_url)}
        response = requests.post(url, headers=self._get_headers(), data=data)
        if response.status_code != 200:
            self.logger.error('Cqhttp send photo {} error: {}'.format(photo_url, response.text))

    def _send_video_to_single_chat(self, url: str, video_url: str):
        data = {'message': '[CQ:video,file={}]'.format(video_url)}
        response = requests.post(url, headers=self._get_headers(), data=data)
        if response.status_code != 200:
            self.logger.error('Cqhttp send video {} error: {}'.format(video_url, response.text))

    def send_message(self,
                     message: str,
                     photo_url_list: Union[List[str], None] = None,
                     video_url_list: Union[List[str], None] = None):
        for url in self.url_list:
            self._send_text_to_single_chat(url, message)
            if photo_url_list:
                for photo_url in photo_url_list:
                    self._send_photo_to_single_chat(url, photo_url)
            if video_url_list:
                for video_url in video_url_list:
                    self._send_video_to_single_chat(url, video_url)
