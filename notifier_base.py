#!/usr/bin/python3

import queue
import threading
from abc import ABC, abstractmethod
from typing import List, Union


class Message:

    def __init__(self,
                 text: str,
                 photo_url_list: Union[List[str], None] = None,
                 video_url_list: Union[List[str], None] = None):
        self.text = text
        self.photo_url_list = photo_url_list
        self.video_url_list = video_url_list


class NotifierBase(ABC):
    message_queue = queue.SimpleQueue()
    initialized = False

    def __new__(self):
        raise Exception('Do not instantiate this class!')

    @classmethod
    @abstractmethod
    def init(cls):
        cls.initialized = True
        cls.work_start()

    @classmethod
    @abstractmethod
    def send_message(cls, message: Message):
        pass

    @classmethod
    def _work(cls):
        while True:
            message = cls.message_queue.get()
            cls.send_message(message)

    @classmethod
    def work_start(cls):
        threading.Thread(target=cls._work, daemon=True).start()

    @classmethod
    def put_message(cls, message: Message):
        cls.message_queue.put(message)
