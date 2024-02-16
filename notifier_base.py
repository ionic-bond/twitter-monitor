import queue
import threading
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Union

from utils import check_initialized


class Message:

    def __init__(self,
                 text: str,
                 photo_url_list: Union[List[str], None] = None,
                 video_url_list: Union[List[str], None] = None):
        self.text = text
        self.photo_url_list = photo_url_list
        self.video_url_list = video_url_list


class NotifierBase(ABC):
    initialized = False

    def __new__(self):
        raise Exception('Do not instantiate this class!')

    @classmethod
    @abstractmethod
    def init(cls):
        cls.message_queue = queue.SimpleQueue()
        cls.last_send_time = None
        cls.initialized = True
        cls.work_start()

    @classmethod
    @abstractmethod
    @check_initialized
    def send_message(cls, message: Message):
        pass

    @classmethod
    @check_initialized
    def _work(cls):
        while True:
            message = cls.message_queue.get()
            try:
                cls.send_message(message)
                cls.last_send_time = datetime.utcnow()
            except Exception as e:
                print(e)
                cls.logger.error(e)

    @classmethod
    @check_initialized
    def work_start(cls):
        threading.Thread(target=cls._work, daemon=True).start()

    @classmethod
    @check_initialized
    def put_message_into_queue(cls, message: Message):
        cls.message_queue.put(message)
