import queue
import threading
from abc import ABC, abstractmethod

from status_tracker import StatusTracker
from utils import check_initialized


class Message:

    def __init__(self,
                 text: str,
                 photo_url_list: list[str] | None = None,
                 video_url_list: list[str] | None = None) -> None:
        self.text = text
        self.photo_url_list = photo_url_list
        self.video_url_list = video_url_list


class NotifierBase(ABC):
    initialized = False

    def __new__(cls):
        raise Exception('Do not instantiate this class!')

    @classmethod
    @abstractmethod
    def init(cls) -> None:
        cls.message_queue = queue.SimpleQueue()
        StatusTracker.set_notifier_status(cls.notifier_name, True)
        cls.initialized = True
        cls.work_start()

    @classmethod
    @abstractmethod
    @check_initialized
    def send_message(cls, message: Message) -> None:
        pass

    @classmethod
    @check_initialized
    def _work(cls):
        while True:
            message = cls.message_queue.get()
            try:
                StatusTracker.set_notifier_status(cls.notifier_name, False)
                cls.send_message(message)
                StatusTracker.set_notifier_status(cls.notifier_name, True)
            except Exception as e:
                print(e)
                cls.logger.error(e)

    @classmethod
    @check_initialized
    def work_start(cls) -> None:
        threading.Thread(target=cls._work, daemon=True).start()

    @classmethod
    @check_initialized
    def put_message_into_queue(cls, message: Message) -> None:
        cls.message_queue.put(message)
