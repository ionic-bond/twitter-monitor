import json
import logging
from datetime import datetime, timedelta


class StatusTracker():

    def __new__(self):
        raise Exception('Do not instantiate this class!')

    monitors_status = dict()
    notifiers_status = dict()
    last_notify_time = datetime.utcnow()

    logger = logging.getLogger('status')

    @classmethod
    def update_monitor_status(cls, monitor_type: str, username: str):
        key = '{}-{}'.format(monitor_type, username)
        cls.monitors_status[key] = datetime.utcnow()

    @classmethod
    def get_monitor_status(cls, monitor_type: str, username: str):
        key = '{}-{}'.format(monitor_type, username)
        return cls.monitors_status.get(key, None)

    @classmethod
    def update_notifier_status(cls, notifier: str):
        cls.notifiers_status[notifier] = datetime.utcnow()

    @classmethod
    def get_notifier_status(cls, notifier: str):
        return cls.notifiers_status.get(notifier, None)

    @classmethod
    def update_last_notify_time(cls):
        cls.last_notify_time = datetime.utcnow()

    @classmethod
    def check(cls) -> list:
        cls.logger.info(json.dumps(cls.monitors_status))
        cls.logger.info(json.dumps(cls.notifiers_status))
        cls.logger.info('Last notify time: {}'.format(cls.last_notify_time))

        alerts = []

        monitor_time_threshold = datetime.utcnow() - timedelta(minutes=30)
        for monitor_name, monitor_status in cls.monitors_status.items():
            if monitor_status < monitor_time_threshold:
                alerts.append('{}: {}'.format(monitor_name, monitor_status))

        notifier_time_threshold = cls.last_notify_time - timedelta(minutes=30)
        for notifier_name, notifier_status in cls.notifiers_status.items():
            if notifier_status < notifier_time_threshold:
                alerts.append('{}: {}'.format(notifier_name, notifier_status))

        return alerts
